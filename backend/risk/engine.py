from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import config


@dataclass
class RiskState:
    max_position_pct: float
    max_holdings: int
    daily_loss_pct: float
    stop_loss_pct: float
    trailing_stop_pct: float
    circuit_breaker: bool = False


class RiskEngine:
    def __init__(self) -> None:
        self.state = RiskState(
            max_position_pct=config.RISK_MAX_POSITION_PCT,
            max_holdings=config.RISK_MAX_HOLDINGS,
            daily_loss_pct=config.RISK_DAILY_LOSS_PCT,
            stop_loss_pct=config.RISK_STOP_LOSS_PCT,
            trailing_stop_pct=config.RISK_TRAILING_STOP_PCT,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "max_position_pct": self.state.max_position_pct,
            "max_holdings": self.state.max_holdings,
            "daily_loss_pct": self.state.daily_loss_pct,
            "stop_loss_pct": self.state.stop_loss_pct,
            "trailing_stop_pct": self.state.trailing_stop_pct,
            "circuit_breaker": self.state.circuit_breaker,
        }

    def evaluate_signal(self, signal: str, confidence: int) -> dict[str, Any]:
        if self.state.circuit_breaker and signal == "BUY":
            return {"allow": False, "reason": "daily circuit breaker active"}
        if signal == "BUY" and confidence < 55:
            return {"allow": False, "reason": "confidence too low"}
        return {"allow": True, "reason": "ok"}


risk_engine = RiskEngine()
