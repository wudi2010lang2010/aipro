from __future__ import annotations

import threading
import time
from typing import Any

from data.schema import AISignal
from data.storage import get_session


class BacktestResultStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq = 0
        self._store: dict[str, dict[str, Any]] = {}

    def save(self, payload: dict[str, Any]) -> str:
        with self._lock:
            self._seq += 1
            rid = f"bt_{int(time.time())}_{self._seq}"
            self._store[rid] = payload
            return rid

    def get(self, rid: str) -> dict[str, Any] | None:
        with self._lock:
            return self._store.get(rid)


result_store = BacktestResultStore()


def run_virtual_simulation(initial_cash: float = 100000.0, limit: int = 200) -> dict[str, Any]:
    with get_session() as session:
        rows = (
            session.query(AISignal)
            .order_by(AISignal.id.asc())
            .limit(min(max(limit, 1), 2000))
            .all()
        )

    cash = float(initial_cash)
    holding: dict[str, Any] | None = None
    trades: list[dict[str, Any]] = []

    for r in rows:
        sig = (r.signal or "").upper()
        px = float(r.buy_price or 0)
        if px <= 0:
            continue

        if sig == "BUY" and holding is None:
            shares = int(cash / px / 100) * 100
            if shares <= 0:
                continue
            cost = round(shares * px, 4)
            cash = round(cash - cost, 4)
            holding = {
                "ts_code": r.ts_code,
                "shares": shares,
                "price": px,
                "created_at": r.created_at,
            }
            trades.append(
                {
                    "time": r.created_at,
                    "action": "BUY",
                    "ts_code": r.ts_code,
                    "price": px,
                    "shares": shares,
                    "cash": cash,
                }
            )

        elif sig in {"SELL", "WATCH", "HOLD"} and holding is not None and holding["ts_code"] == r.ts_code:
            shares = int(holding["shares"])
            proceeds = round(shares * px, 4)
            cash = round(cash + proceeds, 4)
            pnl = round((px - float(holding["price"])) * shares, 4)
            trades.append(
                {
                    "time": r.created_at,
                    "action": "SELL",
                    "ts_code": r.ts_code,
                    "price": px,
                    "shares": shares,
                    "cash": cash,
                    "pnl": pnl,
                }
            )
            holding = None

    unrealized = 0.0
    if holding is not None:
        unrealized = round((float(holding["price"]) - float(holding["price"])) * int(holding["shares"]), 4)

    return {
        "initial_cash": initial_cash,
        "final_cash": cash,
        "holding": holding,
        "trade_count": len(trades),
        "unrealized": unrealized,
        "trades": trades[-200:],
    }
