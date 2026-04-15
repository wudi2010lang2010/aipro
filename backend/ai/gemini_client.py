from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from config import config
from loguru import logger


@dataclass
class GeminiResult:
    ok: bool
    data: dict[str, Any]
    model: str
    error: str = ""


class GeminiClient:
    def __init__(self) -> None:
        self._last_ts = 0.0
        self._min_interval = 4.0  # <= 15 rpm

    def _rate_limit(self) -> None:
        now = time.time()
        wait = self._min_interval - (now - self._last_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_ts = time.time()

    def generate_json(self, prompt: str, fast: bool = False) -> GeminiResult:
        model = config.GEMINI_MODEL_FAST if fast else config.GEMINI_MODEL_PRO
        if not config.GEMINI_API_KEY:
            return GeminiResult(ok=False, data={}, model=model, error="missing GEMINI_API_KEY")

        self._rate_limit()
        try:
            from google import genai

            client = genai.Client(api_key=config.GEMINI_API_KEY)
            resp = client.models.generate_content(model=model, contents=prompt)
            text = (resp.text or "").strip()
            data = json.loads(text)
            return GeminiResult(ok=True, data=data, model=model)
        except Exception as exc:
            logger.warning(f"Gemini call failed: {exc}")
            return GeminiResult(ok=False, data={}, model=model, error=str(exc))


# singleton
client = GeminiClient()
