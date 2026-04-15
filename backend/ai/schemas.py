from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SignalType = Literal["BUY", "SELL", "HOLD", "WATCH"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class AIAnalyzeRequest(BaseModel):
    ts_code: str = Field(..., description="Stock code, e.g. 000001.SZ")
    period: Literal["daily", "60min", "30min", "15min"] = "daily"


class AISignalItem(BaseModel):
    id: Optional[int] = None
    ts_code: str
    name: str = ""
    signal: SignalType
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    buy_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_level: RiskLevel = "MEDIUM"
    hold_days: Optional[int] = None
    key_risks: List[str] = []
    model_version: str = "rule-fallback"
    created_at: str = ""


class AIAnalyzeResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: AISignalItem
