"""
backend/main.py
FastAPI 应用入口

启动顺序：
  1. 配置 loguru 日志（控制台 + 文件滚动）
  2. 初始化 SQLite 数据库（建表，幂等）
  3. 启动后台数据调度器（APScheduler BackgroundScheduler）
  4. 启动异步行情推送调度器（APScheduler AsyncIOScheduler）
  5. 注册 REST 路由 + WebSocket 端点
  6. 挂载 Vue 前端静态文件（生产模式）
"""

from __future__ import annotations

import sys
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import config
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

# ─── 日志配置 ──────────────────────────────────────────────────────────────────


def _setup_logging() -> None:
    """
    配置 loguru 日志：
    - 控制台：INFO 级别，带颜色
    - 文件：  DEBUG 级别，按天滚动，保留 30 天
    """
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 移除 loguru 默认 handler
    logger.remove()

    # 控制台 handler
    logger.add(
        sys.stdout,
        level="INFO",
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "{message}"
        ),
    )

    # 文件 handler
    logger.add(
        config.LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",  # 每天零点滚动
        retention="30 days",  # 保留 30 天
        compression="zip",  # 旧日志压缩
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )


# ─── 异步调度器（行情推送）────────────────────────────────────────────────────

_async_scheduler: AsyncIOScheduler | None = None


def _get_async_scheduler() -> AsyncIOScheduler:
    global _async_scheduler
    if _async_scheduler is None:
        _async_scheduler = AsyncIOScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 30,
            },
        )
    return _async_scheduler


# ─── 应用生命周期 ──────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan 上下文管理器。
    yield 之前：应用启动逻辑
    yield 之后：应用关闭逻辑
    """
    # ── 启动 ───────────────────────────────────────────────────
    _setup_logging()

    logger.info("=" * 60)
    logger.info("  Stock AI Analyzer  启动中...")
    logger.info("=" * 60)

    # 1. 初始化数据库
    try:
        from data.schema import init_db

        init_db()
    except Exception as exc:
        logger.error(f"数据库初始化失败: {exc}")
        raise

    # 2. 启动后台数据调度器（BackgroundScheduler，运行在独立线程）
    try:
        from data.updater import data_updater

        data_updater.start()
    except Exception as exc:
        logger.warning(f"数据调度器启动失败（非致命）: {exc}")

    # 3. 启动异步调度器（AsyncIOScheduler，运行在事件循环中）
    try:
        from api.websocket import push_market_data

        scheduler = _get_async_scheduler()
        scheduler.add_job(
            push_market_data,
            trigger="interval",
            seconds=config.POLL_INTERVAL,
            id="ws_push_market",
            name="WebSocket 行情广播",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(f"异步调度器已启动，行情推送间隔: {config.POLL_INTERVAL}s")
    except Exception as exc:
        logger.warning(f"异步调度器启动失败（非致命）: {exc}")

    logger.info(f"服务地址:  http://{config.HOST}:{config.PORT}")
    logger.info(f"API 文档:  http://{config.HOST}:{config.PORT}/docs")
    logger.info(f"数据库:    {config.DB_PATH}")
    logger.info("=" * 60)

    # 5. 首次数据自动初始化（后台线程，不阻塞启动）
    try:
        from data.initializer import auto_init

        auto_init()
    except Exception as exc:
        logger.warning(f"自动初始化启动失败（非致命）: {exc}")

    yield  # ← 应用正常运行期间在此等待

    # ── 关闭 ───────────────────────────────────────────────────
    logger.info("服务正在关闭...")

    try:
        scheduler = _get_async_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)
    except Exception:
        pass

    try:
        from data.updater import data_updater

        data_updater.stop()
    except Exception:
        pass

    try:
        from data.storage import dispose_engine

        dispose_engine()
    except Exception:
        pass

    logger.info("服务已安全停止")


# ─── FastAPI 实例 ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stock AI Analyzer",
    description=(
        "AI 辅助 A 股短线趋势交易分析平台\n\n"
        "- 实时行情：腾讯/新浪财经\n"
        "- 历史数据：tushare Pro\n"
        "- AI 分析：Google Gemini\n"
        "- 交易市场：沪深 A 股"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS 中间件 ───────────────────────────────────────────────────────────────
# 开发阶段允许 Vite 开发服务器（localhost:5173）跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        f"http://localhost:{config.PORT}",
        f"http://127.0.0.1:{config.PORT}",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 路由注册 ──────────────────────────────────────────────────────────────────

from api.routes.market import router as market_router  # noqa: E402

app.include_router(market_router)

# 后续各周新增路由在此处追加，例如：
from api.routes.kline import router as kline_router  # noqa: E402

app.include_router(kline_router)

from api.routes.screener import router as screener_router  # noqa: E402
from api.routes.ai import router as ai_router  # noqa: E402
from api.routes.risk import router as risk_router  # noqa: E402

app.include_router(screener_router)
app.include_router(ai_router)
app.include_router(risk_router)

# from api.routes.portfolio import router as portfolio_router
# from api.routes.backtest  import router as backtest_router
# ...

# ─── WebSocket 端点 ────────────────────────────────────────────────────────────


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    """
    实时行情 WebSocket 端点。
    前端连接后立即接收一次行情快照，之后每 POLL_INTERVAL 秒广播一次。

    客户端协议（JSON）：
      {"type": "ping"}              → 心跳
      {"type": "get_quote"}         → 主动请求最新行情
      {"type": "get_status"}        → 获取服务端状态
    """
    from api.websocket import websocket_endpoint

    await websocket_endpoint(websocket)


# ─── 系统接口 ──────────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"], summary="健康检查")
def health_check():
    """服务健康检查，用于监控和启动脚本的等待逻辑。"""
    from datetime import datetime

    from data.calendar_util import get_market_status

    status_code, status_desc = get_market_status()
    return {
        "status": "ok",
        "version": "1.0.0",
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_status": status_code,
        "market_desc": status_desc,
    }


@app.get("/api/scheduler/jobs", tags=["system"], summary="查看定时任务状态")
def get_scheduler_jobs():
    """查看所有后台定时任务的运行状态及下次执行时间。"""
    try:
        from data.updater import data_updater

        jobs = data_updater.get_jobs_status()

        scheduler = _get_async_scheduler()
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": (
                        next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
                    ),
                    "scheduler": "async",
                }
            )

        return {"code": 0, "data": jobs}
    except Exception as exc:
        return {"code": 500, "message": str(exc)}


@app.post("/api/admin/manual-load", tags=["system"], summary="手动触发数据加载")
def manual_load(
    action: str, ts_code: str = "", start_date: str = "", end_date: str = ""
):
    """
    手动触发 tushare 数据加载（代理配置好后使用）。

    action 可选值：
    - stock_basic     全量更新股票列表
    - trade_calendar  更新交易日历
    - daily           拉取单只股票日线（需传 ts_code, start_date）
    - after_market    拉取盘后数据（可传 trade_date 作为 start_date）

    示例：
      POST /api/admin/manual-load?action=stock_basic
      POST /api/admin/manual-load?action=daily&ts_code=000001.SZ&start_date=20230101
    """
    try:
        from data.updater import data_updater

        if action == "stock_basic":
            count = data_updater.manual_load_stock_basic()
            return {"code": 0, "data": {"count": count}}

        elif action == "trade_calendar":
            count = data_updater.manual_load_trade_calendar(
                start_date or "20200101", end_date or None
            )
            return {"code": 0, "data": {"count": count}}

        elif action == "daily":
            if not ts_code or not start_date:
                return {"code": 400, "message": "daily 操作需要 ts_code 和 start_date"}
            count = data_updater.manual_load_daily(
                ts_code, start_date, end_date or None
            )
            return {"code": 0, "data": {"ts_code": ts_code, "count": count}}

        elif action == "after_market":
            result = data_updater.manual_load_after_market(start_date or None)
            return {"code": 0, "data": result}

        else:
            return {
                "code": 400,
                "message": f"未知 action: {action}，"
                f"可选: stock_basic / trade_calendar / daily / after_market",
            }

    except Exception as exc:
        logger.error(f"手动加载失败 [{action}]: {exc}")
        return {"code": 500, "message": str(exc)}


# ─── 静态文件（生产环境：Vue 构建产物）────────────────────────────────────────
# 开发环境不存在 static/ 目录，此段自动跳过
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists() and any(_STATIC_DIR.iterdir()):
    app.mount(
        "/",
        StaticFiles(directory=str(_STATIC_DIR), html=True),
        name="vue_frontend",
    )
    logger.info(f"前端静态文件已挂载: {_STATIC_DIR}")


# ─── 直接运行入口 ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,  # 生产/手动运行时关闭热重载
        log_level="warning",  # uvicorn 自身日志降级，改用 loguru
        access_log=False,  # 访问日志由 loguru 接管
    )
