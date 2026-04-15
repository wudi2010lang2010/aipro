from __future__ import annotations

from fastapi import APIRouter, Body, Query

from screener.presets import PRESETS
from screener.scanner import scan_market

router = APIRouter(prefix="/api/screener", tags=["screener"])


PRESET_FALLBACKS: dict[str, dict] = {
    "trend_breakout": {
        "min_price": 3,
        "max_price": 300,
        "min_change_pct": 2.0,
        "max_change_pct": 15.0,
        "min_turnover_rate": -99,
        "min_volume_ratio": -99,
    },
    "low_absorb": {
        "min_price": 2,
        "max_price": 3000,
        "min_change_pct": -8.0,
        "max_change_pct": 2.0,
        "min_turnover_rate": -99,
        "min_volume_ratio": -99,
    },
    "strong_momentum": {
        "min_price": 5,
        "max_price": 500,
        "min_change_pct": 15.0,
        "max_change_pct": 35.0,
        "min_turnover_rate": -99,
        "min_volume_ratio": -99,
    },
}


@router.get("/presets", summary="预设策略列表")
def get_presets():
    return {"code": 0, "message": "ok", "data": PRESETS}


@router.post("/run", summary="执行选股扫描")
def run_screener(
    preset: str = Query("trend_breakout"),
    limit: int = Query(100, ge=1, le=500),
    cond: dict = Body(default={}),
):
    preset_key = preset if preset in PRESETS else "trend_breakout"
    base = PRESETS[preset_key].copy()
    base.update(cond or {})
    rows = scan_market(
        base,
        preset_name=PRESETS[preset_key]["name"],
        preset_key=preset_key,
        limit=limit,
    )
    used_fallback = False
    fallback_name = ""
    if not rows:
        used_fallback = True
        fallback_name = "策略兜底"
        relaxed = PRESET_FALLBACKS.get(preset_key, PRESET_FALLBACKS["trend_breakout"]).copy()
        rows = scan_market(
            relaxed,
            preset_name=f"{PRESETS[preset_key]['name']}-兜底",
            preset_key=preset_key,
            limit=min(limit, 80),
        )
    if not rows:
        used_fallback = True
        fallback_name = "二级兜底"
        full_relaxed = {
            "min_price": 0,
            "max_price": 1e9,
            "min_change_pct": -99 if preset_key == "low_absorb" else (15 if preset_key == "strong_momentum" else 2),
            "max_change_pct": 2 if preset_key == "low_absorb" else 99,
            "min_turnover_rate": -99,
            "min_volume_ratio": -99,
        }
        rows = scan_market(
            full_relaxed,
            preset_name=f"{PRESETS[preset_key]['name']}-全市场兜底",
            preset_key=preset_key,
            limit=min(limit, 50),
        )
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "count": len(rows),
            "rows": rows,
            "cond": base,
            "used_fallback": used_fallback,
            "fallback_name": fallback_name,
            "preset_key": preset_key,
        },
    }
