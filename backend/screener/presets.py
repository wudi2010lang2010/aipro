from __future__ import annotations

PRESETS: dict[str, dict] = {
    "trend_breakout": {
        "name": "趋势突破",
        "min_price": 3,
        "max_price": 120,
        "min_change_pct": 2.5,
        "max_change_pct": 9.8,
        "min_turnover_rate": 2.0,
        "min_volume_ratio": 1.5,
    },
    "low_absorb": {
        "name": "低吸反弹",
        "min_price": 2,
        "max_price": 80,
        "min_change_pct": -3.5,
        "max_change_pct": 1.0,
        "min_turnover_rate": 1.2,
        "min_volume_ratio": 1.2,
    },
    "strong_momentum": {
        "name": "强势动量",
        "min_price": 5,
        "max_price": 300,
        "min_change_pct": 5,
        "max_change_pct": 12,
        "min_turnover_rate": 3.0,
        "min_volume_ratio": 2.0,
    },
}
