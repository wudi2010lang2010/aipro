from __future__ import annotations

from typing import Any


def calc_fixed_stop(cost_price: float, pct: float) -> float:
    return round(cost_price * (1 - pct), 3)


def calc_trailing_stop(peak_price: float, pct: float) -> float:
    return round(peak_price * (1 - pct), 3)


def calc_time_stop(holding_days: int, max_days: int) -> bool:
    return holding_days >= max_days


def evaluate_stop(price: float, cost_price: float, peak_price: float, cfg: dict[str, Any]) -> dict[str, Any]:
    fixed = calc_fixed_stop(cost_price, float(cfg.get("stop_loss_pct", 0.05)))
    trailing = calc_trailing_stop(max(peak_price, price), float(cfg.get("trailing_stop_pct", 0.03)))
    trigger = price <= max(fixed, trailing)
    return {"trigger": trigger, "fixed": fixed, "trailing": trailing}
