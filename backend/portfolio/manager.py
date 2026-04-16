from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from data.realtime_client import realtime_client
from data.schema import Portfolio, Stock, Transaction
from data.storage import get_session

BUY_COMMISSION_RATE = 0.00025
SELL_COMMISSION_RATE = 0.00025
STAMP_DUTY_RATE = 0.001


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _trade_note(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _commission_buy(notional: float) -> float:
    return round(notional * BUY_COMMISSION_RATE, 4)


def _commission_sell(notional: float) -> float:
    return round(notional * SELL_COMMISSION_RATE, 4)


def _stamp_sell(notional: float) -> float:
    return round(notional * STAMP_DUTY_RATE, 4)


def _position_to_dict(p: Portfolio, quote_map: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    quote_map = quote_map or {}
    q = quote_map.get(p.ts_code, {})
    last_price = _safe_float(q.get("price"), _safe_float(p.cost_price))
    cost_price = _safe_float(p.cost_price)
    shares = _safe_int(p.shares)

    market_value = round(last_price * shares, 4)
    cost_value = round(cost_price * shares, 4)
    unrealized_pnl = round(market_value - cost_value, 4)
    unrealized_pct = round(unrealized_pnl / cost_value * 100, 4) if cost_value > 0 else 0.0

    hold_days = 0
    try:
        buy_date = datetime.strptime((p.buy_date or _today())[:10], "%Y-%m-%d")
        hold_days = max((datetime.now().date() - buy_date.date()).days, 0)
    except Exception:
        hold_days = 0

    return {
        "id": p.id,
        "ts_code": p.ts_code,
        "name": p.name,
        "cost_price": round(cost_price, 4),
        "shares": shares,
        "buy_date": p.buy_date,
        "stop_loss": p.stop_loss,
        "take_profit": p.take_profit,
        "status": p.status,
        "note": p.note,
        "created_at": p.created_at,
        "last_price": round(last_price, 4),
        "update_time": q.get("update_time", "--:--:--"),
        "market_value": market_value,
        "cost_value": cost_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pct": unrealized_pct,
        "hold_days": hold_days,
    }


def list_positions(include_closed: bool = False) -> list[dict[str, Any]]:
    with get_session() as session:
        q = session.query(Portfolio)
        if not include_closed:
            q = q.filter(Portfolio.status == "OPEN")
        items = q.order_by(Portfolio.id.desc()).all()

    ts_codes = [p.ts_code for p in items if p.ts_code]
    quote_map = realtime_client.get_quotes(ts_codes) if ts_codes else {}
    return [_position_to_dict(p, quote_map) for p in items]


def get_portfolio_summary(include_closed: bool = False) -> dict[str, Any]:
    positions = list_positions(include_closed=include_closed)
    total_market = sum(_safe_float(x.get("market_value")) for x in positions)
    total_cost = sum(_safe_float(x.get("cost_value")) for x in positions)
    total_pnl = round(total_market - total_cost, 4)
    total_pct = round(total_pnl / total_cost * 100, 4) if total_cost > 0 else 0.0

    return {
        "count": len(positions),
        "total_market_value": round(total_market, 4),
        "total_cost_value": round(total_cost, 4),
        "total_unrealized_pnl": total_pnl,
        "total_unrealized_pct": total_pct,
    }


def add_position(payload: dict[str, Any]) -> dict[str, Any]:
    ts_code = str(payload.get("ts_code", "")).upper().strip()
    if not ts_code:
        raise ValueError("ts_code is required")

    cost_price = _safe_float(payload.get("cost_price"), 0.0)
    shares = _safe_int(payload.get("shares"), 0)
    if cost_price <= 0 or shares <= 0:
        raise ValueError("cost_price and shares must be positive")

    buy_date = str(payload.get("buy_date") or _today())[:10]
    note = str(payload.get("note") or "")

    with get_session() as session:
        stock = session.query(Stock).filter(Stock.ts_code == ts_code).first()
        name = str(payload.get("name") or (stock.name if stock else ts_code))

        row = Portfolio(
            ts_code=ts_code,
            name=name,
            cost_price=cost_price,
            shares=shares,
            buy_date=buy_date,
            stop_loss=payload.get("stop_loss"),
            take_profit=payload.get("take_profit"),
            status="OPEN",
            note=note,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        session.add(row)
        session.flush()

        notional = round(cost_price * shares, 4)
        commission = _commission_buy(notional)
        session.add(
            Transaction(
                ts_code=ts_code,
                name=name,
                action="BUY",
                price=cost_price,
                shares=shares,
                commission=commission,
                stamp_duty=0.0,
                net_amount=round(-(notional + commission), 4),
                trade_date=buy_date,
                note=_trade_note({"portfolio_id": row.id, "source": "portfolio_add", "memo": note}),
            )
        )

    return {"id": row.id, "ts_code": ts_code, "name": name}


def update_position(position_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with get_session() as session:
        row = session.query(Portfolio).filter(Portfolio.id == position_id).first()
        if not row:
            raise ValueError("position not found")

        if "stop_loss" in payload:
            row.stop_loss = payload.get("stop_loss")
        if "take_profit" in payload:
            row.take_profit = payload.get("take_profit")
        if "note" in payload:
            row.note = str(payload.get("note") or "")

        session.add(row)

    return {"id": position_id, "updated": True}


def close_position(position_id: int, sell_price: float | None = None, sell_date: str | None = None, note: str = "") -> dict[str, Any]:
    with get_session() as session:
        row = (
            session.query(Portfolio)
            .filter(Portfolio.id == position_id, Portfolio.status == "OPEN")
            .first()
        )
        if not row:
            raise ValueError("open position not found")

        if sell_price is None:
            quote = realtime_client.get_quote(row.ts_code) or {}
            sell_price = _safe_float(quote.get("price"), _safe_float(row.cost_price))

        if sell_price <= 0:
            raise ValueError("invalid sell price")

        trade_date = (sell_date or _today())[:10]
        shares = _safe_int(row.shares)
        notional = round(sell_price * shares, 4)
        sell_commission = _commission_sell(notional)
        stamp = _stamp_sell(notional)

        buy_notional = round(_safe_float(row.cost_price) * shares, 4)
        buy_commission = _commission_buy(buy_notional)
        sell_net = round(notional - sell_commission - stamp, 4)
        buy_total = round(buy_notional + buy_commission, 4)
        realized_pnl = round(sell_net - buy_total, 4)
        realized_pct = round(realized_pnl / buy_total * 100, 4) if buy_total > 0 else 0.0

        row.status = "CLOSED"
        row.note = (f"{row.note or ''} | close:{trade_date}@{sell_price} {note}").strip(" |")
        session.add(row)

        session.add(
            Transaction(
                ts_code=row.ts_code,
                name=row.name,
                action="SELL",
                price=sell_price,
                shares=shares,
                commission=sell_commission,
                stamp_duty=stamp,
                net_amount=sell_net,
                trade_date=trade_date,
                note=_trade_note(
                    {
                        "portfolio_id": row.id,
                        "source": "portfolio_close",
                        "buy_total": buy_total,
                        "sell_net": sell_net,
                        "realized_pnl": realized_pnl,
                        "realized_pct": realized_pct,
                        "memo": note,
                    }
                ),
            )
        )

    return {
        "id": position_id,
        "ts_code": row.ts_code,
        "sell_price": round(sell_price, 4),
        "shares": shares,
        "realized_pnl": realized_pnl,
        "realized_pct": realized_pct,
    }


def list_transactions(limit: int = 200) -> list[dict[str, Any]]:
    with get_session() as session:
        rows = (
            session.query(Transaction)
            .order_by(Transaction.id.desc())
            .limit(min(max(limit, 1), 1000))
            .all()
        )

    data = []
    for r in rows:
        data.append(
            {
                "id": r.id,
                "ts_code": r.ts_code,
                "name": r.name,
                "action": r.action,
                "price": r.price,
                "shares": r.shares,
                "commission": r.commission,
                "stamp_duty": r.stamp_duty,
                "net_amount": r.net_amount,
                "trade_date": r.trade_date,
                "note": r.note,
            }
        )
    return data


def get_equity_curve(days: int = 90, initial_cash: float = 100000.0) -> list[dict[str, Any]]:
    rows = list_transactions(limit=5000)
    rows.sort(key=lambda x: (x.get("trade_date") or "", x.get("id") or 0))

    cash = float(initial_cash)
    history: list[dict[str, Any]] = []
    by_day: dict[str, float] = {}
    for r in rows:
        cash += _safe_float(r.get("net_amount"), 0.0)
        day = str(r.get("trade_date") or "")[:10]
        if day:
            by_day[day] = cash

    if not by_day:
        return []

    dates = sorted(by_day.keys())
    for d in dates:
        history.append({"date": d, "equity": round(by_day[d], 4)})

    if days > 0:
        history = history[-days:]
    return history
