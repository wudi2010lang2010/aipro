from __future__ import annotations

import json

PROMPT_SYSTEM = (
    "You are a China A-share short-term trading assistant. "
    "Return strict JSON only, no markdown."
)


def build_prompt(payload: dict) -> str:
    schema_hint = {
        "signal": "BUY|SELL|HOLD|WATCH",
        "confidence": "0-100 integer",
        "reasoning": "short Chinese explanation",
        "buy_price": "number|null",
        "stop_loss": "number|null",
        "take_profit": "number|null",
        "risk_level": "LOW|MEDIUM|HIGH",
        "hold_days": "integer|null",
        "key_risks": ["string"],
    }
    return (
        "Analyze this stock data for short-term action.\\n"
        "Return JSON using this schema exactly:\\n"
        f"{json.dumps(schema_hint, ensure_ascii=False)}\\n"
        "Input:\\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
