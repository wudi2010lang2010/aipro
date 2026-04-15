from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func

from data.schema import DailyBasic, DailyKline, ScreenerResult, Stock
from data.storage import get_session
from screener.filters import apply_filters


def _latest_daily_basic_map(session) -> dict[str, dict]:
    latest_date = session.query(DailyBasic.trade_date).order_by(DailyBasic.trade_date.desc()).first()
    if not latest_date:
        return {}
    date_str = latest_date[0]
    rows = session.query(DailyBasic).filter(DailyBasic.trade_date == date_str).all()
    return {
        r.ts_code: {
            "turnover_rate": r.turnover_rate,
            "volume_ratio": r.volume_ratio,
        }
        for r in rows
    }


def _latest_kline_map(session) -> dict[str, dict]:
    latest_per_code = (
        session.query(
            DailyKline.ts_code.label("ts_code"),
            func.max(DailyKline.trade_date).label("trade_date"),
        )
        .group_by(DailyKline.ts_code)
        .subquery()
    )
    rows = (
        session.query(DailyKline)
        .join(
            latest_per_code,
            and_(
                DailyKline.ts_code == latest_per_code.c.ts_code,
                DailyKline.trade_date == latest_per_code.c.trade_date,
            ),
        )
        .all()
    )
    data: dict[str, dict] = {}
    for r in rows:
        data[r.ts_code] = {
            "price": r.close,
            "change_pct": r.pct_chg,
            "trade_date": r.trade_date,
        }
    return data


def _score_row(row: dict[str, Any], preset_key: str) -> float:
    change_pct = float(row.get("change_pct") or 0)
    turnover_rate = float(row.get("turnover_rate") or 0)
    volume_ratio = float(row.get("volume_ratio") or 0)
    base = 50.0

    if preset_key == "low_absorb":
        # Prefer oversold/sideways names with active liquidity.
        rebound_zone = max(0.0, 6.0 - abs(change_pct + 1.0) * 2.0)
        base += rebound_zone * 3.0
        base += min(turnover_rate, 6.0) * 2.0
        base += min(volume_ratio, 4.0) * 2.5
    elif preset_key == "strong_momentum":
        # Prefer strong trend continuation.
        base += min(max(change_pct, 0.0), 15.0) * 3.0
        base += min(turnover_rate, 10.0) * 2.5
        base += min(volume_ratio, 8.0) * 2.0
    else:
        # Default: trend breakout.
        base += min(max(change_pct, -2.0), 10.0) * 2.2
        base += min(turnover_rate, 8.0) * 2.0
        base += min(volume_ratio, 6.0) * 2.8

    return round(max(0.0, min(base, 100.0)), 2)


def scan_market(
    cond: dict[str, Any],
    preset_name: str = "custom",
    preset_key: str = "trend_breakout",
    limit: int = 200,
) -> list[dict[str, Any]]:
    with get_session() as session:
        stocks = session.query(Stock).all()
        basics = _latest_daily_basic_map(session)
        kmap = _latest_kline_map(session)

    rows: list[dict[str, Any]] = []
    for s in stocks:
        k = kmap.get(s.ts_code)
        if not k:
            continue
        b = basics.get(s.ts_code, {})
        rows.append(
            {
                "ts_code": s.ts_code,
                "name": s.name,
                "price": k.get("price"),
                "change_pct": k.get("change_pct"),
                "turnover_rate": b.get("turnover_rate"),
                "volume_ratio": b.get("volume_ratio"),
            }
        )

    rows = apply_filters(rows, cond)

    # preset-aware score
    for r in rows:
        r["score"] = _score_row(r, preset_key)
        r["signal_count"] = 0
        r["signals"] = []

    rows.sort(key=lambda x: x["score"], reverse=True)
    rows = rows[: min(max(limit, 1), 500)]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_session() as session:
        for r in rows:
            session.add(
                ScreenerResult(
                    ts_code=r["ts_code"],
                    name=r.get("name", ""),
                    preset_name=preset_name,
                    score=r.get("score", 0),
                    price=r.get("price"),
                    change_pct=r.get("change_pct"),
                    volume_ratio=r.get("volume_ratio"),
                    turnover_rate=r.get("turnover_rate"),
                    signal_count=r.get("signal_count", 0),
                    signals=json.dumps(r.get("signals", []), ensure_ascii=False),
                    scanned_at=now,
                )
            )

    return rows
