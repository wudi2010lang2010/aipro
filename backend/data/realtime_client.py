"""
data/realtime_client.py
实时行情客户端 —— 腾讯财经（主）/ 新浪财经（辅）
无需代理，直接可用。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional

import requests
from loguru import logger

# ─── 大盘指数代码表 ────────────────────────────────────────────────────────────
INDEX_CODES: Dict[str, str] = {
    "sh000001": "上证指数",
    "sz399001": "深证成指",
    "sz399006": "创业板指",
    "sh000688": "科创50",
}

# ─── API 地址 ──────────────────────────────────────────────────────────────────
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q={codes}"
SINA_RANK_URL = (
    "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php"
    "/Market_Center.getHQNodeData"
)


# ─── 代码格式转换工具 ──────────────────────────────────────────────────────────


def tencent_to_ts(code: str) -> str:
    """
    腾讯格式 → tushare 格式
    sh000001 → 000001.SH
    sz000001 → 000001.SZ
    """
    code = code.strip().lower()
    if code.startswith("sh"):
        return f"{code[2:]}.SH"
    if code.startswith("sz"):
        return f"{code[2:]}.SZ"
    return code


def ts_to_tencent(ts_code: str) -> str:
    """
    tushare 格式 → 腾讯格式
    000001.SZ → sz000001
    600000.SH → sh600000
    """
    if "." not in ts_code:
        return ts_code
    symbol, market = ts_code.upper().split(".", 1)
    return f"{market.lower()}{symbol}"


def sina_to_ts(symbol: str) -> str:
    """新浪格式 → tushare 格式（同腾讯格式）"""
    return tencent_to_ts(symbol)


# ─── 主客户端 ──────────────────────────────────────────────────────────────────


class RealtimeClient:
    """
    实时行情客户端。

    数据来源：
    - 个股/指数实时报价：腾讯财经 qt.gtimg.cn
    - 涨幅榜 Top N：新浪财经排行接口
    - 板块行情：新浪财经行业接口

    延迟约 15-30 秒，满足 2-3 分钟轮询频率的使用需求。
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://finance.qq.com/",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )

    # ── 腾讯行情 ───────────────────────────────────────────────────────────────

    def _fetch_tencent(self, codes: List[str]) -> Dict[str, dict]:
        """
        调用腾讯 qt.gtimg.cn 接口，批量获取报价。

        codes 格式为腾讯格式列表，如 ['sh000001', 'sz000001']。
        返回 {ts_code: quote_dict} 字典。
        """
        if not codes:
            return {}

        url = TENCENT_QUOTE_URL.format(codes=",".join(codes))
        try:
            resp = self._session.get(url, timeout=8)
            resp.encoding = "gbk"
            return self._parse_tencent(resp.text)
        except requests.RequestException as exc:
            logger.warning(f"腾讯行情请求失败: {exc}")
            return {}

    @staticmethod
    def _parse_tencent(raw: str) -> Dict[str, dict]:
        """
        解析腾讯行情响应文本。

        腾讯数据格式（~分隔，从索引 0 开始）：
          0:类型  1:名称  2:代码  3:现价  4:昨收  5:开盘
          6:成交量(手)  33:最高  34:最低  37:成交额  38:换手率
          30:近期成交明细  31:时间(HH:MM:SS)
        """
        result: Dict[str, dict] = {}
        pattern = re.compile(r'v_(\w+)="([^"]*)"')

        for code, data_str in pattern.findall(raw):
            if not data_str:
                continue
            parts = data_str.split("~")
            if len(parts) < 35:
                continue
            try:
                price_str = parts[3].strip()
                pre_close_str = parts[4].strip()
                if not price_str or price_str == "0":
                    continue

                price = float(price_str)
                pre_close = float(pre_close_str) if pre_close_str else price
                open_price = float(parts[5]) if parts[5].strip() else price
                volume = float(parts[6]) if parts[6].strip() else 0.0
                high = float(parts[33]) if parts[33].strip() else price
                low = float(parts[34]) if parts[34].strip() else price

                amount_str = parts[37].strip() if len(parts) > 37 else "0"
                amount = float(amount_str) if amount_str else 0.0

                change = round(price - pre_close, 3)
                change_pct = (
                    round(change / pre_close * 100, 2) if pre_close > 0 else 0.0
                )

                ts_code = tencent_to_ts(code)
                result[ts_code] = {
                    "ts_code": ts_code,
                    "name": parts[1].strip(),
                    "price": price,
                    "pre_close": pre_close,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "volume": volume,  # 手
                    "amount": amount,  # 元
                    "change": change,
                    "change_pct": change_pct,
                    "update_time": datetime.now().strftime("%H:%M:%S"),
                }
            except (ValueError, IndexError) as exc:
                logger.debug(f"解析腾讯报价失败 [{code}]: {exc}")

        return result

    # ── 新浪排行 ───────────────────────────────────────────────────────────────

    def _fetch_sina_rank(
        self,
        node: str = "hs_a",
        sort: str = "changepercent",
        asc: int = 0,
        num: int = 20,
    ) -> List[dict]:
        """
        调用新浪财经排行接口。

        node 说明：
          hs_a    = 沪深A股
          sh_a    = 上证A股
          sz_a    = 深证A股

        sort 字段：changepercent(涨幅) / volume(成交量) / amount(成交额)
        asc: 0=降序, 1=升序
        """
        params = {
            "page": 1,
            "num": num,
            "sort": sort,
            "asc": asc,
            "node": node,
            "symbol": "",
        }
        try:
            resp = self._session.get(SINA_RANK_URL, params=params, timeout=10)
            resp.encoding = "gbk"
            return self._parse_sina_hq(resp.text)
        except requests.RequestException as exc:
            logger.warning(f"新浪排行请求失败 [{node}]: {exc}")
            return []

    @staticmethod
    def _parse_sina_hq(raw: str) -> List[dict]:
        """解析新浪行情/排行 JSON 响应。"""
        result: List[dict] = []
        try:
            import json

            data = json.loads(raw)
            if not isinstance(data, list):
                return result

            for item in data:
                symbol = item.get("symbol", "")
                if not symbol:
                    continue
                try:
                    result.append(
                        {
                            "ts_code": sina_to_ts(symbol),
                            "name": item.get("name", ""),
                            "price": float(item.get("trade", 0) or 0),
                            "pre_close": float(item.get("settlement", 0) or 0),
                            "open": float(item.get("open", 0) or 0),
                            "high": float(item.get("high", 0) or 0),
                            "low": float(item.get("low", 0) or 0),
                            "volume": float(item.get("volume", 0) or 0),
                            "amount": float(item.get("amount", 0) or 0),
                            "change_pct": float(item.get("changepercent", 0) or 0),
                            "change": float(item.get("change", 0) or 0),
                            "update_time": datetime.now().strftime("%H:%M:%S"),
                        }
                    )
                except (ValueError, TypeError) as exc:
                    logger.debug(f"解析新浪条目失败 {symbol}: {exc}")
        except Exception as exc:
            logger.warning(f"解析新浪行情响应失败: {exc}")
        return result

    # ── 公开接口 ───────────────────────────────────────────────────────────────

    def get_indices(self) -> List[dict]:
        """
        获取四大指数实时行情。

        Returns:
            list of dict, 包含上证、深证、创业板、科创50。
            即使某只拉取失败也会返回占位数据，不会抛出异常。
        """
        codes = list(INDEX_CODES.keys())
        data = self._fetch_tencent(codes)

        result: List[dict] = []
        for tencent_code, display_name in INDEX_CODES.items():
            ts_code = tencent_to_ts(tencent_code)
            if ts_code in data:
                item = dict(data[ts_code])
                item["display_name"] = display_name
            else:
                item = {
                    "ts_code": ts_code,
                    "name": display_name,
                    "display_name": display_name,
                    "price": 0.0,
                    "pre_close": 0.0,
                    "open": 0.0,
                    "high": 0.0,
                    "low": 0.0,
                    "volume": 0.0,
                    "amount": 0.0,
                    "change": 0.0,
                    "change_pct": 0.0,
                    "update_time": "--:--:--",
                }
            result.append(item)

        return result

    def get_quotes(self, ts_codes: List[str]) -> Dict[str, dict]:
        """
        批量获取个股实时报价。

        Args:
            ts_codes: tushare 格式代码列表，如 ['000001.SZ', '600000.SH']

        Returns:
            {ts_code: quote_dict}，拉取失败的代码不会出现在结果中。
        """
        if not ts_codes:
            return {}

        # 腾讯单次请求上限约 100 只，超过则分批
        batch_size = 80
        result: Dict[str, dict] = {}
        for i in range(0, len(ts_codes), batch_size):
            batch = ts_codes[i : i + batch_size]
            tencent_codes = [ts_to_tencent(c) for c in batch]
            result.update(self._fetch_tencent(tencent_codes))

        return result

    def get_quote(self, ts_code: str) -> Optional[dict]:
        """获取单只股票实时报价，失败返回 None。"""
        data = self.get_quotes([ts_code])
        return data.get(ts_code)

    def get_top_gainers(self, top_n: int = 20) -> List[dict]:
        """
        获取沪深 A 股涨幅榜 Top N。
        来源：新浪财经 hs_a 排行，按 changepercent 降序。
        """
        return self._fetch_sina_rank(
            node="hs_a", sort="changepercent", asc=0, num=top_n
        )

    def get_top_losers(self, top_n: int = 20) -> List[dict]:
        """获取跌幅榜 Top N。"""
        return self._fetch_sina_rank(
            node="hs_a", sort="changepercent", asc=1, num=top_n
        )

    def get_top_turnover(self, top_n: int = 20) -> List[dict]:
        """获取成交额榜 Top N。"""
        return self._fetch_sina_rank(node="hs_a", sort="amount", asc=0, num=top_n)

    def get_sectors(self) -> List[dict]:
        """
        获取板块涨跌幅排名。
        优先使用新浪申万行业分类（sw_a），失败时降级为概念板块（gn）。
        """
        result = self._fetch_sina_rank(node="sw_a", sort="changepercent", asc=0, num=30)
        if not result:
            logger.debug("sw_a 板块数据为空，尝试备用 gn 节点")
            result = self._fetch_sina_rank(
                node="gn", sort="changepercent", asc=0, num=30
            )
        return result

    def get_watchlist_quotes(self, ts_codes: List[str]) -> List[dict]:
        """
        获取自选股报价列表，保持传入顺序，失败的返回空占位。
        """
        if not ts_codes:
            return []

        data = self.get_quotes(ts_codes)
        result: List[dict] = []
        for code in ts_codes:
            if code in data:
                result.append(data[code])
            else:
                result.append(
                    {
                        "ts_code": code,
                        "name": "--",
                        "price": 0.0,
                        "change_pct": 0.0,
                        "update_time": "--:--:--",
                        "error": "获取失败",
                    }
                )
        return result


# ─── 全局单例 ──────────────────────────────────────────────────────────────────
realtime_client = RealtimeClient()
