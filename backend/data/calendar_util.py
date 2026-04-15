"""
交易日历工具
优先查询数据库 trade_calendar 表；数据库无数据时降级为工作日判断（不含节假日）。
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

# ─── 交易时段常量 ──────────────────────────────────────────────────────────────
MORNING_START = time(9, 30)
MORNING_END = time(11, 30)
AFTERNOON_START = time(13, 0)
AFTERNOON_END = time(15, 0)
PRE_MARKET_START = time(9, 15)
PRE_MARKET_END = time(9, 25)


# ─── 基础判断 ──────────────────────────────────────────────────────────────────


def _is_weekday(d: date) -> bool:
    """是否工作日（周一=0 … 周五=4）"""
    return d.weekday() < 5


def is_trade_day(d: date | None = None) -> bool:
    """
    判断是否 A 股交易日。
    优先查询本地数据库 trade_calendar 表；
    表中无记录时降级为「仅排除周末」的简单判断。
    """
    if d is None:
        d = date.today()

    date_str = d.strftime("%Y%m%d")

    # ── 尝试查询数据库 ──────────────────────────────────────────
    try:
        from data.schema import TradeCalendar
        from data.storage import get_session

        with get_session() as session:
            record = (
                session.query(TradeCalendar)
                .filter(TradeCalendar.cal_date == date_str)
                .first()
            )
            if record is not None:
                return record.is_open == 1
    except Exception:
        pass  # 数据库未初始化 / 表为空时静默降级

    # ── 降级：仅判断工作日 ─────────────────────────────────────
    return _is_weekday(d)


# ─── 时段判断 ──────────────────────────────────────────────────────────────────


def is_market_open(dt: datetime | None = None) -> bool:
    """
    当前是否在正式交易时段。
    上午 09:30-11:30，下午 13:00-15:00，且为交易日。
    """
    if dt is None:
        dt = datetime.now()
    if not is_trade_day(dt.date()):
        return False
    t = dt.time()
    return (MORNING_START <= t <= MORNING_END) or (
        AFTERNOON_START <= t <= AFTERNOON_END
    )


def is_pre_market(dt: datetime | None = None) -> bool:
    """是否集合竞价阶段（09:15-09:25），且为交易日。"""
    if dt is None:
        dt = datetime.now()
    if not is_trade_day(dt.date()):
        return False
    return PRE_MARKET_START <= dt.time() <= PRE_MARKET_END


def is_lunch_break(dt: datetime | None = None) -> bool:
    """是否午间休市（11:30-13:00），且为交易日。"""
    if dt is None:
        dt = datetime.now()
    if not is_trade_day(dt.date()):
        return False
    return MORNING_END < dt.time() < AFTERNOON_START


def is_after_market(dt: datetime | None = None) -> bool:
    """是否已收盘（15:00 之后），且为交易日。"""
    if dt is None:
        dt = datetime.now()
    if not is_trade_day(dt.date()):
        return False
    return dt.time() >= AFTERNOON_END


def get_market_status(dt: datetime | None = None) -> tuple[str, str]:
    """
    返回当前市场状态码和中文描述。

    Returns:
        (status_code, description)
        status_code: PRE_MARKET | OPEN | LUNCH | CLOSED | BEFORE_OPEN | HOLIDAY
    """
    if dt is None:
        dt = datetime.now()

    if not is_trade_day(dt.date()):
        return "HOLIDAY", "非交易日"

    t = dt.time()

    if t < PRE_MARKET_START:
        return "BEFORE_OPEN", "开盘前"
    if PRE_MARKET_START <= t <= PRE_MARKET_END:
        return "PRE_MARKET", "集合竞价"
    if PRE_MARKET_END < t < MORNING_START:
        return "BEFORE_OPEN", "开盘前"
    if MORNING_START <= t <= MORNING_END:
        return "OPEN", "交易中"
    if MORNING_END < t < AFTERNOON_START:
        return "LUNCH", "午间休市"
    if AFTERNOON_START <= t <= AFTERNOON_END:
        return "OPEN", "交易中"
    return "CLOSED", "已收盘"


# ─── 交易日工具 ────────────────────────────────────────────────────────────────


def get_last_trade_day(d: date | None = None) -> date:
    """获取距离 d（默认今天）最近的上一个交易日。"""
    if d is None:
        d = date.today()
    prev = d - timedelta(days=1)
    for _ in range(10):
        if is_trade_day(prev):
            return prev
        prev -= timedelta(days=1)
    return prev  # fallback（极端情况）


def get_next_trade_day(d: date | None = None) -> date:
    """获取距离 d（默认今天）最近的下一个交易日。"""
    if d is None:
        d = date.today()
    nxt = d + timedelta(days=1)
    for _ in range(10):
        if is_trade_day(nxt):
            return nxt
        nxt += timedelta(days=1)
    return nxt


def format_trade_date(d: date | None = None) -> str:
    """格式化为 tushare 接口所需的日期字符串 YYYYMMDD。"""
    if d is None:
        d = date.today()
    return d.strftime("%Y%m%d")


def get_recent_trade_days(n: int = 20, end: date | None = None) -> list[str]:
    """
    获取最近 n 个交易日的日期列表（YYYYMMDD），按升序排列。
    end 默认为今天。
    """
    if end is None:
        end = date.today()
    results: list[str] = []
    cur = end
    while len(results) < n:
        if is_trade_day(cur):
            results.append(cur.strftime("%Y%m%d"))
        cur -= timedelta(days=1)
    results.reverse()
    return results
