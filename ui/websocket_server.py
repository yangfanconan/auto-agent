"""
WebSocket 服务端模块
实现控制台 IO 与 Web 页面的实时双向可视化交互

支持：
- 实时推送结构化 IO 消息
- 接收用户指令和操作确认
- 心跳检测、断线重连
- 消息广播和单播
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional, Callable, Any
from pathlib import Path

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    websockets = None

try:
    from ..utils import get_logger, load_config
    from ..core.console_io import IOMessage, IOType, IOSource
    from ..core.events import subscribe_async, publish_event
except ImportError:
    from utils import get_logger, load_config
    from core.console_io import IOMessage, IOType, IOSource
    from core.events import subscribe_async, publish_event


class WebSocketManager:
    """WebSocket 连接管理器"""
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        heartbeat_interval: float = 30.0,
        on_message: Optional[Callable[[str, Dict], Any]] = None
    ):
        self.logger = get_logger()
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        self.on_message = on_message
        
        # 连接管理
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.connection_info: Dict[str, Dict] = {}
        
        # 状态
        self._server = None
        self._running = False
        self._stop_event = asyncio.Event()
        
        # 消息队列
        self._broadcast_queue = asyncio.Queue()
        
        self.logger.info(f"WebSocketManager 已初始化 (host={host}, port={port})")
    
    async def start_server(self):
        """启动 WebSocket 服务器"""
        if websockets is None:
            self.logger.error("websockets 库未安装，请运行：pip install websockets")
            return
        
        try:
            self._server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=self.heartbeat_interval,
                ping_timeout=10,
            )
            self._running = True
            self.logger.info(f"WebSocket 服务器已启动：ws://{self.host}:{self.port}")
            
            # 启动广播任务
            asyncio.create_task(self._broadcast_loop())
            
            # 等待停止信号
            await self._stop_event.wait()
            
        except Exception as e:
            self.logger.error(f"WebSocket 服务器启动失败：{e}")
            raise
    
    async def stop_server(self):
        """停止 WebSocket 服务器"""
        self._running = False
        self._stop_event.set()
        
        # 关闭所有连接
        for ws_id in list(self.connections.keys()):
            await self._close_connection(ws_id)
        
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        self.logger.info("WebSocket 服务器已停止")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol):
        """处理 WebSocket 连接"""
        ws_id = f"ws_{id(websocket)}_{datetime.now().strftime('%H%M%S')}"
        
        # 注册连接
        self.connections[ws_id] = websocket
        self.connection_info[ws_id] = {
            "connected_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "type": "browser",
        }
        
        self.logger.info(f"WebSocket 连接已建立：{ws_id}")
        
        # 发送欢迎消息
        await self._send_to_connection(
            ws_id,
            {
                "type": "system",
                "event": "connected",
                "data": {"ws_id": ws_id, "timestamp": datetime.now().timestamp()},
            }
        )
        
        try:
            # 接收消息循环
            async for message in websocket:
                self.connection_info[ws_id]["last_activity"] = datetime.now().isoformat()
                await self._handle_message(ws_id, message)
        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"WebSocket 连接已关闭：{ws_id}")
        except Exception as e:
            self.logger.error(f"WebSocket 连接异常：{ws_id} - {e}")
        finally:
            await self._close_connection(ws_id)
    
    async def _handle_message(self, ws_id: str, message: str):
        """处理 WebSocket 消息"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "unknown")
            
            self.logger.debug(f"收到 WebSocket 消息 [{ws_id}]: {msg_type}")
            
            # 调用回调
            if self.on_message:
                try:
                    result = await self.on_message(ws_id, data)
                    if result:
                        await self._send_to_connection(ws_id, result)
                except Exception as e:
                    self.logger.error(f"消息回调失败：{e}")
            
            # 发布事件
            publish_event(
                event_type="websocket.message",
                payload={
                    "ws_id": ws_id,
                    "type": msg_type,
                    "data": data,
                },
                source="websocket"
            )
            
        except json.JSONDecodeError:
            self.logger.warning(f"无效的 JSON 消息：{message[:100]}")
        except Exception as e:
            self.logger.error(f"消息处理失败：{e}")
    
    async def _close_connection(self, ws_id: str):
        """关闭连接"""
        if ws_id in self.connections:
            try:
                await self.connections[ws_id].close()
            except:
                pass
            del self.connections[ws_id]
        
        if ws_id in self.connection_info:
            del self.connection_info[ws_id]
    
    async def send_message(self, message: Dict):
        """广播消息到所有连接"""
        await self._broadcast_queue.put(message)
    
    async def send_to_connection(self, ws_id: str, message: Dict):
        """发送消息到指定连接"""
        await self._send_to_connection(ws_id, message)
    
    async def _send_to_connection(self, ws_id: str, message: Dict):
        """内部方法：发送消息到指定连接"""
        if ws_id not in self.connections:
            return
        
        try:
            websocket = self.connections[ws_id]
            await websocket.send(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            self.logger.warning(f"发送消息失败 [{ws_id}]: {e}")
            await self._close_connection(ws_id)
    
    async def _broadcast_loop(self):
        """广播循环"""
        while self._running:
            try:
                message = await asyncio.wait_for(self._broadcast_queue.get(), timeout=1.0)
                
                # 广播到所有连接
                tasks = [
                    self._send_to_connection(ws_id, message)
                    for ws_id in list(self.connections.keys())
                ]
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"广播失败：{e}")
    
    def get_connection_count(self) -> int:
        """获取连接数"""
        return len(self.connections)
    
    def get_connection_info(self) -> Dict:
        """获取连接信息"""
        return {
            "count": len(self.connections),
            "connections": list(self.connection_info.values()),
        }


class WebSocketIOBridge:
    """WebSocket IO 桥接器 - 连接 ConsoleIO 和 WebSocket"""
    
    def __init__(
        self,
        websocket_manager: WebSocketManager,
        console_redirector: Optional[Any] = None
    ):
        self.logger = get_logger()
        self.ws_manager = websocket_manager
        self.console_io = console_redirector
        
        # 订阅事件
        self._setup_event_subscribers()
        
        self.logger.info("WebSocketIOBridge 已初始化")
    
    def _setup_event_subscribers(self):
        """设置事件订阅"""
        # 订阅 IO 消息
        subscribe_async("system.io", self._on_io_message)
        subscribe_async("task.started", self._on_task_event)
        subscribe_async("task.completed", self._on_task_event)
        subscribe_async("task.failed", self._on_task_event)
        subscribe_async("tool.called", self._on_tool_event)
    
    async def _on_io_message(self, event):
        """处理 IO 消息"""
        payload = event.payload
        await self.ws_manager.send_message({
            "type": "io",
            "event": payload.get("type", "output"),
            "data": payload,
        })
    
    async def _on_task_event(self, event):
        """处理任务事件"""
        await self.ws_manager.send_message({
            "type": "task",
            "event": event.type,
            "data": event.payload,
        })
    
    async def _on_tool_event(self, event):
        """处理工具事件"""
        await self.ws_manager.send_message({
            "type": "tool",
            "event": event.type,
            "data": event.payload,
        })
    
    async def handle_websocket_message(self, ws_id: str, data: Dict) -> Optional[Dict]:
        """处理 WebSocket 消息（回调）"""
        msg_type = data.get("type")
        
        if msg_type == "command":
            # 用户指令
            command = data.get("command", "")
            self.logger.info(f"收到用户指令 [{ws_id}]: {command}")
            
            # 发布事件
            publish_event(
                event_type="user.command",
                payload={"ws_id": ws_id, "command": command},
                source="websocket"
            )
            
            return {
                "type": "ack",
                "event": "command_received",
                "data": {"command": command},
            }
        
        elif msg_type == "action_confirm":
            # 操作确认
            action_id = data.get("action_id")
            confirmed = data.get("confirmed", False)
            self.logger.info(f"操作确认 [{ws_id}]: {action_id} = {confirmed}")
            
            publish_event(
                event_type="user.action_confirm",
                payload={"ws_id": ws_id, "action_id": action_id, "confirmed": confirmed},
                source="websocket"
            )
        
        return None


# 便捷函数
async def start_websocket_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    on_message: Optional[Callable] = None
) -> WebSocketManager:
    """启动 WebSocket 服务器（便捷函数）"""
    manager = WebSocketManager(host, port, on_message=on_message)
    asyncio.create_task(manager.start_server())
    return manager
