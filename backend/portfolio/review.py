from __future__ import annotations

import json
from typing import Any

from portfolio.manager import get_equity_curve, list_transactions


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _max_drawdown(curve: list[dict[str, Any]]) -> float:
    if not curve:
        return 0.0
    peak = _safe_float(curve[0].get("equity"))
    mdd = 0.0
    for p in curve:
        eq = _safe_float(p.get("equity"))
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak
            if dd > mdd:
                mdd = dd
    return round(mdd * 100, 4)


def build_review_report(initial_cash: float = 100000.0) -> dict[str, Any]:
    tx = list_transactions(limit=5000)

    realized: list[float] = []
    for r in tx:
        if (r.get("action") or "").upper() != "SELL":
            continue
        note = r.get("note")
        if not note:
            continue
        try:
            payload = json.loads(note)
        except Exception:
            continue
        if "realized_pnl" in payload:
            realized.append(_safe_float(payload.get("realized_pnl")))

    total_trades = len(realized)
    wins = [x for x in realized if x > 0]
    losses = [x for x in realized if x < 0]

    win_rate = round(len(wins) / total_trades * 100, 4) if total_trades > 0 else 0.0
    avg_win = round(sum(wins) / len(wins), 4) if wins else 0.0
    avg_loss = round(abs(sum(losses) / len(losses)), 4) if losses else 0.0
    profit_loss_ratio = round(avg_win / avg_loss, 4) if avg_loss > 0 else 0.0

    max_losing_streak = 0
    streak = 0
    for x in realized:
        if x < 0:
            streak += 1
            if streak > max_losing_streak:
                max_losing_streak = streak
        else:
            streak = 0

    curve = get_equity_curve(days=3650, initial_cash=initial_cash)
    max_drawdown_pct = _max_drawdown(curve)
    latest_equity = _safe_float(curve[-1]["equity"], initial_cash) if curve else initial_cash
    total_return_pct = round((latest_equity - initial_cash) / initial_cash * 100, 4) if initial_cash > 0 else 0.0

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_loss_ratio": profit_loss_ratio,
        "max_drawdown_pct": max_drawdown_pct,
        "max_losing_streak": max_losing_streak,
        "total_realized_pnl": round(sum(realized), 4),
        "total_return_pct": total_return_pct,
        "equity_curve": curve,
    }
