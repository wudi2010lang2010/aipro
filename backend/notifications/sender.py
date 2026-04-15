from __future__ import annotations

import json
import smtplib
from email.mime.text import MIMEText
from typing import Any

import requests
from config import config
from loguru import logger


class Notifier:
    def _post_wecom(self, content: str) -> bool:
        if not config.WECOM_WEBHOOK_URL:
            return False
        try:
            payload = {"msgtype": "markdown", "markdown": {"content": content}}
            r = requests.post(config.WECOM_WEBHOOK_URL, json=payload, timeout=8)
            ok = r.status_code == 200 and r.json().get("errcode") == 0
            if not ok:
                logger.warning(f"wecom push failed: {r.text}")
            return ok
        except Exception as exc:
            logger.warning(f"wecom push error: {exc}")
            return False

    def _send_email(self, subject: str, body: str) -> bool:
        if not all([config.SMTP_USER, config.SMTP_PASS, config.NOTIFY_EMAIL]):
            return False
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = config.SMTP_USER
            msg["To"] = config.NOTIFY_EMAIL

            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=10) as s:
                s.starttls()
                s.login(config.SMTP_USER, config.SMTP_PASS)
                s.sendmail(config.SMTP_USER, [config.NOTIFY_EMAIL], msg.as_string())
            return True
        except Exception as exc:
            logger.warning(f"email send error: {exc}")
            return False

    def notify_ai_signal(self, signal: dict[str, Any]) -> None:
        content = (
            f"### AI信号\n"
            f"- 股票: `{signal.get('ts_code')}` {signal.get('name','')}\n"
            f"- 动作: **{signal.get('signal')}**\n"
            f"- 置信度: {signal.get('confidence')}\n"
            f"- 风险: {signal.get('risk_level')}\n"
            f"- 理由: {signal.get('reasoning','')[:120]}"
        )
        sent = self._post_wecom(content)
        if not sent:
            self._send_email("AI信号通知", json.dumps(signal, ensure_ascii=False, indent=2))


notifier = Notifier()
