"""
api/routes/kline.py
K 线数据、技术指标、交易信号及股票搜索 API 路由

端点列表：
  GET /api/kline/search          股票名称 / 代码模糊搜索
  GET /api/kline/{ts_code}       K 线 + 技术指标 + 信号

注意：/search 必须声明在 /{ts_code} 之前，否则 FastAPI 会将
"search" 当作 ts_code 路径参数捕获。
"""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Query
from loguru import logger

router = APIRouter(prefix="/api/kline", tags=["kline"])

# ─── 指标列顺序（决定响应 JSON 字段顺序）─────────────────────────────────────

_INDICATOR_COLS: list[str] = [
    "ma5",
    "ma10",
    "ma20",
    "ma60",
    "ema12",
    "ema26",
    "macd",
    "macd_signal",
    "macd_hist",
    "rsi6",
    "rsi12",
    "rsi24",
    "kdj_k",
    "kdj_d",
    "kdj_j",
    "boll_upper",
    "boll_mid",
    "boll_lower",
    "vol_ma5",
    "vol_ma10",
]

# ─── 工具函数 ──────────────────────────────────────────────────────────────────


def _safe(val, decimals: int = 4):
    """
    将 NaN / inf / None 统一转换为 None；
    float 保留 decimals 位小数；其他类型原样返回。
    """
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(val, decimals)
    # pandas / numpy 标量
    try:
        import numpy as np  # numpy 是 pandas 依赖，必然存在

        if isinstance(val, (np.floating,)):
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return None
            return round(f, decimals)
        if isinstance(val, (np.integer,)):
            return int(val)
    except ImportError:
        pass
    return val


def _format_trade_date(d: str) -> str:
    """
    将 tushare 风格的 YYYYMMDD 转换为 YYYY-MM-DD。
    若已带连字符则原样返回。
    """
    d = str(d).strip()
    if len(d) == 8 and "-" not in d:
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return d


def _row_to_dict(row: pd.Series, df_columns) -> dict:
    """将 DataFrame 行转换为 JSON 可序列化的字典。"""
    item: dict = {
        "time": row["time"],
        "open": _safe(row["open"]),
        "high": _safe(row["high"]),
        "low": _safe(row["low"]),
        "close": _safe(row["close"]),
        "volume": _safe(row["volume"]),
    }
    # 可选字段
    if "amount" in df_columns:
        item["amount"] = _safe(row["amount"])
    if "pct_chg" in df_columns:
        item["pct_chg"] = _safe(row["pct_chg"])

    # 技术指标
    for col in _INDICATOR_COLS:
        if col in df_columns:
            item[col] = _safe(row[col])
        else:
            item[col] = None

    return item


# ─── 股票搜索（必须在 /{ts_code} 之前注册！）──────────────────────────────────


@router.get("/search", summary="股票名称 / 代码模糊搜索")
def search_stocks(
    q: str = Query(
        ..., min_length=1, description="股票名称、代码（symbol）或 ts_code 关键词"
    ),
):
    """
    在本地 stocks 表中模糊匹配 name / symbol / ts_code，返回最多 20 条结果。

    示例：
      GET /api/kline/search?q=平安
      GET /api/kline/search?q=000001
    """
    try:
        from data.schema import Stock
        from data.storage import get_session

        keyword = q.strip()
        pattern = f"%{keyword}%"

        with get_session() as session:
            records = (
                session.query(Stock)
                .filter(
                    Stock.name.ilike(pattern)
                    | Stock.symbol.ilike(pattern)
                    | Stock.ts_code.ilike(pattern)
                )
                .order_by(Stock.ts_code)
                .limit(20)
                .all()
            )
            data = [
                {
                    "ts_code": r.ts_code,
                    "name": r.name,
                    "market": r.market or "",
                }
                for r in records
            ]

        return {"code": 0, "data": data}

    except Exception as exc:
        logger.error(f"搜索股票失败 [q={q!r}]: {exc}")
        return {"code": 500, "message": str(exc)}


# ─── K 线 + 技术指标 + 信号 ────────────────────────────────────────────────────


@router.get("/{ts_code}", summary="K 线数据 + 技术指标 + 交易信号")
def get_kline(
    ts_code: str,
    period: str = Query(
        default="daily",
        description="K 线周期：daily / 60min / 30min / 15min",
    ),
    limit: int = Query(
        default=250,
        ge=1,
        le=1000,
        description="返回 K 线数量（最多 1000）",
    ),
):
    """
    从本地数据库读取历史 K 线，附加技术指标及最新交易信号。

    - **period=daily**：读取 daily_kline 表，time 格式为 YYYY-MM-DD
    - **period=60min/30min/15min**：读取 minute_kline 表，time 格式为 YYYY-MM-DD HH:MM:SS

    返回格式：
    ```json
    {
      "code": 0,
      "data": {
        "ts_code": "000001.SZ",
        "period": "daily",
        "klines": [...],
        "signals": [...],
        "count": 250
      }
    }
    ```
    """
    try:
        ts_code = ts_code.upper().strip()

        # ── 1. 从数据库读取原始 K 线 ─────────────────────────────────────────
        from data.schema import DailyKline, MinuteKline
        from data.storage import get_session

        rows: list[dict] = []

        with get_session() as session:
            if period == "daily":
                records = (
                    session.query(DailyKline)
                    .filter(DailyKline.ts_code == ts_code)
                    .order_by(DailyKline.trade_date.desc())
                    .limit(limit)
                    .all()
                )
                rows = [
                    {
                        "time": _format_trade_date(r.trade_date),
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume,
                        "amount": r.amount,
                        "pct_chg": r.pct_chg,
                    }
                    for r in records
                ]
            else:
                # 分钟线，按 freq 字段过滤
                valid_freqs = {"60min", "30min", "15min", "5min", "1min"}
                freq = period if period in valid_freqs else "15min"

                records = (
                    session.query(MinuteKline)
                    .filter(
                        MinuteKline.ts_code == ts_code,
                        MinuteKline.freq == freq,
                    )
                    .order_by(MinuteKline.trade_time.desc())
                    .limit(limit)
                    .all()
                )
                rows = [
                    {
                        "time": r.trade_time,  # 已是 YYYY-MM-DD HH:MM:SS
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume,
                        "amount": r.amount,
                        "pct_chg": None,
                    }
                    for r in records
                ]

        # ── 2. 无数据时触发后台加载，返回 loading 状态 ───────────────────────
        if not rows:
            if period == "daily":
                # 后台异步拉取该股票日线数据，不阻塞本次请求
                from data.initializer import trigger_kline_load

                trigger_kline_load(ts_code, start_date="20230101")
                loading_msg = "数据加载中，约 10 秒后刷新页面即可查看"
            else:
                loading_msg = "暂无分钟线数据，请配置代理后通过 tushare 加载"

            return {
                "code": 0,
                "data": {
                    "ts_code": ts_code,
                    "period": period,
                    "klines": [],
                    "signals": [],
                    "count": 0,
                    "loading": period == "daily",
                    "message": loading_msg,
                },
            }

        # ── 3. 升序排列（旧 → 新），技术指标计算需要时序正确 ─────────────────
        rows.reverse()

        # ── 4. 构建 DataFrame ─────────────────────────────────────────────────
        df = pd.DataFrame(rows)

        # 强制转换数值列，防止 None 混入导致计算异常
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # ── 5. 计算技术指标 ───────────────────────────────────────────────────
        from indicators.calculator import calculate

        df = calculate(df)

        # ── 6. 检测交易信号 ───────────────────────────────────────────────────
        from indicators.signals import detect

        signals = detect(df)

        # ── 7. 序列化为 JSON 响应 ─────────────────────────────────────────────
        df_columns = set(df.columns)
        klines = [_row_to_dict(row, df_columns) for _, row in df.iterrows()]

        return {
            "code": 0,
            "data": {
                "ts_code": ts_code,
                "period": period,
                "klines": klines,
                "signals": signals,
                "count": len(klines),
            },
        }

    except Exception as exc:
        logger.error(f"获取 K 线失败 [{ts_code} {period}]: {exc}")
        return {"code": 500, "message": str(exc)}
