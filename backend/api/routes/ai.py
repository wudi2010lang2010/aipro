from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from ai.analyzer import analyze_stock, get_signal_by_id, list_signals

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/analyze", summary="触发单只股票AI分析")
def analyze(ts_code: str = Query(...), period: str = Query("daily")):
    valid_periods = {"daily", "60min", "30min", "15min"}
    period = (period or "daily").strip()
    if period not in valid_periods:
        raise HTTPException(status_code=400, detail=f"invalid period: {period}")

    try:
        item = analyze_stock(ts_code=ts_code, period=period)
        return {"code": 0, "message": "ok", "data": item.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(f"AI analyze failed [{ts_code} {period}]: {exc}")
        raise HTTPException(status_code=500, detail="AI analyze failed") from exc


@router.get("/signals", summary="AI历史信号列表")
def signals(limit: int = Query(50, ge=1, le=500), ts_code: str = Query("")):
    data = list_signals(limit=limit, ts_code=ts_code)
    return {"code": 0, "message": "ok", "data": data}


@router.get("/signals/{signal_id}", summary="单条信号详情")
def signal_detail(signal_id: int):
    item = get_signal_by_id(signal_id)
    if not item:
        raise HTTPException(status_code=404, detail="signal not found")
    return {"code": 0, "message": "ok", "data": item}
