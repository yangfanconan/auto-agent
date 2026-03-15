"""
事件总线模块
实现模块间解耦通信
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any, Optional
from enum import Enum
import json

try:
    from ..utils import get_logger
except ImportError:
    from utils import get_logger


class EventType(str, Enum):
    """预定义事件类型"""
    # 任务事件
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_SUBTASK_COMPLETED = "task.subtask.completed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    
    # 工具事件
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    
    # 环境事件
    ENV_SCANNED = "env.scanned"
    ENV_FIXED = "env.fixed"
    
    # 代码事件
    CODE_GENERATED = "code.generated"
    CODE_REVIEWED = "code.reviewed"
    
    # 测试事件
    TEST_STARTED = "test.started"
    TEST_COMPLETED = "test.completed"
    TEST_FAILED = "test.failed"
    
    # Git 事件
    GIT_COMMITTED = "git.committed"
    GIT_PUSHED = "git.pushed"
    
    # 系统事件
    ERROR_OCCURRED = "system.error"
    WARNING_OCCURRED = "system.warning"
    INFO_MESSAGE = "system.info"


@dataclass
class Event:
    """事件对象"""
    type: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        return cls(
            type=data["type"],
            payload=data["payload"],
            timestamp=data.get("timestamp", time.time()),
            source=data.get("source", "unknown")
        )


class EventBus:
    """事件总线"""
    
    _instance: Optional['EventBus'] = None
    
    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logger = get_logger()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._async_subscribers: Dict[str, List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._event_history: List[Event] = []
        self._max_history = 1000
        
        self._initialized = True
        self.logger.info("事件总线已初始化")
    
    def subscribe(self, event_type: str, handler: Callable):
        """
        订阅事件（同步处理器）
        
        Args:
            event_type: 事件类型
            handler: 处理函数，签名：handler(event: Event)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        self.logger.debug(f"订阅事件：{event_type}")
    
    def subscribe_async(self, event_type: str, handler: Callable):
        """
        订阅事件（异步处理器）
        
        Args:
            event_type: 事件类型
            handler: 异步处理函数，签名：async handler(event: Event)
        """
        if event_type not in self._async_subscribers:
            self._async_subscribers[event_type] = []
        self._async_subscribers[event_type].append(handler)
        self.logger.debug(f"订阅异步事件：{event_type}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
        if event_type in self._async_subscribers:
            self._async_subscribers[event_type].remove(handler)
    
    def publish(self, event: Event):
        """
        发布事件（同步）
        
        Args:
            event: 事件对象
        """
        # 记录到历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # 调用同步处理器
        if event.type in self._subscribers:
            for handler in self._subscribers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    self.logger.error(f"事件处理器异常：{e}")
        
        # 调用异步处理器（如果有运行中的事件循环）
        if event.type in self._async_subscribers:
            try:
                loop = asyncio.get_running_loop()
                for handler in self._async_subscribers[event.type]:
                    asyncio.create_task(self._call_async_handler(handler, event))
            except RuntimeError:
                # 没有运行中的事件循环，跳过异步处理器
                pass
        
        # 放入队列（如果有运行中的事件循环）
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._queue.put(event))
        except RuntimeError:
            # 没有运行中的事件循环，跳过
            pass
        
        self.logger.debug(f"发布事件：{event.type}")
    
    async def publish_async(self, event: Event):
        """发布事件（异步）"""
        await self._queue.put(event)
        self.publish(event)  # 同时触发同步处理器
    
    async def _call_async_handler(self, handler: Callable, event: Event):
        """调用异步处理器"""
        try:
            await handler(event)
        except Exception as e:
            self.logger.error(f"异步事件处理器异常：{e}")
    
    async def start_worker(self):
        """启动事件处理工作器"""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        self.logger.info("事件总线工作器已启动")
    
    async def stop_worker(self):
        """停止事件处理工作器"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self.logger.info("事件总线工作器已停止")
    
    async def _worker_loop(self):
        """事件处理循环"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                # 这里可以添加额外的处理逻辑，如持久化、转发等
                self.logger.debug(f"事件处理：{event.type}")
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"事件处理异常：{e}")
    
    def get_history(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """获取事件历史"""
        if event_type:
            events = [e for e in self._event_history if e.type == event_type]
        else:
            events = self._event_history
        return events[-limit:]
    
    def clear_history(self):
        """清空事件历史"""
        self._event_history = []
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_events": len(self._event_history),
            "sync_subscribers": sum(len(v) for v in self._subscribers.values()),
            "async_subscribers": sum(len(v) for v in self._async_subscribers.values()),
            "event_types": len(set(e.type for e in self._event_history)),
        }


# 便捷函数
def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return EventBus()


def publish_event(event_type: str, payload: Dict, source: str = "unknown"):
    """便捷发布事件"""
    bus = get_event_bus()
    event = Event(type=event_type, payload=payload, source=source)
    bus.publish(event)


# 装饰器
def on_event(event_type: str):
    """事件订阅装饰器"""
    def decorator(func: Callable):
        def wrapper(event: Event):
            return func(event)
        
        bus = get_event_bus()
        if asyncio.iscoroutinefunction(func):
            bus.subscribe_async(event_type, wrapper)
        else:
            bus.subscribe(event_type, wrapper)
        
        return func
    return decorator
