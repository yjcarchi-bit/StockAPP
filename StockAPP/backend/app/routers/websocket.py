"""
WebSocket 推送服务模块
=====================
提供实时数据推送功能，支持多客户端连接

特性:
- 多客户端连接管理
- 自动重连机制
- 心跳检测
- 消息广播
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect, APIRouter


class MessageType(Enum):
    """消息类型"""
    REALTIME_QUOTE = "realtime_quote"
    ALL_QUOTES = "all_quotes"
    STRATEGY_SIGNAL = "strategy_signal"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    STATUS = "status"


@dataclass
class ClientInfo:
    """客户端信息"""
    websocket: WebSocket
    connected_at: datetime
    last_heartbeat: datetime
    subscriptions: Set[str]
    
    def is_alive(self, timeout_seconds: int = 60) -> bool:
        """检查客户端是否存活"""
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < timeout_seconds


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    管理所有客户端连接，支持消息广播和单播
    
    Example:
        >>> manager = ConnectionManager()
        >>> await manager.connect(websocket)
        >>> await manager.broadcast({"type": "quote", "data": {...}})
    """
    
    def __init__(self, heartbeat_interval: int = 30):
        """
        初始化连接管理器
        
        Args:
            heartbeat_interval: 心跳间隔（秒）
        """
        self._clients: Dict[WebSocket, ClientInfo] = {}
        self.heartbeat_interval = heartbeat_interval
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket) -> None:
        """
        接受新连接
        
        Args:
            websocket: WebSocket连接
        """
        await websocket.accept()
        
        async with self._lock:
            self._clients[websocket] = ClientInfo(
                websocket=websocket,
                connected_at=datetime.now(),
                last_heartbeat=datetime.now(),
                subscriptions=set(),
            )
        
        await self._send_status(websocket, "connected")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """
        断开连接
        
        Args:
            websocket: WebSocket连接
        """
        async with self._lock:
            if websocket in self._clients:
                del self._clients[websocket]
    
    async def _send_status(self, websocket: WebSocket, status: str) -> None:
        """发送状态消息"""
        try:
            await websocket.send_json({
                "type": MessageType.STATUS.value,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "client_count": len(self._clients),
            })
        except Exception:
            pass
    
    async def send_json(self, websocket: WebSocket, data: dict) -> bool:
        """
        发送JSON消息
        
        Args:
            websocket: WebSocket连接
            data: 消息数据
            
        Returns:
            是否发送成功
        """
        try:
            await websocket.send_json(data)
            return True
        except Exception:
            await self.disconnect(websocket)
            return False
    
    async def broadcast(self, message: dict) -> int:
        """
        广播消息给所有客户端
        
        Args:
            message: 消息数据
            
        Returns:
            成功发送的客户端数量
        """
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        success_count = 0
        disconnected = []
        
        async with self._lock:
            clients = list(self._clients.items())
        
        for websocket, client_info in clients:
            if await self.send_json(websocket, message):
                success_count += 1
            else:
                disconnected.append(websocket)
        
        for ws in disconnected:
            await self.disconnect(ws)
        
        return success_count
    
    async def broadcast_quotes(self, quotes: dict) -> None:
        """
        广播行情数据
        
        Args:
            quotes: 行情数据字典
        """
        await self.broadcast({
            "type": MessageType.ALL_QUOTES.value,
            "data": quotes,
        })
    
    async def broadcast_signal(self, signal: dict) -> None:
        """
        广播策略信号
        
        Args:
            signal: 信号数据
        """
        await self.broadcast({
            "type": MessageType.STRATEGY_SIGNAL.value,
            "data": signal,
        })
    
    async def send_heartbeat(self, websocket: WebSocket) -> None:
        """发送心跳"""
        async with self._lock:
            if websocket in self._clients:
                self._clients[websocket].last_heartbeat = datetime.now()
        
        await self.send_json(websocket, {
            "type": MessageType.HEARTBEAT.value,
            "timestamp": datetime.now().isoformat(),
        })
    
    async def handle_heartbeat(self, websocket: WebSocket) -> None:
        """处理心跳响应"""
        async with self._lock:
            if websocket in self._clients:
                self._clients[websocket].last_heartbeat = datetime.now()
    
    def get_client_count(self) -> int:
        """获取客户端数量"""
        return len(self._clients)
    
    def get_client_info(self, websocket: WebSocket) -> Optional[ClientInfo]:
        """获取客户端信息"""
        return self._clients.get(websocket)
    
    async def cleanup_dead_connections(self, timeout_seconds: int = 60) -> int:
        """
        清理无响应的连接
        
        Args:
            timeout_seconds: 超时时间
            
        Returns:
            清理的连接数量
        """
        dead_clients = []
        
        async with self._lock:
            for websocket, client_info in self._clients.items():
                if not client_info.is_alive(timeout_seconds):
                    dead_clients.append(websocket)
        
        for ws in dead_clients:
            await self.disconnect(ws)
        
        return len(dead_clients)


manager = ConnectionManager()


async def websocket_handler(websocket: WebSocket) -> None:
    """
    WebSocket 消息处理
    
    Args:
        websocket: WebSocket连接
    """
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "heartbeat":
                await manager.handle_heartbeat(websocket)
                await manager.send_heartbeat(websocket)
            
            elif message_type == "ping":
                await manager.send_heartbeat(websocket)
            
            elif message_type == "subscribe":
                pass
            
            else:
                await manager.send_json(websocket, {
                    "type": MessageType.ERROR.value,
                    "message": f"未知消息类型: {message_type}",
                })
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        await manager.disconnect(websocket)


router = APIRouter()


@router.websocket("/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """
    实时数据 WebSocket 端点
    
    连接后可接收:
    - all_quotes: 所有ETF行情
    - strategy_signal: 策略信号
    
    发送消息:
    - heartbeat: 心跳请求
    - ping: 心跳请求
    """
    await websocket_handler(websocket)


@router.get("/status")
async def get_websocket_status():
    """获取 WebSocket 服务状态"""
    from core.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    scheduler_status = scheduler.get_status() if scheduler else None
    
    return {
        "client_count": manager.get_client_count(),
        "scheduler": scheduler_status,
    }
