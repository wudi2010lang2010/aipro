from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from ai.gemini_client import client as gemini_client
from ai.prompts import build_prompt
from ai.schemas import AISignalItem
from data.schema import AISignal, DailyKline, MinuteKline, Stock
from data.storage import get_session
from indicators.signals import detect
from notifications.sender import notifier
from risk.engine import risk_engine


def _fallback_signal(ts_code: str, name: str, latest: dict[str, Any], sigs: list[dict]) -> AISignalItem:
    close = float(latest.get("close") or 0)
    pct = float(latest.get("pct_chg") or 0)
    label = "WATCH"
    confidence = 55
    reasoning = "指标中性，建议观望"
    if any(s.get("type") == "BUY" for s in sigs) and pct > -3:
        label = "BUY"
        confidence = 70
        reasoning = "出现买入型技术信号，短线可关注"
    elif any(s.get("type") == "SELL" for s in sigs):
        label = "SELL"
        confidence = 72
        reasoning = "出现卖出型技术信号，注意控制风险"

    stop_loss = round(close * 0.95, 3) if close else None
    take_profit = round(close * 1.08, 3) if close else None

    return AISignalItem(
        ts_code=ts_code,
        name=name,
        signal=label,
        confidence=confidence,
        reasoning=reasoning,
        buy_price=close if label == "BUY" else None,
        stop_loss=stop_loss,
        take_profit=take_profit,
        risk_level="MEDIUM",
        hold_days=3,
        key_risks=["市场波动", "题材退潮"],
        model_version="rule-fallback",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def _load_bars(ts_code: str, period: str, limit: int = 120) -> list[dict[str, Any]]:
    valid_periods = {"daily", "60min", "30min", "15min"}
    p = period if period in valid_periods else "daily"

    with get_session() as session:
        if p == "daily":
            rows = (
                session.query(DailyKline)
                .filter(DailyKline.ts_code == ts_code)
                .order_by(DailyKline.trade_date.desc())
                .limit(limit)
                .all()
            )
            bars = [
                {
                    "trade_date": r.trade_date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "pct_chg": r.pct_chg,
                }
                for r in reversed(rows)
            ]
            return bars

        rows = (
            session.query(MinuteKline)
            .filter(
                MinuteKline.ts_code == ts_code,
                MinuteKline.freq == p,
            )
            .order_by(MinuteKline.trade_time.desc())
            .limit(limit)
            .all()
        )
        bars = [
            {
                "trade_date": r.trade_time,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
                "pct_chg": None,
            }
            for r in reversed(rows)
        ]
        for i in range(1, len(bars)):
            prev_close = float(bars[i - 1].get("close") or 0)
            close = float(bars[i].get("close") or 0)
            if prev_close > 0:
                bars[i]["pct_chg"] = round((close - prev_close) / prev_close * 100, 4)
            else:
                bars[i]["pct_chg"] = 0.0
        if bars and bars[0]["pct_chg"] is None:
            bars[0]["pct_chg"] = 0.0
        return bars


def analyze_stock(ts_code: str, period: str = "daily") -> AISignalItem:
    ts_code = ts_code.upper().strip()
    period = (period or "daily").strip()

    with get_session() as session:
        stock = session.query(Stock).filter(Stock.ts_code == ts_code).first()
        name = stock.name if stock else ts_code

    bars = _load_bars(ts_code=ts_code, period=period, limit=120)
    if not bars:
        raise ValueError(f"No kline data for {ts_code}")

    # reuse local rule signal as context
    import pandas as pd
    from indicators.calculator import calculate

    df = calculate(pd.DataFrame(bars))
    local_signals = detect(df)
    latest = bars[-1]

    payload = {
        "ts_code": ts_code,
        "name": name,
        "period": period,
        "latest": latest,
        "local_signals": local_signals,
        "risk": risk_engine.snapshot(),
    }

    prompt = build_prompt(payload)
    ai_res = gemini_client.generate_json(prompt, fast=False)

    if ai_res.ok:
        d = ai_res.data
        item = AISignalItem(
            ts_code=ts_code,
            name=name,
            signal=d.get("signal", "WATCH"),
            confidence=int(d.get("confidence", 60)),
            reasoning=str(d.get("reasoning", ""))[:1000] or "模型未返回理由",
            buy_price=d.get("buy_price"),
            stop_loss=d.get("stop_loss"),
            take_profit=d.get("take_profit"),
            risk_level=d.get("risk_level", "MEDIUM"),
            hold_days=d.get("hold_days"),
            key_risks=[str(x) for x in d.get("key_risks", [])][:8],
            model_version=ai_res.model,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
    else:
        item = _fallback_signal(ts_code, name, latest, local_signals)

    # risk post-check
    gate = risk_engine.evaluate_signal(item.signal, item.confidence)
    if not gate["allow"] and item.signal == "BUY":
        item.signal = "WATCH"
        item.reasoning = f"{item.reasoning}；风控拦截: {gate['reason']}"

    with get_session() as session:
        row = AISignal(
            ts_code=item.ts_code,
            name=item.name,
            signal=item.signal,
            confidence=item.confidence,
            reasoning=item.reasoning,
            buy_price=item.buy_price,
            stop_loss=item.stop_loss,
            take_profit=item.take_profit,
            risk_level=item.risk_level,
            hold_days=item.hold_days,
            key_risks=json.dumps(item.key_risks, ensure_ascii=False),
            model_version=item.model_version,
            created_at=item.created_at,
        )
        session.add(row)
        session.flush()
        item.id = row.id

    notifier.notify_ai_signal(item.model_dump())
    return item


def list_signals(limit: int = 50, ts_code: str = "") -> list[dict[str, Any]]:
    with get_session() as session:
        q = session.query(AISignal)
        if ts_code:
            q = q.filter(AISignal.ts_code == ts_code.upper())
        rows = q.order_by(AISignal.id.desc()).limit(min(max(limit, 1), 500)).all()

    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "ts_code": r.ts_code,
                "name": r.name,
                "signal": r.signal,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
                "buy_price": r.buy_price,
                "stop_loss": r.stop_loss,
                "take_profit": r.take_profit,
                "risk_level": r.risk_level,
                "hold_days": r.hold_days,
                "key_risks": json.loads(r.key_risks) if r.key_risks else [],
                "model_version": r.model_version,
                "created_at": r.created_at,
            }
        )
    return out


def get_signal_by_id(signal_id: int) -> dict[str, Any] | None:
    with get_session() as session:
        r = session.query(AISignal).filter(AISignal.id == signal_id).first()
    if not r:
        return None
    return {
        "id": r.id,
        "ts_code": r.ts_code,
        "name": r.name,
        "signal": r.signal,
        "confidence": r.confidence,
        "reasoning": r.reasoning,
        "buy_price": r.buy_price,
        "stop_loss": r.stop_loss,
        "take_profit": r.take_profit,
        "risk_level": r.risk_level,
        "hold_days": r.hold_days,
        "key_risks": json.loads(r.key_risks) if r.key_risks else [],
        "model_version": r.model_version,
        "created_at": r.created_at,
    }
