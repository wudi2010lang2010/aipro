"""
indicators/signals.py
基于技术指标检测最近一根 K 线触发的交易信号。

用法：
    from indicators.signals import detect
    signals = detect(df)   # df 已经过 calculator.calculate() 处理
"""

from __future__ import annotations

import math

import pandas as pd

# ─── 工具函数 ──────────────────────────────────────────────────────────────────


def _valid(val) -> bool:
    """判断值是否为有效数字（非 None / NaN / inf）。"""
    if val is None:
        return False
    try:
        f = float(val)
        return not (math.isnan(f) or math.isinf(f))
    except (TypeError, ValueError):
        return False


def _get(row, col: str):
    """
    安全地从 pandas Series 中取值。
    如果列不存在或值为 NaN/None，返回 None。
    """
    try:
        val = row[col]
    except (KeyError, IndexError):
        return None
    return val if _valid(val) else None


def _all_valid(row, *cols: str) -> bool:
    """检查一行中的所有指定列均有有效值。"""
    return all(_get(row, c) is not None for c in cols)


# ─── 主函数 ────────────────────────────────────────────────────────────────────


def detect(df: pd.DataFrame) -> list[dict]:
    """
    检测最近一根 K 线触发的技术信号列表。

    参数
    ----
    df : pd.DataFrame
        已经过 calculator.calculate() 处理，按日期升序排列。
        至少需要 2 行数据。

    返回
    ----
    list[dict]
        每个元素格式：
        {
            "name": "信号名称",
            "type": "BUY" | "SELL" | "NEUTRAL",
            "desc": "信号说明"
        }
    """
    signals: list[dict] = []

    if df is None or len(df) < 2:
        return signals

    prev = df.iloc[-2]  # 倒数第二根 K 线
    curr = df.iloc[-1]  # 最新一根 K 线

    # ── 1. MACD 金叉 ──────────────────────────────────────────────────────────
    # DIF 从下方穿越 DEA（由负差转正差）
    if (
        _all_valid(prev, "macd", "macd_signal")
        and _all_valid(curr, "macd", "macd_signal")
        and float(prev["macd"]) < float(prev["macd_signal"])
        and float(curr["macd"]) > float(curr["macd_signal"])
    ):
        signals.append(
            {
                "name": "MACD金叉",
                "type": "BUY",
                "desc": "DIF上穿DEA，短期动能转强",
            }
        )

    # ── 2. MACD 死叉 ──────────────────────────────────────────────────────────
    # DIF 从上方穿越 DEA（由正差转负差）
    if (
        _all_valid(prev, "macd", "macd_signal")
        and _all_valid(curr, "macd", "macd_signal")
        and float(prev["macd"]) > float(prev["macd_signal"])
        and float(curr["macd"]) < float(curr["macd_signal"])
    ):
        signals.append(
            {
                "name": "MACD死叉",
                "type": "SELL",
                "desc": "DIF下穿DEA，短期动能转弱",
            }
        )

    # ── 3. MA 多头排列 ────────────────────────────────────────────────────────
    if _all_valid(curr, "ma5", "ma10", "ma20") and float(curr["ma5"]) > float(
        curr["ma10"]
    ) > float(curr["ma20"]):
        signals.append(
            {
                "name": "MA多头排列",
                "type": "BUY",
                "desc": f"MA5({curr['ma5']}) > MA10({curr['ma10']}) > MA20({curr['ma20']})，趋势向上",
            }
        )

    # ── 4. MA 空头排列 ────────────────────────────────────────────────────────
    if _all_valid(curr, "ma5", "ma10", "ma20") and float(curr["ma5"]) < float(
        curr["ma10"]
    ) < float(curr["ma20"]):
        signals.append(
            {
                "name": "MA空头排列",
                "type": "SELL",
                "desc": f"MA5({curr['ma5']}) < MA10({curr['ma10']}) < MA20({curr['ma20']})，趋势向下",
            }
        )

    # ── 5. 放量突破 ───────────────────────────────────────────────────────────
    # 条件：收盘价突破近20日最高价，且当日成交量 > 5日均量 × 1.5
    if len(df) >= 21 and _all_valid(curr, "vol_ma5"):
        # 取当前 K 线之前的 20 根 K 线最高价
        recent_high = df["high"].iloc[:-1].tail(20)
        if not recent_high.empty and recent_high.notna().any():
            high_20 = float(recent_high.max())
            close_curr = _get(curr, "close")
            vol_curr = _get(curr, "volume")
            vol_ma5_curr = _get(curr, "vol_ma5")

            if (
                close_curr is not None
                and vol_curr is not None
                and vol_ma5_curr is not None
                and float(close_curr) > high_20
                and float(vol_curr) > float(vol_ma5_curr) * 1.5
            ):
                signals.append(
                    {
                        "name": "放量突破",
                        "type": "BUY",
                        "desc": (
                            f"收盘({close_curr})突破近20日最高({round(high_20, 4)})，"
                            f"成交量({round(float(vol_curr), 0):.0f})超5日均量1.5倍"
                        ),
                    }
                )

    # ── 6. RSI 超买 ───────────────────────────────────────────────────────────
    rsi6_curr = _get(curr, "rsi6")
    if rsi6_curr is not None and float(rsi6_curr) > 80:
        signals.append(
            {
                "name": "RSI超买",
                "type": "SELL",
                "desc": f"RSI6={round(float(rsi6_curr), 2)}，已进入超买区（>80），注意回调风险",
            }
        )

    # ── 7. RSI 超卖 ───────────────────────────────────────────────────────────
    if rsi6_curr is not None and float(rsi6_curr) < 20:
        signals.append(
            {
                "name": "RSI超卖",
                "type": "BUY",
                "desc": f"RSI6={round(float(rsi6_curr), 2)}，已进入超卖区（<20），关注反弹机会",
            }
        )

    # ── 8. BOLL 突破上轨 ──────────────────────────────────────────────────────
    close_curr = _get(curr, "close")
    boll_upper_curr = _get(curr, "boll_upper")
    if (
        close_curr is not None
        and boll_upper_curr is not None
        and float(close_curr) > float(boll_upper_curr)
    ):
        signals.append(
            {
                "name": "BOLL突破上轨",
                "type": "SELL",
                "desc": (
                    f"收盘({close_curr})突破布林带上轨({boll_upper_curr})，"
                    "价格偏高，超买警示"
                ),
            }
        )

    # ── 9. BOLL 跌破下轨 ──────────────────────────────────────────────────────
    boll_lower_curr = _get(curr, "boll_lower")
    if (
        close_curr is not None
        and boll_lower_curr is not None
        and float(close_curr) < float(boll_lower_curr)
    ):
        signals.append(
            {
                "name": "BOLL跌破下轨",
                "type": "BUY",
                "desc": (
                    f"收盘({close_curr})跌破布林带下轨({boll_lower_curr})，"
                    "价格偏低，超卖关注"
                ),
            }
        )

    return signals
