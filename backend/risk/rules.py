from __future__ import annotations

from datetime import datetime, timedelta


def is_limit_up(change_pct: float | None, board: str = "main") -> bool:
    if change_pct is None:
        return False
    lim = 20.0 if board in {"chi_next", "star"} else 10.0
    return change_pct >= lim - 0.01


def is_limit_down(change_pct: float | None, board: str = "main") -> bool:
    if change_pct is None:
        return False
    lim = 20.0 if board in {"chi_next", "star"} else 10.0
    return change_pct <= -lim + 0.01


def can_sell_today(buy_date: str, now: datetime | None = None) -> bool:
    # Simplified T+1: can sell next calendar day.
    now = now or datetime.now()
    try:
        d = datetime.strptime(buy_date, "%Y-%m-%d")
    except ValueError:
        return True
    return now.date() >= (d + timedelta(days=1)).date()
