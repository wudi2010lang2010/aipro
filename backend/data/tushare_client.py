"""
data/tushare_client.py
tushare API 封装

注意：tushare 接口需要网络代理才能访问时，所有方法均会静默捕获异常并返回空 DataFrame。
      代理配置好后，可通过 DataUpdater.manual_load_* 系列方法手动补充历史数据。
"""

from __future__ import annotations

import time
from datetime import date
from typing import Optional

import pandas as pd
from loguru import logger


class TushareClient:
    """
    tushare Pro API 封装。
    所有方法：
      - 调用失败时记录日志并返回空 DataFrame，不抛出异常
      - 使用懒加载初始化，首次调用时才连接 tushare
    """

    def __init__(self):
        self._pro = None
        self._last_call_time: float = 0.0
        # tushare 免费额度限速：每分钟约 200 次，保守起见间隔 0.3 秒
        self._min_interval: float = 0.3

    # ─── 内部工具 ──────────────────────────────────────────────────────────────

    @property
    def pro(self):
        """懒加载 tushare Pro API 实例"""
        if self._pro is None:
            import tushare as ts
            from config import config

            if not config.TUSHARE_TOKEN:
                raise RuntimeError(
                    "TUSHARE_TOKEN 未配置，请在 backend/.env 中填入 token"
                )
            ts.set_token(config.TUSHARE_TOKEN)
            self._pro = ts.pro_api()
            logger.info("tushare Pro API 初始化成功")
        return self._pro

    def _rate_limit(self):
        """简单限速，避免触发 tushare 频率限制"""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_time = time.time()

    def _safe_call(self, func, *args, **kwargs) -> pd.DataFrame:
        """
        安全调用 tushare 接口。
        任何异常均捕获并返回空 DataFrame。
        """
        self._rate_limit()
        try:
            result = func(*args, **kwargs)
            if result is None:
                return pd.DataFrame()
            return result
        except Exception as e:
            logger.warning(f"tushare 调用失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def _today() -> str:
        return date.today().strftime("%Y%m%d")

    # ─── 股票基础信息 ──────────────────────────────────────────────────────────

    def get_stock_basic(self) -> pd.DataFrame:
        """
        获取全市场股票基础信息。
        返回字段：ts_code, symbol, name, area, industry, market, list_date
        """
        logger.info("拉取股票基础信息...")
        df = self._safe_call(
            self.pro.stock_basic,
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,market,list_date",
        )
        if not df.empty:
            logger.info(f"股票基础信息: {len(df)} 条")
        return df

    # ─── 交易日历 ──────────────────────────────────────────────────────────────

    def get_trade_calendar(
        self,
        start_date: str = "20200101",
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取 SSE 交易日历。
        返回字段：cal_date, is_open（1=交易日，0=休市）
        """
        if end_date is None:
            end_date = self._today()
        logger.info(f"拉取交易日历: {start_date} ~ {end_date}")
        df = self._safe_call(
            self.pro.trade_cal,
            exchange="SSE",
            start_date=start_date,
            end_date=end_date,
            fields="cal_date,is_open",
        )
        if not df.empty:
            logger.info(f"交易日历: {len(df)} 条")
        return df

    # ─── 日线数据 ──────────────────────────────────────────────────────────────

    def get_daily(
        self,
        ts_code: str,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取日线数据（不复权）。
        返回字段：ts_code, trade_date, open, high, low, close, vol, amount, pct_chg
        """
        if end_date is None:
            end_date = self._today()
        df = self._safe_call(
            self.pro.daily,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        if not df.empty:
            logger.debug(f"日线(不复权) {ts_code}: {len(df)} 条")
        return df

    def get_daily_adj(
        self,
        ts_code: str,
        start_date: str,
        end_date: Optional[str] = None,
        adj: str = "qfq",
    ) -> pd.DataFrame:
        """
        获取复权日线数据（默认前复权 qfq）。
        使用 ts.pro_bar 接口，支持 qfq（前复权）/ hfq（后复权）/ None（不复权）。

        返回字段：ts_code, trade_date, open, high, low, close, vol, amount, pct_chg
        """
        import tushare as ts

        if end_date is None:
            end_date = self._today()

        self._rate_limit()
        try:
            df = ts.pro_bar(
                ts_code=ts_code,
                adj=adj,
                start_date=start_date,
                end_date=end_date,
            )
            if df is None:
                return pd.DataFrame()
            logger.debug(f"日线({adj}) {ts_code}: {len(df)} 条")
            return df
        except Exception as e:
            logger.warning(f"复权日线获取失败 {ts_code}: {e}")
            return pd.DataFrame()

    def get_daily_batch(
        self,
        trade_date: str,
    ) -> pd.DataFrame:
        """
        获取指定交易日全市场日线数据（适合批量拉取）。
        返回字段：ts_code, trade_date, open, high, low, close, vol, amount, pct_chg
        """
        logger.info(f"批量拉取日线 {trade_date}...")
        df = self._safe_call(
            self.pro.daily,
            trade_date=trade_date,
        )
        if not df.empty:
            logger.info(f"批量日线 {trade_date}: {len(df)} 条")
        return df

    # ─── 每日指标 ──────────────────────────────────────────────────────────────

    def get_daily_basic(self, trade_date: str) -> pd.DataFrame:
        """
        获取指定交易日全市场每日指标（换手率/量比/PE/PB/市值）。
        返回字段：ts_code, trade_date, turnover_rate, volume_ratio, pe, pb, total_mv, circ_mv
        """
        logger.info(f"拉取每日指标 {trade_date}...")
        df = self._safe_call(
            self.pro.daily_basic,
            trade_date=trade_date,
            fields="ts_code,trade_date,turnover_rate,volume_ratio,pe,pb,total_mv,circ_mv",
        )
        if not df.empty:
            logger.info(f"每日指标 {trade_date}: {len(df)} 条")
        return df

    # ─── 分钟线 ────────────────────────────────────────────────────────────────

    def get_minute(
        self,
        ts_code: str,
        freq: str = "15min",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取分钟线数据。
        freq: 1min / 5min / 15min / 30min / 60min

        注意：tushare 分钟线接口（stk_mins）需要 2000 积分以上。
        返回字段：ts_code, trade_time, open, high, low, close, vol, amount
        """
        kwargs: dict = {"ts_code": ts_code, "freq": freq}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date

        df = self._safe_call(self.pro.stk_mins, **kwargs)
        if not df.empty:
            logger.debug(f"分钟线({freq}) {ts_code}: {len(df)} 条")
        return df

    # ─── 资金流向 ──────────────────────────────────────────────────────────────

    def get_money_flow(self, trade_date: str) -> pd.DataFrame:
        """
        获取指定交易日个股资金流向。
        返回字段：ts_code, trade_date, buy_sm/md/lg/elg_amount, sell_*, net_mf_amount
        """
        logger.info(f"拉取资金流向 {trade_date}...")
        df = self._safe_call(
            self.pro.moneyflow,
            trade_date=trade_date,
        )
        if not df.empty:
            logger.info(f"资金流向 {trade_date}: {len(df)} 条")
        return df

    # ─── 北向资金 ──────────────────────────────────────────────────────────────

    def get_north_money(
        self,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        获取北向资金（沪股通 + 深股通）每日净买入。
        返回字段：trade_date, ggt_ss, ggt_sz, hgt, sgt, north_money, south_money
        """
        if end_date is None:
            end_date = self._today()
        df = self._safe_call(
            self.pro.moneyflow_hsgt,
            start_date=start_date,
            end_date=end_date,
        )
        if not df.empty:
            logger.info(f"北向资金: {len(df)} 条")
        return df

    # ─── 沪深股通十大成交股 ────────────────────────────────────────────────────

    def get_hsgt_top10(self, trade_date: str) -> pd.DataFrame:
        """
        获取沪深股通十大成交股。
        返回字段：trade_date, ts_code, name, close, change, rank, market_type 等
        """
        df = self._safe_call(
            self.pro.hsgt_top10,
            trade_date=trade_date,
        )
        if not df.empty:
            logger.info(f"沪深股通十大 {trade_date}: {len(df)} 条")
        return df

    # ─── 龙虎榜 ────────────────────────────────────────────────────────────────

    def get_top_list(self, trade_date: str) -> pd.DataFrame:
        """
        获取龙虎榜。
        返回字段：trade_date, ts_code, name, close, pct_chg, turnover_rate, reason 等
        """
        logger.info(f"拉取龙虎榜 {trade_date}...")
        df = self._safe_call(
            self.pro.top_list,
            trade_date=trade_date,
        )
        if not df.empty:
            logger.info(f"龙虎榜 {trade_date}: {len(df)} 条")
        return df

    # ─── 连通性测试 ────────────────────────────────────────────────────────────

    def ping(self) -> bool:
        """
        测试 tushare 连接是否正常。
        返回 True 表示可用，False 表示不可用（需检查代理）。
        """
        try:
            df = self._safe_call(
                self.pro.trade_cal,
                exchange="SSE",
                start_date="20240101",
                end_date="20240110",
                fields="cal_date,is_open",
            )
            ok = not df.empty
            if ok:
                logger.info("tushare 连接正常 ✓")
            else:
                logger.warning("tushare 返回空数据，请检查代理或 token")
            return ok
        except Exception as e:
            logger.warning(f"tushare 连接失败: {e}，请检查代理设置")
            return False


# ─── 全局单例 ──────────────────────────────────────────────────────────────────
tushare_client = TushareClient()
