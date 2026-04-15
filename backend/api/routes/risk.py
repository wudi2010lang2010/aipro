from __future__ import annotations

from fastapi import APIRouter

from risk.engine import risk_engine

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("/status", summary="当前风控状态")
def risk_status():
    return {"code": 0, "message": "ok", "data": risk_engine.snapshot()}
