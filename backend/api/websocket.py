"""
api/websocket.py
WebSocket 连接管理器 + 实时行情推送端点
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import List

from data.calendar_util import get_market_status, is_market_open
from data.realtime_client import realtime_client
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

# ─── 连接管理器 ────────────────────────────────────────────────────────────────


class ConnectionManager:
    """
    管理所有 WebSocket 长连接。
    支持广播、单播、断线自动清理。
    """

    def __init__(self):
        self._connections: List[WebSocket] = []

    @property
    def count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"WebSocket 新连接，当前共 {self.count} 个")

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info(f"WebSocket 断开，剩余 {self.count} 个")

    async def send(self, ws: WebSocket, message: dict) -> bool:
        """
        向单个客户端发送消息。
        返回 True 表示成功，False 表示连接已断开。
        """
        try:
            await ws.send_text(json.dumps(message, ensure_ascii=False))
            return True
        except Exception:
            self.disconnect(ws)
            return False

    async def broadcast(self, message: dict) -> None:
        """
        向所有已连接客户端广播消息。
        发送失败的连接自动移除。
        """
        if not self._connections:
            return

        msg_str = json.dumps(message, ensure_ascii=False)
        dead: List[WebSocket] = []

        for ws in list(self._connections):
            try:
                await ws.send_text(msg_str)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)


# 全局连接管理器单例
manager = ConnectionManager()


# ─── 消息构造工具 ──────────────────────────────────────────────────────────────


def _make_quote_message() -> dict:
    """
    构造行情推送消息。
    包含：四大指数、市场状态、推送时间。
    """
    indices = realtime_client.get_indices()
    status_code, status_desc = get_market_status()

    return {
        "type": "quote",
        "data": {
            "indices": indices,
            "market_status": status_code,
            "market_status_desc": status_desc,
            "is_open": is_market_open(),
            "push_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


def _make_pong_message() -> dict:
    return {"type": "pong", "time": datetime.now().strftime("%H:%M:%S")}


def _make_error_message(msg: str) -> dict:
    return {"type": "error", "message": msg}


def _make_status_message() -> dict:
    """推送服务端状态（连接数、市场状态）"""
    status_code, status_desc = get_market_status()
    return {
        "type": "status",
        "data": {
            "connections": manager.count,
            "market_status": status_code,
            "market_status_desc": status_desc,
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    }


# ─── 推送函数（供 APScheduler 定时调用）────────────────────────────────────────


async def push_market_data() -> None:
    """
    向所有客户端推送最新行情快照。
    由 main.py 中的 AsyncIOScheduler 定时触发（每 POLL_INTERVAL 秒）。
    无连接时直接跳过，不产生无效 API 调用。
    """
    if manager.count == 0:
        return

    try:
        msg = _make_quote_message()
        await manager.broadcast(msg)
        logger.debug(
            f"行情广播完成，推送 {manager.count} 个客户端，"
            f"指数数量: {len(msg['data']['indices'])}"
        )
    except Exception as exc:
        logger.error(f"行情推送失败: {exc}")


# ─── WebSocket 端点处理函数 ────────────────────────────────────────────────────


async def websocket_endpoint(ws: WebSocket) -> None:
    """
    WebSocket 主处理函数，挂载到 FastAPI app.websocket("/ws")。

    协议说明（客户端 → 服务端）：
      {"type": "ping"}                → 心跳保活，服务端回 pong
      {"type": "subscribe", "codes": ["000001.SZ"]}  → 订阅个股（预留）
      {"type": "get_status"}          → 获取服务端状态

    协议说明（服务端 → 客户端）：
      {"type": "quote",   "data": {...}}   行情推送（定时）
      {"type": "signal",  "data": {...}}   AI 信号（有信号时）
      {"type": "risk_alert", "data": {...}} 风控警告
      {"type": "status",  "data": {...}}   服务端状态
      {"type": "pong"}                     心跳回应
      {"type": "error",   "message": "..."} 错误信息
    """
    await manager.connect(ws)

    # 连接后立即推送一次行情和状态
    try:
        await manager.send(ws, _make_status_message())
        await manager.send(ws, _make_quote_message())
    except Exception as exc:
        logger.warning(f"初始推送失败: {exc}")

    # 消息循环
    try:
        while True:
            try:
                # 等待客户端消息，超时后继续循环（保持连接活跃）
                raw = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # 超时说明客户端 30 秒内没有消息，发 ping 探活
                alive = await manager.send(ws, {"type": "ping"})
                if not alive:
                    break
                continue

            # 解析消息
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send(ws, _make_error_message("消息格式错误，请发送 JSON"))
                continue

            msg_type = msg.get("type", "")

            if msg_type == "ping":
                await manager.send(ws, _make_pong_message())

            elif msg_type == "get_status":
                await manager.send(ws, _make_status_message())

            elif msg_type == "get_quote":
                # 客户端主动请求最新行情（非定时推送）
                try:
                    await manager.send(ws, _make_quote_message())
                except Exception as exc:
                    await manager.send(ws, _make_error_message(f"获取行情失败: {exc}"))

            elif msg_type == "subscribe":
                # 预留：订阅特定股票实时报价（Week 2+ 实现）
                codes = msg.get("codes", [])
                await manager.send(
                    ws,
                    {
                        "type": "subscribed",
                        "codes": codes,
                        "message": f"已订阅 {len(codes)} 只股票（功能开发中）",
                    },
                )

            else:
                await manager.send(ws, _make_error_message(f"未知消息类型: {msg_type}"))

    except WebSocketDisconnect:
        pass  # 正常断开
    except Exception as exc:
        logger.error(f"WebSocket 处理异常: {exc}")
    finally:
        manager.disconnect(ws)


# ─── 主动推送工具（供其他模块调用）────────────────────────────────────────────


async def broadcast_signal(signal_data: dict) -> None:
    """
    推送 AI 交易信号给所有客户端。
    由 ai/analyzer.py 产生信号后调用。
    """
    await manager.broadcast(
        {
            "type": "signal",
            "data": signal_data,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


async def broadcast_risk_alert(alert_data: dict) -> None:
    """
    推送风控警告给所有客户端。
    由 risk/engine.py 触发后调用。
    """
    await manager.broadcast(
        {
            "type": "risk_alert",
            "data": alert_data,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
