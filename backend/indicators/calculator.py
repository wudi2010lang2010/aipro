"""
indicators/calculator.py
使用 ta 库计算技术指标，添加到 K 线 DataFrame 中。

支持指标：
  均线     : MA5 / MA10 / MA20 / MA60
  EMA      : EMA12 / EMA26
  MACD     : DIF / DEA / 柱状线
  RSI      : RSI6 / RSI12 / RSI24
  KDJ      : K / D / J（Stochastic 模拟）
  布林带   : 上轨 / 中轨 / 下轨（20, 2σ）
  量能均线 : VOL_MA5 / VOL_MA10
"""

from __future__ import annotations

import math

import pandas as pd
import ta

# ─── 公共工具 ──────────────────────────────────────────────────────────────────


def _round_series(s: pd.Series, decimals: int = 4) -> pd.Series:
    """对 Series 保留指定小数位，不影响 NaN。"""
    return s.round(decimals)


# ─── 主函数 ────────────────────────────────────────────────────────────────────


def calculate(df: pd.DataFrame) -> pd.DataFrame:
    """
    在传入的 DataFrame 上计算全套技术指标，并返回。

    参数
    ----
    df : pd.DataFrame
        必须包含列：open / high / low / close / volume
        行顺序：按日期 **升序**（最旧在前，最新在后）

    返回
    ----
    pd.DataFrame
        原 DataFrame 附加全部指标列；所有 NaN 替换为 None（JSON 兼容）。
    """
    if df is None or df.empty or len(df) < 2:
        return df

    # 确保数值列为 float，避免整数列导致 ta 计算异常
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = df[col].astype(float)

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # ── 简单移动均线（SMA）────────────────────────────────────────────────────
    df["ma5"] = _round_series(ta.trend.sma_indicator(close, window=5))
    df["ma10"] = _round_series(ta.trend.sma_indicator(close, window=10))
    df["ma20"] = _round_series(ta.trend.sma_indicator(close, window=20))
    df["ma60"] = _round_series(ta.trend.sma_indicator(close, window=60))

    # ── 指数移动均线（EMA）────────────────────────────────────────────────────
    df["ema12"] = _round_series(ta.trend.ema_indicator(close, window=12))
    df["ema26"] = _round_series(ta.trend.ema_indicator(close, window=26))

    # ── MACD（DIF / DEA / 柱）────────────────────────────────────────────────
    # macd()      → DIF = EMA12 - EMA26
    # macd_signal()  → DEA = EMA9(DIF)
    # macd_diff()    → 柱  = DIF - DEA  （中国习惯 ×2，此处保留原值）
    df["macd"] = _round_series(ta.trend.macd(close))
    df["macd_signal"] = _round_series(ta.trend.macd_signal(close))
    df["macd_hist"] = _round_series(ta.trend.macd_diff(close))

    # ── RSI ───────────────────────────────────────────────────────────────────
    df["rsi6"] = _round_series(ta.momentum.rsi(close, window=6))
    df["rsi12"] = _round_series(ta.momentum.rsi(close, window=12))
    df["rsi24"] = _round_series(ta.momentum.rsi(close, window=24))

    # ── KDJ（Stochastic 模拟）─────────────────────────────────────────────────
    # 参数：RSV 周期=9，平滑周期=3
    #   K = stoch(9, 3)            ≈ 随机 %K
    #   D = stoch_signal(9, 3)     ≈ 随机 %D
    #   J = 3K - 2D
    kdj_k = ta.momentum.stoch(high, low, close, window=9, smooth_window=3)
    kdj_d = ta.momentum.stoch_signal(high, low, close, window=9, smooth_window=3)
    kdj_j = 3.0 * kdj_k - 2.0 * kdj_d

    df["kdj_k"] = _round_series(kdj_k)
    df["kdj_d"] = _round_series(kdj_d)
    df["kdj_j"] = _round_series(kdj_j)

    # ── 布林带（20, 2σ）──────────────────────────────────────────────────────
    df["boll_upper"] = _round_series(
        ta.volatility.bollinger_hband(close, window=20, window_dev=2)
    )
    df["boll_mid"] = _round_series(ta.volatility.bollinger_mavg(close, window=20))
    df["boll_lower"] = _round_series(
        ta.volatility.bollinger_lband(close, window=20, window_dev=2)
    )

    # ── 成交量均线 ────────────────────────────────────────────────────────────
    df["vol_ma5"] = _round_series(ta.trend.sma_indicator(volume, window=5))
    df["vol_ma10"] = _round_series(ta.trend.sma_indicator(volume, window=10))

    # ── NaN → None（JSON 序列化兼容）────────────────────────────────────────
    # 注意：float 列中 .where() 仍会保留 NaN；实际 None 替换在路由层完成。
    # 此处用 object 类型转换确保 None 能正确写入。
    indicator_cols = [
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
    for col in indicator_cols:
        if col in df.columns:
            df[col] = df[col].astype(object).where(df[col].notna(), other=None)

    return df
