from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query

from backtest.engine import BacktestConfig, run_backtest
from backtest.simulator import result_store, run_virtual_simulation

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run", summary="执行回测")
def run(payload: dict = Body(default={})):
    ts_code = str(payload.get("ts_code") or "").upper().strip()
    start_date = str(payload.get("start_date") or "")
    end_date = str(payload.get("end_date") or "")
    if not ts_code or not start_date or not end_date:
        raise HTTPException(status_code=400, detail="ts_code/start_date/end_date are required")

    cfg = BacktestConfig(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        initial_cash=float(payload.get("initial_cash") or 100000),
        buy_ratio=float(payload.get("buy_ratio") or 0.95),
        commission_rate=float(payload.get("commission_rate") or 0.00025),
        stamp_duty_rate=float(payload.get("stamp_duty_rate") or 0.001),
        slippage=float(payload.get("slippage") or 0.0005),
    )

    try:
        result = run_backtest(cfg)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rid = result_store.save(result)
    return {"code": 0, "message": "ok", "data": {"result_id": rid, "report": result["report"]}}


@router.get("/results/{result_id}", summary="获取回测结果")
def get_result(result_id: str):
    data = result_store.get(result_id)
    if not data:
        raise HTTPException(status_code=404, detail="result not found")
    return {"code": 0, "message": "ok", "data": data}


@router.get("/simulate", summary="AI信号仿真盘")
def simulate(initial_cash: float = Query(100000.0, gt=0), limit: int = Query(200, ge=1, le=2000)):
    data = run_virtual_simulation(initial_cash=initial_cash, limit=limit)
    return {"code": 0, "message": "ok", "data": data}
