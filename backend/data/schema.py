"""
data/schema.py
数据库 ORM 模型定义 + 建表初始化
包含全部 14 张表
"""

import os

from loguru import logger
from sqlalchemy import (
    Column,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase

# ─── ORM 基类 ──────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


# ─── 1. 股票基础信息 ────────────────────────────────────────────────────────


class Stock(Base):
    """股票基础信息（全市场 ~5500 只）"""

    __tablename__ = "stocks"

    ts_code = Column(String, primary_key=True)  # 如 000001.SZ
    symbol = Column(String, nullable=False)  # 如 000001
    name = Column(String, nullable=False)  # 股票名称
    market = Column(String)  # 主板/创业板/科创板
    industry = Column(String)  # 所属行业
    list_date = Column(String)  # 上市日期 YYYYMMDD
    is_st = Column(Integer, default=0)  # 是否 ST（1=是）
    is_active = Column(Integer, default=1)  # 是否正常交易
    updated_at = Column(String)  # 最后更新时间


# ─── 2. 交易日历 ────────────────────────────────────────────────────────────


class TradeCalendar(Base):
    """A 股交易日历（SSE）"""

    __tablename__ = "trade_calendar"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cal_date = Column(String, nullable=False, unique=True)  # YYYYMMDD
    is_open = Column(Integer, nullable=False)  # 1=交易日, 0=非交易日


# ─── 3. 日线数据（前复权）──────────────────────────────────────────────────


class DailyKline(Base):
    """日线 K 线数据，前复权存储"""

    __tablename__ = "daily_kline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)  # 股票代码
    trade_date = Column(String, nullable=False)  # 交易日期 YYYYMMDD
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)  # 成交量（手）
    amount = Column(Float)  # 成交额（千元）
    pct_chg = Column(Float)  # 涨跌幅 %

    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date", name="uq_daily_kline"),
        Index("ix_daily_kline_ts_date", "ts_code", "trade_date"),
    )


# ─── 4. 每日指标（换手率/量比/PE 等）──────────────────────────────────────


class DailyBasic(Base):
    """每日交易指标，来源 tushare daily_basic"""

    __tablename__ = "daily_basic"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    trade_date = Column(String, nullable=False)
    turnover_rate = Column(Float)  # 换手率 %
    volume_ratio = Column(Float)  # 量比
    pe = Column(Float)  # 市盈率（动）
    pb = Column(Float)  # 市净率
    total_mv = Column(Float)  # 总市值（万元）
    circ_mv = Column(Float)  # 流通市值（万元）

    __table_args__ = (
        UniqueConstraint("ts_code", "trade_date", name="uq_daily_basic"),
        Index("ix_daily_basic_ts_date", "ts_code", "trade_date"),
    )


# ─── 5. 分钟线（最近 60 交易日）────────────────────────────────────────────


class MinuteKline(Base):
    """分钟线 K 线数据，只保留最近 60 交易日"""

    __tablename__ = "minute_kline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    trade_time = Column(String, nullable=False)  # 如 2024-01-15 09:31:00
    freq = Column(String, default="15min")  # 1min/5min/15min/30min/60min
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)

    __table_args__ = (
        UniqueConstraint("ts_code", "trade_time", "freq", name="uq_minute_kline"),
        Index("ix_minute_kline_ts_time", "ts_code", "trade_time"),
    )


# ─── 6. 实时行情快照（滚动保留 7 天）──────────────────────────────────────


class RealtimeSnapshot(Base):
    """盘中实时行情轮询快照"""

    __tablename__ = "realtime_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    name = Column(String)
    price = Column(Float)
    pre_close = Column(Float)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    change = Column(Float)  # 涨跌额
    change_pct = Column(Float)  # 涨跌幅 %
    snapshot_time = Column(String, nullable=False)  # YYYY-MM-DD HH:MM:SS

    __table_args__ = (Index("ix_snapshot_ts_time", "ts_code", "snapshot_time"),)


# ─── 7. 个股资金流向 ────────────────────────────────────────────────────────


class MoneyFlow(Base):
    """个股资金流向，来源 tushare moneyflow"""

    __tablename__ = "money_flow"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    trade_date = Column(String, nullable=False)
    buy_sm_amount = Column(Float)  # 小单买入额（万元）
    sell_sm_amount = Column(Float)
    buy_md_amount = Column(Float)  # 中单买入额
    sell_md_amount = Column(Float)
    buy_lg_amount = Column(Float)  # 大单买入额
    sell_lg_amount = Column(Float)
    buy_elg_amount = Column(Float)  # 特大单买入额
    sell_elg_amount = Column(Float)
    net_mf_amount = Column(Float)  # 净流入额

    __table_args__ = (UniqueConstraint("ts_code", "trade_date", name="uq_money_flow"),)


# ─── 8. 北向资金 ────────────────────────────────────────────────────────────


class NorthMoney(Base):
    """北向资金每日汇总，来源 tushare moneyflow_hsgt"""

    __tablename__ = "north_money"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String, nullable=False, unique=True)
    ggt_ss = Column(Float)  # 港股通（沪）净买入（亿元）
    ggt_sz = Column(Float)  # 港股通（深）净买入
    hgt = Column(Float)  # 沪股通净买入
    sgt = Column(Float)  # 深股通净买入
    north_money = Column(Float)  # 北向资金合计
    south_money = Column(Float)  # 南向资金合计


# ─── 9. 龙虎榜 ──────────────────────────────────────────────────────────────


class DragonTiger(Base):
    """龙虎榜数据，来源 tushare top_list"""

    __tablename__ = "dragon_tiger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    trade_date = Column(String, nullable=False)
    name = Column(String)
    close = Column(Float)
    pct_chg = Column(Float)
    turnover_rate = Column(Float)
    reason = Column(String)  # 上榜原因

    __table_args__ = (Index("ix_dragon_tiger_date", "trade_date"),)


# ─── 10. 自选股 ─────────────────────────────────────────────────────────────


class Watchlist(Base):
    """用户自选股"""

    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False, unique=True)
    name = Column(String)
    note = Column(String)
    added_at = Column(String)


# ─── 11. 持仓 ───────────────────────────────────────────────────────────────


class Portfolio(Base):
    """当前持仓记录"""

    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    name = Column(String)
    cost_price = Column(Float, nullable=False)  # 成本价（含手续费）
    shares = Column(Integer, nullable=False)  # 持股数（股，非手）
    buy_date = Column(String, nullable=False)  # 买入日期 YYYY-MM-DD
    stop_loss = Column(Float)  # 止损价
    take_profit = Column(Float)  # 止盈价
    status = Column(String, default="OPEN")  # OPEN / CLOSED
    note = Column(String)
    created_at = Column(String)


# ─── 12. 交易记录 ───────────────────────────────────────────────────────────


class Transaction(Base):
    """历史买卖交易流水"""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    name = Column(String)
    action = Column(String, nullable=False)  # BUY / SELL
    price = Column(Float, nullable=False)
    shares = Column(Integer, nullable=False)
    commission = Column(Float)  # 手续费（买卖双向 0.025%）
    stamp_duty = Column(Float)  # 印花税（卖出 0.1%）
    net_amount = Column(Float)  # 实际金额（含费用）
    trade_date = Column(String, nullable=False)  # YYYY-MM-DD
    note = Column(String)

    __table_args__ = (Index("ix_transactions_date", "trade_date"),)


# ─── 13. AI 信号历史 ────────────────────────────────────────────────────────


class AISignal(Base):
    """Gemini AI 分析信号记录"""

    __tablename__ = "ai_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    name = Column(String)
    signal = Column(String, nullable=False)  # BUY / SELL / HOLD / WATCH
    confidence = Column(Integer)  # 0-100
    reasoning = Column(String)  # 分析理由
    buy_price = Column(Float)  # 建议买入价
    stop_loss = Column(Float)  # 建议止损价
    take_profit = Column(Float)  # 建议止盈价
    risk_level = Column(String)  # LOW / MEDIUM / HIGH
    hold_days = Column(Integer)  # 建议持仓天数
    key_risks = Column(String)  # JSON 字符串，风险列表
    model_version = Column(String)  # 使用的模型名称
    created_at = Column(String)

    __table_args__ = (
        Index("ix_ai_signals_ts_code", "ts_code"),
        Index("ix_ai_signals_created", "created_at"),
    )


# ─── 14. 选股结果快照（保留 30 天）────────────────────────────────────────


class ScreenerResult(Base):
    """选股扫描结果快照"""

    __tablename__ = "screener_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String, nullable=False)
    name = Column(String)
    preset_name = Column(String)  # 使用的预设策略名
    score = Column(Float)  # 综合评分 0-100
    price = Column(Float)
    change_pct = Column(Float)
    volume_ratio = Column(Float)
    turnover_rate = Column(Float)
    signal_count = Column(Integer)  # 命中技术信号数量
    signals = Column(String)  # JSON 字符串，信号名列表
    scanned_at = Column(String)  # 扫描时间

    __table_args__ = (Index("ix_screener_scanned_at", "scanned_at"),)


# ─── 数据库初始化 ────────────────────────────────────────────────────────────


def get_engine(db_path: str = None):
    """创建 SQLAlchemy Engine"""
    from config import config

    if db_path is None:
        db_path = config.DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},  # SQLite 多线程支持
    )
    return engine


def init_db(db_path: str = None) -> None:
    """
    初始化数据库，创建所有表。
    已存在的表不会被删除或修改（idempotent）。
    """
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)

    # 开启 WAL 模式，提升并发读写性能
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA synchronous=NORMAL"))
        conn.commit()

    logger.info(f"数据库初始化完成，共 {len(Base.metadata.tables)} 张表")
