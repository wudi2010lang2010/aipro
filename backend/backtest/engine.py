from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from data.schema import DailyKline
from data.storage import get_session
from indicators.calculator import calculate
from indicators.signals import detect


@dataclass
class BacktestConfig:
    ts_code: str
    start_date: str
    end_date: str
    initial_cash: float = 100000.0
    buy_ratio: float = 0.95
    commission_rate: float = 0.00025
    stamp_duty_rate: float = 0.001
    slippage: float = 0.0005


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


def _normalize_date(d: str) -> str:
    d = (d or "").strip()
    if len(d) == 10 and "-" in d:
        return d.replace("-", "")
    return d


def run_backtest(cfg: BacktestConfig) -> dict[str, Any]:
    ts_code = cfg.ts_code.upper().strip()
    start_date = _normalize_date(cfg.start_date)
    end_date = _normalize_date(cfg.end_date)

    with get_session() as session:
        rows = (
            session.query(DailyKline)
            .filter(
                DailyKline.ts_code == ts_code,
                DailyKline.trade_date >= start_date,
                DailyKline.trade_date <= end_date,
            )
            .order_by(DailyKline.trade_date.asc())
            .all()
        )

    if len(rows) < 30:
        raise ValueError("not enough kline data for backtest")

    bars = [
        {
            "trade_date": r.trade_date,
            "open": _safe_float(r.open),
            "high": _safe_float(r.high),
            "low": _safe_float(r.low),
            "close": _safe_float(r.close),
            "volume": _safe_float(r.volume),
            "amount": _safe_float(r.amount),
            "pct_chg": _safe_float(r.pct_chg),
        }
        for r in rows
    ]

    cash = float(cfg.initial_cash)
    shares = 0
    trades: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []

    for i in range(25, len(bars)):
        window = pd.DataFrame(bars[: i + 1])
        df = calculate(window)
        sigs = detect(df)

        today = bars[i]
        close = _safe_float(today["close"])
        tdate = str(today["trade_date"])

        has_buy = any((s.get("type") or "") == "BUY" for s in sigs)
        has_sell = any((s.get("type") or "") == "SELL" for s in sigs)

        if shares == 0 and has_buy:
            buy_price = round(close * (1 + cfg.slippage), 4)
            budget = cash * cfg.buy_ratio
            lot_shares = _safe_int(budget / buy_price / 100) * 100
            if lot_shares > 0:
                notional = round(lot_shares * buy_price, 4)
                commission = round(notional * cfg.commission_rate, 4)
                total_cost = round(notional + commission, 4)
                if total_cost <= cash:
                    cash = round(cash - total_cost, 4)
                    shares = lot_shares
                    trades.append(
                        {
                            "date": tdate,
                            "action": "BUY",
                            "price": buy_price,
                            "shares": lot_shares,
                            "commission": commission,
                            "stamp_duty": 0.0,
                            "cash": cash,
                        }
                    )

        elif shares > 0 and has_sell:
            sell_price = round(close * (1 - cfg.slippage), 4)
            notional = round(shares * sell_price, 4)
            commission = round(notional * cfg.commission_rate, 4)
            stamp = round(notional * cfg.stamp_duty_rate, 4)
            net = round(notional - commission - stamp, 4)
            cash = round(cash + net, 4)
            trades.append(
                {
                    "date": tdate,
                    "action": "SELL",
                    "price": sell_price,
                    "shares": shares,
                    "commission": commission,
                    "stamp_duty": stamp,
                    "cash": cash,
                }
            )
            shares = 0

        equity = round(cash + shares * close, 4)
        equity_curve.append({"date": tdate, "equity": equity, "close": close, "shares": shares})

    # close remaining position at last bar close
    if shares > 0:
        last = bars[-1]
        close = _safe_float(last["close"])
        tdate = str(last["trade_date"])
        sell_price = round(close * (1 - cfg.slippage), 4)
        notional = round(shares * sell_price, 4)
        commission = round(notional * cfg.commission_rate, 4)
        stamp = round(notional * cfg.stamp_duty_rate, 4)
        net = round(notional - commission - stamp, 4)
        cash = round(cash + net, 4)
        trades.append(
            {
                "date": tdate,
                "action": "SELL",
                "price": sell_price,
                "shares": shares,
                "commission": commission,
                "stamp_duty": stamp,
                "cash": cash,
                "forced": True,
            }
        )
        shares = 0
        if equity_curve:
            equity_curve[-1]["equity"] = cash
            equity_curve[-1]["shares"] = 0

    buy_trades = [t for t in trades if t["action"] == "BUY"]
    sell_trades = [t for t in trades if t["action"] == "SELL"]

    # pair pnl by sequential round-trip
    pairs = min(len(buy_trades), len(sell_trades))
    pnls: list[float] = []
    for idx in range(pairs):
        b = buy_trades[idx]
        s = sell_trades[idx]
        buy_total = round(b["price"] * b["shares"] + b["commission"], 4)
        sell_net = round(s["price"] * s["shares"] - s["commission"] - s["stamp_duty"], 4)
        pnls.append(round(sell_net - buy_total, 4))

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    initial = float(cfg.initial_cash)
    final_equity = round(cash, 4)
    total_return_pct = round((final_equity - initial) / initial * 100, 4) if initial > 0 else 0.0

    peak = equity_curve[0]["equity"] if equity_curve else initial
    mdd = 0.0
    for p in equity_curve:
        eq = _safe_float(p["equity"])
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak
            if dd > mdd:
                mdd = dd

    report = {
        "ts_code": ts_code,
        "start_date": start_date,
        "end_date": end_date,
        "initial_cash": initial,
        "final_equity": final_equity,
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": round(mdd * 100, 4),
        "trade_count": len(pnls),
        "win_rate": round(len(wins) / len(pnls) * 100, 4) if pnls else 0.0,
        "profit_loss_ratio": round((sum(wins) / len(wins)) / abs(sum(losses) / len(losses)), 4)
        if wins and losses
        else 0.0,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    return {
        "report": report,
        "equity_curve": equity_curve,
        "trades": trades,
    }
