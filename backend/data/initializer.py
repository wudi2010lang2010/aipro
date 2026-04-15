"""
data/initializer.py
首次启动自动初始化器

启动时在后台线程中执行：
  1. 测试 tushare 连接
  2. stocks 表为空 → 自动拉取全量股票基础信息
  3. trade_calendar 表为空 → 自动拉取交易日历（2020~今天）
  4. north_money 表为空 → 自动拉取近 2 年北向资金

全部为非阻塞操作，不影响 FastAPI 正常启动和接口响应。
tushare 不可用时静默跳过，日志中会有提示。
"""

from __future__ import annotations

import threading

from loguru import logger


def auto_init() -> None:
    """
    在后台线程中执行首次数据初始化。
    在 main.py lifespan 启动阶段调用，立即返回不阻塞。
    """
    thread = threading.Thread(target=_do_init, name="auto-init", daemon=True)
    thread.start()


def _do_init() -> None:
    """后台初始化主流程"""
    logger.info("=== 自动初始化开始（后台）===")

    # ── Step 1: 测试 tushare 连接 ──────────────────────────────────────────
    try:
        from data.tushare_client import tushare_client

        if not tushare_client.ping():
            logger.warning(
                "tushare 连接失败，跳过自动初始化。\n"
                "  原因：网络不通或需要配置代理。\n"
                "  解决：代理配置好后访问 POST /api/admin/manual-load 手动触发。"
            )
            return
    except Exception as exc:
        logger.warning(f"tushare 初始化异常，跳过自动初始化: {exc}")
        return

    # ── Step 2: 股票基础信息 ───────────────────────────────────────────────
    _init_stock_basic()

    # ── Step 3: 交易日历 ───────────────────────────────────────────────────
    _init_trade_calendar()

    # ── Step 4: 北向资金（近 2 年）────────────────────────────────────────
    _init_north_money()

    logger.info("=== 自动初始化完成 ===")


# ─── 各数据项初始化函数 ────────────────────────────────────────────────────────


def _init_stock_basic() -> None:
    """若 stocks 表为空，自动拉取全量股票基础信息"""
    try:
        from data.schema import Stock
        from data.storage import get_session

        with get_session() as session:
            count = session.query(Stock).count()

        if count > 0:
            logger.info(f"[初始化] 股票基础信息已有 {count} 条，跳过")
            return

        logger.info("[初始化] 股票基础信息为空，开始拉取...")
        from data.updater import data_updater

        n = data_updater.manual_load_stock_basic()
        logger.info(f"[初始化] 股票基础信息加载完成：{n} 条")

    except Exception as exc:
        logger.error(f"[初始化] 股票基础信息加载失败: {exc}")


def _init_trade_calendar() -> None:
    """若 trade_calendar 表为空，自动拉取 2020 年至今的交易日历"""
    try:
        from data.schema import TradeCalendar
        from data.storage import get_session

        with get_session() as session:
            count = session.query(TradeCalendar).count()

        if count > 0:
            logger.info(f"[初始化] 交易日历已有 {count} 条，跳过")
            return

        logger.info("[初始化] 交易日历为空，开始拉取（2020~今天）...")
        from data.updater import data_updater

        n = data_updater.manual_load_trade_calendar(start_date="20200101")
        logger.info(f"[初始化] 交易日历加载完成：{n} 条")

    except Exception as exc:
        logger.error(f"[初始化] 交易日历加载失败: {exc}")


def _init_north_money() -> None:
    """若 north_money 表为空，自动拉取近 2 年北向资金数据"""
    try:
        from data.schema import NorthMoney
        from data.storage import get_session

        with get_session() as session:
            count = session.query(NorthMoney).count()

        if count > 0:
            logger.info(f"[初始化] 北向资金已有 {count} 条，跳过")
            return

        logger.info("[初始化] 北向资金为空，开始拉取（近 2 年）...")

        from datetime import date, timedelta

        start_date = (date.today() - timedelta(days=730)).strftime("%Y%m%d")

        from data.updater import data_updater

        n = data_updater.manual_load_north_money_history(start_date=start_date)
        logger.info(f"[初始化] 北向资金加载完成：{n} 条")

    except Exception as exc:
        logger.error(f"[初始化] 北向资金加载失败: {exc}")


# ─── K 线按需加载（供 kline 路由调用）────────────────────────────────────────


def trigger_kline_load(ts_code: str, start_date: str = "20230101") -> None:
    """
    后台触发单只股票 K 线历史数据加载。
    当 kline API 查询到空数据时调用，不阻塞 API 响应。

    Args:
        ts_code:    股票代码，如 '000001.SZ'
        start_date: 起始日期，默认拉取 2023 年至今
    """

    def _load():
        try:
            logger.info(f"[按需加载] 触发 K 线加载: {ts_code} from {start_date}")
            from data.updater import data_updater

            count = data_updater.manual_load_daily(ts_code, start_date)
            if count > 0:
                logger.info(f"[按需加载] {ts_code} 日线加载完成：{count} 条")
            else:
                logger.warning(
                    f"[按需加载] {ts_code} 无新数据（可能 tushare 不可用或代码有误）"
                )
        except Exception as exc:
            logger.error(f"[按需加载] {ts_code} K 线加载失败: {exc}")

    thread = threading.Thread(target=_load, name=f"kline-load-{ts_code}", daemon=True)
    thread.start()
