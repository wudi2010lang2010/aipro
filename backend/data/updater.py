"""
data/updater.py
数据更新调度器

职责：
  - 盘中每 N 秒轮询实时行情快照
  - 每个交易日 15:30 盘后批量拉取当日数据
  - 每周日更新股票基础信息 + 交易日历
  - 提供 manual_load_* 系列方法，供代理配置好后手动补充历史数据
  - 提供 cleanup_old_data 清理过期数据

tushare 不可用时，盘后任务会静默跳过，不影响实时行情功能。
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config import config
from loguru import logger

from data.calendar_util import (
    format_trade_date,
    is_after_market,
    is_market_open,
    is_trade_day,
)


class DataUpdater:
    """
    数据更新调度器。
    使用 APScheduler BackgroundScheduler，在后台线程中运行。
    与 FastAPI 主进程解耦，不阻塞 API 响应。
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,  # 积压时只执行一次
                "max_instances": 1,  # 同一 job 不并发
                "misfire_grace_time": 60,
            },
        )
        self._setup_jobs()

    # ─── 任务注册 ──────────────────────────────────────────────────────────────

    def _setup_jobs(self):
        """注册所有定时任务"""

        # 1. 盘中实时行情轮询（交易时段才实际执行）
        self.scheduler.add_job(
            self.job_poll_realtime,
            IntervalTrigger(seconds=config.POLL_INTERVAL),
            id="poll_realtime",
            name="实时行情轮询",
            replace_existing=True,
        )

        # 2. 盘后批量数据更新（工作日 15:30）
        self.scheduler.add_job(
            self.job_after_market_update,
            CronTrigger(
                day_of_week="mon-fri",
                hour=15,
                minute=30,
                timezone="Asia/Shanghai",
            ),
            id="after_market_update",
            name="盘后数据更新",
            replace_existing=True,
        )

        # 3. 每周日 22:00 更新股票基础信息 + 交易日历（全量）
        self.scheduler.add_job(
            self.job_weekly_maintenance,
            CronTrigger(
                day_of_week="sun",
                hour=22,
                minute=0,
                timezone="Asia/Shanghai",
            ),
            id="weekly_maintenance",
            name="每周维护（股票列表+日历）",
            replace_existing=True,
        )

        # 4. 每天凌晨 02:00 清理过期数据
        self.scheduler.add_job(
            self.job_cleanup,
            CronTrigger(hour=2, minute=0, timezone="Asia/Shanghai"),
            id="daily_cleanup",
            name="过期数据清理",
            replace_existing=True,
        )

    # ─── 调度器生命周期 ────────────────────────────────────────────────────────

    def start(self):
        """启动调度器"""
        self.scheduler.start()
        logger.info(f"数据调度器已启动，共 {len(self.scheduler.get_jobs())} 个定时任务")

    def stop(self):
        """停止调度器（不等待正在运行的任务）"""
        self.scheduler.shutdown(wait=False)
        logger.info("数据调度器已停止")

    def get_jobs_status(self) -> list:
        """获取所有任务的运行状态，供 API 展示"""
        result = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            result.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": (
                        next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
                    ),
                }
            )
        return result

    # ─── 定时任务实现 ──────────────────────────────────────────────────────────

    def job_poll_realtime(self):
        """
        盘中实时行情轮询。
        仅在交易时段内执行，非交易时段直接返回。
        """
        if not is_market_open():
            return

        try:
            from data.realtime_client import realtime_client
            from data.schema import RealtimeSnapshot
            from data.storage import get_session

            indices = realtime_client.get_indices()
            if not indices:
                return

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with get_session() as session:
                for item in indices:
                    snap = RealtimeSnapshot(
                        ts_code=item["ts_code"],
                        name=item.get("name", ""),
                        price=item.get("price", 0.0),
                        pre_close=item.get("pre_close", 0.0),
                        open=item.get("open", 0.0),
                        high=item.get("high", 0.0),
                        low=item.get("low", 0.0),
                        volume=item.get("volume", 0.0),
                        amount=item.get("amount", 0.0),
                        change=item.get("change", 0.0),
                        change_pct=item.get("change_pct", 0.0),
                        snapshot_time=now_str,
                    )
                    session.add(snap)

            logger.debug(f"实时快照已保存 [{now_str}]：{len(indices)} 条")

        except Exception as exc:
            logger.error(f"实时行情轮询失败: {exc}")

    def job_after_market_update(self):
        """
        盘后批量数据更新。
        依次拉取：每日指标、资金流向、北向资金、龙虎榜。
        tushare 不可用时静默跳过。
        """
        if not is_trade_day():
            return

        trade_date = format_trade_date()
        logger.info(f"=== 盘后数据更新开始 [{trade_date}] ===")

        self._save_daily_basic(trade_date)
        self._save_money_flow(trade_date)
        self._save_north_money(trade_date, trade_date)
        self._save_dragon_tiger(trade_date)
        self.job_cleanup()

        logger.info(f"=== 盘后数据更新完成 [{trade_date}] ===")

    def job_weekly_maintenance(self):
        """每周维护：全量更新股票列表和交易日历。"""
        logger.info("=== 每周维护开始 ===")
        self._save_stock_basic()
        self._save_trade_calendar()
        logger.info("=== 每周维护完成 ===")

    def job_cleanup(self):
        """清理过期数据（实时快照 > 7 天，分钟线 > 60 天）"""
        try:
            from data.schema import MinuteKline, RealtimeSnapshot
            from data.storage import get_session

            snap_cutoff = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
            minute_cutoff = (date.today() - timedelta(days=60)).strftime("%Y-%m-%d")

            with get_session() as session:
                deleted_snap = (
                    session.query(RealtimeSnapshot)
                    .filter(RealtimeSnapshot.snapshot_time < snap_cutoff)
                    .delete(synchronize_session=False)
                )
                deleted_min = (
                    session.query(MinuteKline)
                    .filter(MinuteKline.trade_time < minute_cutoff)
                    .delete(synchronize_session=False)
                )

            if deleted_snap or deleted_min:
                logger.info(
                    f"清理过期数据：快照 {deleted_snap} 条，分钟线 {deleted_min} 条"
                )
        except Exception as exc:
            logger.error(f"清理过期数据失败: {exc}")

    # ─── 内部写库方法（供盘后任务和手动加载复用）──────────────────────────────

    def _save_daily_basic(self, trade_date: str) -> int:
        """保存每日指标到数据库，返回新增条数。"""
        try:
            from data.schema import DailyBasic
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_daily_basic(trade_date)
            if df.empty:
                return 0

            count = 0
            with get_session() as session:
                existing_codes = {
                    r.ts_code
                    for r in session.query(DailyBasic.ts_code).filter(
                        DailyBasic.trade_date == trade_date
                    )
                }
                for _, row in df.iterrows():
                    if row["ts_code"] in existing_codes:
                        continue
                    session.add(
                        DailyBasic(
                            ts_code=row["ts_code"],
                            trade_date=row["trade_date"],
                            turnover_rate=row.get("turnover_rate"),
                            volume_ratio=row.get("volume_ratio"),
                            pe=row.get("pe"),
                            pb=row.get("pb"),
                            total_mv=row.get("total_mv"),
                            circ_mv=row.get("circ_mv"),
                        )
                    )
                    count += 1

            logger.info(f"每日指标 [{trade_date}]：新增 {count} 条")
            return count
        except Exception as exc:
            logger.error(f"保存每日指标失败 [{trade_date}]: {exc}")
            return 0

    def _save_money_flow(self, trade_date: str) -> int:
        """保存个股资金流向，返回新增条数。"""
        try:
            from data.schema import MoneyFlow
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_money_flow(trade_date)
            if df.empty:
                return 0

            count = 0
            with get_session() as session:
                existing_codes = {
                    r.ts_code
                    for r in session.query(MoneyFlow.ts_code).filter(
                        MoneyFlow.trade_date == trade_date
                    )
                }
                for _, row in df.iterrows():
                    if row["ts_code"] in existing_codes:
                        continue
                    session.add(
                        MoneyFlow(
                            ts_code=row["ts_code"],
                            trade_date=row["trade_date"],
                            buy_sm_amount=row.get("buy_sm_amount"),
                            sell_sm_amount=row.get("sell_sm_amount"),
                            buy_md_amount=row.get("buy_md_amount"),
                            sell_md_amount=row.get("sell_md_amount"),
                            buy_lg_amount=row.get("buy_lg_amount"),
                            sell_lg_amount=row.get("sell_lg_amount"),
                            buy_elg_amount=row.get("buy_elg_amount"),
                            sell_elg_amount=row.get("sell_elg_amount"),
                            net_mf_amount=row.get("net_mf_amount"),
                        )
                    )
                    count += 1

            logger.info(f"资金流向 [{trade_date}]：新增 {count} 条")
            return count
        except Exception as exc:
            logger.error(f"保存资金流向失败 [{trade_date}]: {exc}")
            return 0

    def _save_north_money(self, start_date: str, end_date: str) -> int:
        """保存北向资金，返回新增条数。"""
        try:
            from data.schema import NorthMoney
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_north_money(start_date, end_date)
            if df.empty:
                return 0

            count = 0
            with get_session() as session:
                for _, row in df.iterrows():
                    trade_date = row.get("trade_date", "")
                    if not trade_date:
                        continue
                    existing = (
                        session.query(NorthMoney)
                        .filter(NorthMoney.trade_date == trade_date)
                        .first()
                    )
                    if existing:
                        continue
                    session.add(
                        NorthMoney(
                            trade_date=trade_date,
                            ggt_ss=row.get("ggt_ss"),
                            ggt_sz=row.get("ggt_sz"),
                            hgt=row.get("hgt"),
                            sgt=row.get("sgt"),
                            north_money=row.get("north_money"),
                            south_money=row.get("south_money"),
                        )
                    )
                    count += 1

            if count:
                logger.info(f"北向资金：新增 {count} 条")
            return count
        except Exception as exc:
            logger.error(f"保存北向资金失败: {exc}")
            return 0

    def _save_dragon_tiger(self, trade_date: str) -> int:
        """保存龙虎榜，返回新增条数。"""
        try:
            from data.schema import DragonTiger
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_top_list(trade_date)
            if df.empty:
                return 0

            count = 0
            with get_session() as session:
                # 当天龙虎榜整体删除重写（避免重复）
                session.query(DragonTiger).filter(
                    DragonTiger.trade_date == trade_date
                ).delete(synchronize_session=False)

                for _, row in df.iterrows():
                    session.add(
                        DragonTiger(
                            ts_code=row.get("ts_code", ""),
                            trade_date=trade_date,
                            name=row.get("name", ""),
                            close=row.get("close"),
                            pct_chg=row.get("pct_chg"),
                            turnover_rate=row.get("turnover_rate"),
                            reason=row.get("reason", ""),
                        )
                    )
                    count += 1

            logger.info(f"龙虎榜 [{trade_date}]：{count} 条")
            return count
        except Exception as exc:
            logger.error(f"保存龙虎榜失败 [{trade_date}]: {exc}")
            return 0

    def _save_stock_basic(self) -> int:
        """全量更新股票基础信息，返回更新条数。"""
        try:
            from data.schema import Stock
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_stock_basic()
            if df.empty:
                return 0

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            count = 0
            with get_session() as session:
                for _, row in df.iterrows():
                    ts_code = row["ts_code"]
                    is_st = 1 if "ST" in str(row.get("name", "")) else 0
                    existing = (
                        session.query(Stock).filter(Stock.ts_code == ts_code).first()
                    )
                    if existing:
                        existing.name = row["name"]
                        existing.market = row.get("market", "")
                        existing.industry = row.get("industry", "")
                        existing.is_st = is_st
                        existing.updated_at = now_str
                    else:
                        session.add(
                            Stock(
                                ts_code=ts_code,
                                symbol=row["symbol"],
                                name=row["name"],
                                market=row.get("market", ""),
                                industry=row.get("industry", ""),
                                list_date=row.get("list_date", ""),
                                is_st=is_st,
                                is_active=1,
                                updated_at=now_str,
                            )
                        )
                    count += 1

            logger.info(f"股票基础信息：共 {count} 条已更新/写入")
            return count
        except Exception as exc:
            logger.error(f"保存股票基础信息失败: {exc}")
            return 0

    def _save_trade_calendar(
        self,
        start_date: str = "20200101",
        end_date: Optional[str] = None,
    ) -> int:
        """更新交易日历，返回新增条数。"""
        try:
            from data.schema import TradeCalendar
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_trade_calendar(start_date, end_date)
            if df.empty:
                return 0

            count = 0
            with get_session() as session:
                for _, row in df.iterrows():
                    cal_date = str(row["cal_date"])
                    existing = (
                        session.query(TradeCalendar)
                        .filter(TradeCalendar.cal_date == cal_date)
                        .first()
                    )
                    if existing is None:
                        session.add(
                            TradeCalendar(
                                cal_date=cal_date,
                                is_open=int(row["is_open"]),
                            )
                        )
                        count += 1

            logger.info(f"交易日历：新增 {count} 条")
            return count
        except Exception as exc:
            logger.error(f"保存交易日历失败: {exc}")
            return 0

    def _save_daily_kline(
        self,
        ts_code: str,
        start_date: str,
        end_date: Optional[str] = None,
        adj: str = "qfq",
    ) -> int:
        """保存单只股票的前复权日线数据，返回新增条数。"""
        try:
            from data.schema import DailyKline
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_daily_adj(ts_code, start_date, end_date, adj)
            if df is None or df.empty:
                return 0

            count = 0
            with get_session() as session:
                for _, row in df.iterrows():
                    trade_date = str(row.get("trade_date", ""))
                    existing = (
                        session.query(DailyKline)
                        .filter(
                            DailyKline.ts_code == ts_code,
                            DailyKline.trade_date == trade_date,
                        )
                        .first()
                    )
                    if existing:
                        continue
                    vol = row.get("vol") or row.get("volume")
                    session.add(
                        DailyKline(
                            ts_code=ts_code,
                            trade_date=trade_date,
                            open=row.get("open"),
                            high=row.get("high"),
                            low=row.get("low"),
                            close=row.get("close"),
                            volume=vol,
                            amount=row.get("amount"),
                            pct_chg=row.get("pct_chg"),
                        )
                    )
                    count += 1

            logger.debug(f"日线({adj}) {ts_code}：新增 {count} 条")
            return count
        except Exception as exc:
            logger.error(f"保存日线失败 {ts_code}: {exc}")
            return 0

    def _save_minute_kline(
        self,
        ts_code: str,
        freq: str = "15min",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """保存单只股票的分钟线数据，返回新增条数。"""
        try:
            from data.schema import MinuteKline
            from data.storage import get_session
            from data.tushare_client import tushare_client

            df = tushare_client.get_minute(ts_code, freq, start_date, end_date)
            if df.empty:
                return 0

            count = 0
            with get_session() as session:
                for _, row in df.iterrows():
                    trade_time = str(row.get("trade_time", ""))
                    existing = (
                        session.query(MinuteKline)
                        .filter(
                            MinuteKline.ts_code == ts_code,
                            MinuteKline.trade_time == trade_time,
                            MinuteKline.freq == freq,
                        )
                        .first()
                    )
                    if existing:
                        continue
                    vol = row.get("vol") or row.get("volume")
                    session.add(
                        MinuteKline(
                            ts_code=ts_code,
                            trade_time=trade_time,
                            freq=freq,
                            open=row.get("open"),
                            high=row.get("high"),
                            low=row.get("low"),
                            close=row.get("close"),
                            volume=vol,
                            amount=row.get("amount"),
                        )
                    )
                    count += 1

            logger.debug(f"分钟线({freq}) {ts_code}：新增 {count} 条")
            return count
        except Exception as exc:
            logger.error(f"保存分钟线失败 {ts_code}: {exc}")
            return 0

    # ─── 手动加载接口（代理配置好后调用）─────────────────────────────────────

    def manual_load_stock_basic(self) -> int:
        """
        手动触发：全量拉取股票基础信息。
        代理配置好后，在首次初始化时调用一次。
        """
        logger.info("[手动] 开始拉取股票基础信息...")
        count = self._save_stock_basic()
        logger.info(f"[手动] 股票基础信息完成：{count} 条")
        return count

    def manual_load_trade_calendar(
        self,
        start_date: str = "20200101",
        end_date: Optional[str] = None,
    ) -> int:
        """
        手动触发：拉取交易日历。
        代理配置好后，调用一次建立完整日历。
        """
        logger.info(f"[手动] 开始拉取交易日历 {start_date}~{end_date or '今天'}...")
        count = self._save_trade_calendar(start_date, end_date)
        logger.info(f"[手动] 交易日历完成：{count} 条")
        return count

    def manual_load_daily(
        self,
        ts_code: str,
        start_date: str,
        end_date: Optional[str] = None,
        adj: str = "qfq",
    ) -> int:
        """
        手动触发：拉取指定股票的复权日线数据。

        Args:
            ts_code:    股票代码，如 '000001.SZ'
            start_date: 起始日期，格式 YYYYMMDD，如 '20230101'
            end_date:   结束日期，格式 YYYYMMDD，默认为今天
            adj:        复权类型，qfq（前复权）/ hfq（后复权）

        Returns:
            新增条数

        示例（代理配置好后在 Python 控制台执行）：
            from data.updater import data_updater
            data_updater.manual_load_daily('000001.SZ', '20230101')
        """
        logger.info(
            f"[手动] 开始拉取日线 {ts_code} {start_date}~{end_date or '今天'} ({adj})..."
        )
        count = self._save_daily_kline(ts_code, start_date, end_date, adj)
        logger.info(f"[手动] 日线完成 {ts_code}：新增 {count} 条")
        return count

    def manual_load_daily_batch(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: Optional[str] = None,
        adj: str = "qfq",
        delay: float = 0.5,
    ) -> dict:
        """
        手动触发：批量拉取多只股票日线数据。

        Args:
            ts_codes:   股票代码列表
            start_date: 起始日期 YYYYMMDD
            end_date:   结束日期 YYYYMMDD
            adj:        复权类型
            delay:      每只之间的间隔（秒），避免触发 tushare 限速

        Returns:
            {ts_code: count} 字典
        """
        logger.info(
            f"[手动] 批量拉取日线：{len(ts_codes)} 只，"
            f"{start_date}~{end_date or '今天'}"
        )
        results = {}
        for i, ts_code in enumerate(ts_codes, 1):
            count = self._save_daily_kline(ts_code, start_date, end_date, adj)
            results[ts_code] = count
            logger.info(f"[手动] 进度 {i}/{len(ts_codes)} {ts_code}: {count} 条")
            if delay > 0 and i < len(ts_codes):
                time.sleep(delay)

        total = sum(results.values())
        logger.info(f"[手动] 批量日线完成：共新增 {total} 条")
        return results

    def manual_load_minute(
        self,
        ts_code: str,
        freq: str = "15min",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        """
        手动触发：拉取指定股票的分钟线数据。

        Args:
            ts_code:    股票代码
            freq:       频率 1min / 5min / 15min / 30min / 60min
            start_date: 起始时间（可选）
            end_date:   结束时间（可选）
        """
        logger.info(f"[手动] 开始拉取分钟线 {ts_code} {freq}...")
        count = self._save_minute_kline(ts_code, freq, start_date, end_date)
        logger.info(f"[手动] 分钟线完成 {ts_code}({freq})：新增 {count} 条")
        return count

    def manual_load_after_market(self, trade_date: Optional[str] = None) -> dict:
        """
        手动触发：拉取指定交易日的盘后数据。
        包含：每日指标、资金流向、北向资金、龙虎榜。

        Args:
            trade_date: 交易日期 YYYYMMDD，默认为上一个交易日

        Returns:
            各数据类型新增条数的字典
        """
        from data.calendar_util import get_last_trade_day

        if trade_date is None:
            trade_date = get_last_trade_day().strftime("%Y%m%d")

        logger.info(f"[手动] 开始拉取盘后数据 [{trade_date}]...")

        results = {
            "daily_basic": self._save_daily_basic(trade_date),
            "money_flow": self._save_money_flow(trade_date),
            "north_money": self._save_north_money(trade_date, trade_date),
            "dragon_tiger": self._save_dragon_tiger(trade_date),
        }

        logger.info(f"[手动] 盘后数据完成 [{trade_date}]: {results}")
        return results

    def manual_load_north_money_history(
        self,
        start_date: str = "20230101",
        end_date: Optional[str] = None,
    ) -> int:
        """手动触发：批量拉取历史北向资金数据。"""
        logger.info(f"[手动] 拉取历史北向资金 {start_date}~{end_date or '今天'}...")
        count = self._save_north_money(start_date, end_date or format_trade_date())
        logger.info(f"[手动] 历史北向资金完成：{count} 条")
        return count


# ─── 全局单例 ──────────────────────────────────────────────────────────────────
data_updater = DataUpdater()
