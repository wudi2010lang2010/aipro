"""
api/routes/market.py
市场行情相关 API 路由

端点列表：
  GET /api/market/indices       大盘指数实时行情
  GET /api/market/top-gainers   涨幅榜 Top N
  GET /api/market/top-losers    跌幅榜 Top N
  GET /api/market/top-turnover  成交额榜 Top N
  GET /api/market/sectors       板块涨跌幅排名
  GET /api/market/north-money   北向资金近 N 日
  GET /api/market/status        当前市场状态
  GET /api/market/watchlist     自选股实时报价
  POST /api/market/watchlist    添加自选股
  DELETE /api/market/watchlist/{ts_code}  删除自选股
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from data.calendar_util import get_market_status, is_trade_day
from data.realtime_client import realtime_client
from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

router = APIRouter(prefix="/api/market", tags=["market"])


# ─── 响应模型 ──────────────────────────────────────────────────────────────────


class QuoteItem(BaseModel):
    ts_code: str
    name: str
    price: float = 0.0
    pre_close: float = 0.0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    volume: float = 0.0
    amount: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    update_time: str = "--:--:--"


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: object = None
    time: str = ""


def _ok(data) -> dict:
    """统一成功响应格式"""
    return {
        "code": 0,
        "message": "ok",
        "data": data,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _err(msg: str, code: int = 500) -> dict:
    """统一错误响应格式"""
    return {
        "code": code,
        "message": msg,
        "data": None,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─── 大盘指数 ──────────────────────────────────────────────────────────────────


@router.get("/indices", summary="大盘指数实时行情")
def get_indices():
    """
    获取四大指数实时报价：上证指数、深证成指、创业板指、科创50。

    数据来源：腾讯财经实时 API，延迟约 15-30 秒。
    非交易时段返回上次收盘数据（若可用）。
    """
    try:
        data = realtime_client.get_indices()
        status_code, status_desc = get_market_status()
        return _ok(
            {
                "indices": data,
                "market_status": status_code,
                "market_desc": status_desc,
            }
        )
    except Exception as exc:
        logger.error(f"获取大盘指数失败: {exc}")
        return _err(f"获取大盘指数失败: {exc}")


# ─── 涨跌幅榜 / 成交额榜 ──────────────────────────────────────────────────────


@router.get("/top-gainers", summary="涨幅榜")
def get_top_gainers(
    n: int = Query(default=20, ge=5, le=100, description="返回条数，默认 20"),
):
    """
    获取沪深 A 股涨幅榜 Top N，按涨幅降序排列。
    数据来源：新浪财经排行接口。
    """
    try:
        data = realtime_client.get_top_gainers(n)
        return _ok(data)
    except Exception as exc:
        logger.error(f"获取涨幅榜失败: {exc}")
        return _err(str(exc))


@router.get("/top-losers", summary="跌幅榜")
def get_top_losers(
    n: int = Query(default=20, ge=5, le=100, description="返回条数，默认 20"),
):
    """
    获取沪深 A 股跌幅榜 Top N，按涨幅升序排列。
    """
    try:
        data = realtime_client.get_top_losers(n)
        return _ok(data)
    except Exception as exc:
        logger.error(f"获取跌幅榜失败: {exc}")
        return _err(str(exc))


@router.get("/top-turnover", summary="成交额榜")
def get_top_turnover(
    n: int = Query(default=20, ge=5, le=100, description="返回条数，默认 20"),
):
    """
    获取沪深 A 股成交额榜 Top N，按成交额降序排列。
    """
    try:
        data = realtime_client.get_top_turnover(n)
        return _ok(data)
    except Exception as exc:
        logger.error(f"获取成交额榜失败: {exc}")
        return _err(str(exc))


# ─── 板块行情 ──────────────────────────────────────────────────────────────────


@router.get("/sectors", summary="板块涨跌幅排名")
def get_sectors():
    """
    获取申万行业板块涨跌幅排名，按涨幅降序。
    数据来源：新浪财经行业分类接口。
    """
    try:
        data = realtime_client.get_sectors()
        return _ok(data)
    except Exception as exc:
        logger.error(f"获取板块行情失败: {exc}")
        return _err(str(exc))


# ─── 北向资金 ──────────────────────────────────────────────────────────────────


@router.get("/north-money", summary="北向资金近 N 日")
def get_north_money(
    days: int = Query(
        default=20, ge=1, le=120, description="查询天数，默认 20 个交易日"
    ),
):
    """
    从本地数据库查询北向资金（沪深股通）近 N 个交易日净买入数据。
    数据来源：盘后由 tushare moneyflow_hsgt 接口同步。
    """
    try:
        from data.schema import NorthMoney
        from data.storage import get_session

        with get_session() as session:
            records = (
                session.query(NorthMoney)
                .order_by(NorthMoney.trade_date.desc())
                .limit(days)
                .all()
            )

        data = [
            {
                "trade_date": r.trade_date,
                "north_money": r.north_money,  # 北向合计（亿元）
                "hgt": r.hgt,  # 沪股通
                "sgt": r.sgt,  # 深股通
                "ggt_ss": r.ggt_ss,  # 港股通（沪）
                "ggt_sz": r.ggt_sz,  # 港股通（深）
                "south_money": r.south_money,
            }
            for r in reversed(records)  # 返回升序（oldest → newest）
        ]

        return _ok(data)
    except Exception as exc:
        logger.error(f"查询北向资金失败: {exc}")
        return _err(str(exc))


# ─── 市场状态 ──────────────────────────────────────────────────────────────────


@router.get("/status", summary="当前市场状态")
def get_market_status_api():
    """
    返回当前 A 股市场状态。

    status 枚举值：
    - BEFORE_OPEN  开盘前（08:00-09:25）
    - PRE_MARKET   集合竞价（09:15-09:25）
    - OPEN         交易中（09:30-11:30 / 13:00-15:00）
    - LUNCH        午间休市（11:30-13:00）
    - CLOSED       已收盘（15:00 后）
    - HOLIDAY      非交易日
    """
    now = datetime.now()
    status_code, status_desc = get_market_status(now)
    return _ok(
        {
            "status": status_code,
            "desc": status_desc,
            "is_trade_day": is_trade_day(now.date()),
            "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


# ─── 自选股 ────────────────────────────────────────────────────────────────────


class WatchlistAddBody(BaseModel):
    ts_code: str
    note: Optional[str] = None


@router.get("/watchlist", summary="自选股实时报价")
def get_watchlist():
    """
    获取用户自选股列表及实时报价。
    自选股数据存储在本地 SQLite watchlist 表中。
    """
    try:
        from data.schema import Watchlist
        from data.storage import get_session

        with get_session() as session:
            items = session.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
            ts_codes = [w.ts_code for w in items]
            notes = {w.ts_code: w.note for w in items}

        if not ts_codes:
            return _ok([])

        # 批量拉取实时报价
        quotes = realtime_client.get_watchlist_quotes(ts_codes)

        # 附加备注信息
        for q in quotes:
            q["note"] = notes.get(q["ts_code"], "")

        return _ok(quotes)
    except Exception as exc:
        logger.error(f"获取自选股失败: {exc}")
        return _err(str(exc))


@router.post("/watchlist", summary="添加自选股")
def add_watchlist(body: WatchlistAddBody):
    """
    添加股票到自选股列表。ts_code 已存在时返回成功（幂等）。
    """
    try:
        from data.schema import Watchlist
        from data.storage import get_session

        ts_code = body.ts_code.upper().strip()

        # 先查名称（从 stocks 表）
        from data.schema import Stock

        with get_session() as session:
            existing = (
                session.query(Watchlist).filter(Watchlist.ts_code == ts_code).first()
            )
            if existing:
                return _ok(
                    {"ts_code": ts_code, "added": False, "reason": "already exists"}
                )

            # 查股票名称
            stock = session.query(Stock).filter(Stock.ts_code == ts_code).first()
            name = stock.name if stock else ""

            session.add(
                Watchlist(
                    ts_code=ts_code,
                    name=name,
                    note=body.note or "",
                    added_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

        logger.info(f"自选股已添加: {ts_code} {name}")
        return _ok({"ts_code": ts_code, "name": name, "added": True})
    except Exception as exc:
        logger.error(f"添加自选股失败: {exc}")
        return _err(str(exc))


@router.delete("/watchlist/{ts_code}", summary="删除自选股")
def remove_watchlist(ts_code: str):
    """从自选股列表删除指定股票。"""
    try:
        from data.schema import Watchlist
        from data.storage import get_session

        ts_code = ts_code.upper().strip()
        with get_session() as session:
            deleted = (
                session.query(Watchlist).filter(Watchlist.ts_code == ts_code).delete()
            )

        if deleted == 0:
            return _err(f"{ts_code} 不在自选股列表中", code=404)

        logger.info(f"自选股已删除: {ts_code}")
        return _ok({"ts_code": ts_code, "deleted": True})
    except Exception as exc:
        logger.error(f"删除自选股失败: {exc}")
        return _err(str(exc))


# ─── 单只股票实时报价（供 K 线页面头部信息使用）──────────────────────────────


@router.get("/quote/{ts_code}", summary="单只股票实时报价")
def get_single_quote(ts_code: str):
    """
    获取单只股票的实时报价。
    ts_code 格式：000001.SZ / 600000.SH
    """
    try:
        ts_code = ts_code.upper().strip()
        quote = realtime_client.get_quote(ts_code)
        if quote is None:
            return _err(f"无法获取 {ts_code} 的报价，请检查代码是否正确", code=404)
        return _ok(quote)
    except Exception as exc:
        logger.error(f"获取单只报价失败 {ts_code}: {exc}")
        return _err(str(exc))
