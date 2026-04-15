import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（backend/）
BASE_DIR = Path(__file__).resolve().parent

# 加载 .env 文件
load_dotenv(BASE_DIR / ".env")


class Config:
    # ─── 路径 ─────────────────────────────────────────────
    BASE_DIR: Path = BASE_DIR
    DB_PATH: str = str(BASE_DIR / os.getenv("DB_PATH", "db/stock_analyzer.db"))
    LOG_DIR: Path = BASE_DIR / "logs"

    # ─── tushare ──────────────────────────────────────────
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    # ─── Google Gemini ────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_FAST: str = os.getenv("GEMINI_MODEL_FAST", "gemini-3.1-flash-lite")
    GEMINI_MODEL_PRO: str = os.getenv("GEMINI_MODEL_PRO", "gemini-3.1-pro")

    # ─── 企业微信通知 ──────────────────────────────────────
    WECOM_WEBHOOK_URL: str = os.getenv("WECOM_WEBHOOK_URL", "")

    # ─── SMTP 邮件备份 ────────────────────────────────────
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASS: str = os.getenv("SMTP_PASS", "")
    NOTIFY_EMAIL: str = os.getenv("NOTIFY_EMAIL", "")

    # ─── 服务器 ───────────────────────────────────────────
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # ─── 数据刷新 ─────────────────────────────────────────
    # 盘中实时行情轮询间隔（秒）
    POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "180"))

    # ─── 风控默认参数（可在设置页面覆盖）─────────────────────
    RISK_STOP_LOSS_PCT: float = float(
        os.getenv("RISK_STOP_LOSS_PCT", "0.05")
    )  # 单笔最大亏损 5%
    RISK_TRAILING_STOP_PCT: float = float(
        os.getenv("RISK_TRAILING_STOP_PCT", "0.03")
    )  # 移动止损回撤 3%
    RISK_DAILY_LOSS_PCT: float = float(
        os.getenv("RISK_DAILY_LOSS_PCT", "0.03")
    )  # 单日熔断 3%
    RISK_MAX_POSITION_PCT: float = float(
        os.getenv("RISK_MAX_POSITION_PCT", "0.30")
    )  # 单只仓位上限 30%
    RISK_MAX_HOLDINGS: int = int(os.getenv("RISK_MAX_HOLDINGS", "5"))  # 最大同时持仓数


# 全局单例，其他模块直接 from config import config
config = Config()
