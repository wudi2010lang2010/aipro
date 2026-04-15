from __future__ import annotations

from typing import Any


def apply_filters(rows: list[dict[str, Any]], cond: dict[str, Any]) -> list[dict[str, Any]]:
    min_price = float(cond.get("min_price", 0) or 0)
    max_price = float(cond.get("max_price", 1e12) or 1e12)
    min_change = float(cond.get("min_change_pct", -1e9) or -1e9)
    max_change = float(cond.get("max_change_pct", 1e9) or 1e9)
    min_turnover = float(cond.get("min_turnover_rate", -1e9) or -1e9)
    min_vol_ratio = float(cond.get("min_volume_ratio", -1e9) or -1e9)

    out: list[dict[str, Any]] = []
    for r in rows:
        p = float(r.get("price") or 0)
        c = float(r.get("change_pct") or 0)
        t = float(r.get("turnover_rate") or 0)
        v = float(r.get("volume_ratio") or 0)
        if not (min_price <= p <= max_price):
            continue
        if not (min_change <= c <= max_change):
            continue
        if t < min_turnover:
            continue
        if v < min_vol_ratio:
            continue
        out.append(r)
    return out
