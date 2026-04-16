from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query

from portfolio.manager import (
    add_position,
    close_position,
    get_equity_curve,
    get_portfolio_summary,
    list_positions,
    list_transactions,
    update_position,
)
from portfolio.review import build_review_report

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", summary="当前持仓列表")
def get_portfolio(include_closed: bool = Query(False)):
    rows = list_positions(include_closed=include_closed)
    summary = get_portfolio_summary(include_closed=include_closed)
    return {"code": 0, "message": "ok", "data": {"summary": summary, "rows": rows}}


@router.post("", summary="录入持仓")
def create_position(payload: dict = Body(default={})):
    try:
        item = add_position(payload)
        return {"code": 0, "message": "ok", "data": item}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{position_id}", summary="修改持仓")
def edit_position(position_id: int, payload: dict = Body(default={})):
    try:
        item = update_position(position_id, payload)
        return {"code": 0, "message": "ok", "data": item}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{position_id}", summary="平仓")
def remove_position(
    position_id: int,
    sell_price: float | None = Query(default=None),
    sell_date: str | None = Query(default=None),
    note: str = Query(default=""),
):
    try:
        item = close_position(position_id, sell_price=sell_price, sell_date=sell_date, note=note)
        return {"code": 0, "message": "ok", "data": item}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/review", summary="复盘统计")
def review(initial_cash: float = Query(100000.0, gt=0)):
    data = build_review_report(initial_cash=initial_cash)
    return {"code": 0, "message": "ok", "data": data}


@router.get("/equity", summary="账户净值曲线")
def equity(days: int = Query(120, ge=1, le=3650), initial_cash: float = Query(100000.0, gt=0)):
    data = get_equity_curve(days=days, initial_cash=initial_cash)
    return {"code": 0, "message": "ok", "data": data}


@router.get("/transactions", summary="交易记录")
def transactions(limit: int = Query(200, ge=1, le=1000)):
    data = list_transactions(limit=limit)
    return {"code": 0, "message": "ok", "data": data}
