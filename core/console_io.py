"""
控制台 IO 接管模块
捕获和重定向 stdin/stdout/stderr，支持结构化解析和 WebSocket 推送

增强版：支持多进程/线程安全，保留原始输出能力
"""

import sys
import os
import threading
import queue
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
import io
import json

try:
    from ..utils import get_logger
    from ..core.events import publish_event, EventType
except ImportError:
    from utils import get_logger
    from core.events import publish_event, EventType


class IOType(str, Enum):
    """IO 类型枚举"""
    INPUT = "input"           # 用户输入
    OUTPUT = "output"         # 标准输出
    ERROR = "error"           # 错误输出
    LOG = "log"              # 日志
    STATUS = "status"        # 状态信息
    TOOL_OUTPUT = "tool_output"  # 工具输出


class IOSource(str, Enum):
    """IO 来源枚举"""
    CONSOLE = "console"
    OPENCODE = "opencode"
    QWEN = "qwen"
    WEBSOCKET = "websocket"
    SYSTEM = "system"


@dataclass
class IOMessage:
    """结构化 IO 消息"""
    type: IOType
    source: IOSource
    content: str
    timestamp: float
    meta: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "source": self.source.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "meta": self.meta,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class StreamCapturer:
    """流捕获器 - 捕获 stdout/stderr"""
    
    def __init__(
        self,
        stream_type: IOType,
        callback: Callable[[IOMessage], None],
        source: IOSource = IOSource.CONSOLE,
        keep_original: bool = True
    ):
        self.stream_type = stream_type
        self.callback = callback
        self.source = source
        self.keep_original = keep_original
        
        # 保存原始流
        self.original_stream = sys.stdout if stream_type == IOType.OUTPUT else sys.stderr
        self._buffer = io.StringIO()
        self._lock = threading.Lock()
        
        # 行缓冲
        self._line_buffer = ""
    
    def write(self, text: str):
        """写入捕获内容"""
        with self._lock:
            # 写入原始流（如果保留）
            if self.keep_original and self.original_stream:
                try:
                    self.original_stream.write(text)
                    self.original_stream.flush()
                except:
                    pass
            
            # 缓冲内容
            self._buffer.write(text)
            self._line_buffer += text
            
            # 按行处理
            while '\n' in self._line_buffer:
                line, self._line_buffer = self._line_buffer.split('\n', 1)
                if line.strip():  # 忽略空行
                    self._send_message(line)
    
    def flush(self):
        """刷新缓冲"""
        with self._lock:
            if self._line_buffer.strip():
                self._send_message(self._line_buffer)
                self._line_buffer = ""
            if self.keep_original and self.original_stream:
                self.original_stream.flush()
    
    def _send_message(self, content: str):
        """发送捕获的消息"""
        message = IOMessage(
            type=self.stream_type,
            source=self.source,
            content=content,
            timestamp=datetime.now().timestamp(),
            meta={}
        )
        try:
            self.callback(message)
        except Exception as e:
            # 回调失败不影响主流程
            pass
    
    def start(self):
        """开始捕获"""
        if self.stream_type == IOType.OUTPUT:
            sys.stdout = self
        else:
            sys.stderr = self
    
    def stop(self):
        """停止捕获"""
        self.flush()
        if self.stream_type == IOType.OUTPUT:
            sys.stdout = self.original_stream
        else:
            sys.stderr = self.original_stream


class InputCapturer:
    """输入捕获器 - 捕获 stdin"""
    
    def __init__(
        self,
        callback: Callable[[IOMessage], None],
        source: IOSource = IOSource.CONSOLE
    ):
        self.callback = callback
        self.source = source
        self.original_input = sys.stdin
        self._active = False
    
    def readline(self) -> str:
        """读取一行输入"""
        try:
            # 从原始输入读取
            line = self.original_input.readline()
            
            # 捕获并发送
            if line.strip() and self._active:
                message = IOMessage(
                    type=IOType.INPUT,
                    source=self.source,
                    content=line.strip(),
                    timestamp=datetime.now().timestamp(),
                    meta={}
                )
                try:
                    self.callback(message)
                except:
                    pass
            
            return line
        except EOFError:
            return ""
    
    def start(self):
        """开始捕获"""
        self._active = True
        sys.stdin = self
    
    def stop(self):
        """停止捕获"""
        self._active = False
        sys.stdin = self.original_input


class ConsoleIORedirector:
    """控制台 IO 重定向器"""
    
    def __init__(
        self,
        on_io_message: Optional[Callable[[IOMessage], None]] = None,
        keep_original: bool = True,
        enable_input_capture: bool = True,
        enable_output_capture: bool = True,
        enable_error_capture: bool = True
    ):
        self.logger = get_logger()
        self.on_io_message = on_io_message
        self.keep_original = keep_original
        
        # 捕获器
        self.output_capturer = None
        self.error_capturer = None
        self.input_capturer = None
        
        # 配置
        self.enable_input_capture = enable_input_capture
        self.enable_output_capture = enable_output_capture
        self.enable_error_capture = enable_error_capture
        
        # 状态
        self._active = False
        self._message_queue = queue.Queue()
        
        # 消息处理线程
        self._processor_thread = None
        self._stop_processor = False
        
        self.logger.info("ConsoleIORedirector 已初始化")
    
    def _handle_message(self, message: IOMessage):
        """处理 IO 消息"""
        # 调用回调
        if self.on_io_message:
            try:
                self.on_io_message(message)
            except Exception as e:
                self.logger.error(f"IO 消息回调失败：{e}")
        
        # 发布事件
        try:
            publish_event(
                event_type="system.io",
                payload=message.to_dict(),
                source="console_io"
            )
        except:
            pass
        
        # 加入队列（供 WebSocket 读取）
        try:
            self._message_queue.put(message.to_dict())
        except:
            pass
    
    def _process_messages(self):
        """消息处理循环"""
        while not self._stop_processor:
            try:
                message = self._message_queue.get(timeout=0.1)
                # 可以在这里添加额外的处理逻辑
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"消息处理失败：{e}")
    
    def start(self):
        """开始 IO 重定向"""
        if self._active:
            return
        
        self.logger.info("开始控制台 IO 重定向")
        
        # 启动消息处理线程
        self._stop_processor = False
        self._processor_thread = threading.Thread(target=self._process_messages, daemon=True)
        self._processor_thread.start()
        
        # 创建捕获器
        if self.enable_output_capture:
            self.output_capturer = StreamCapturer(
                stream_type=IOType.OUTPUT,
                callback=self._handle_message,
                source=IOSource.CONSOLE,
                keep_original=self.keep_original
            )
            self.output_capturer.start()
        
        if self.enable_error_capture:
            self.error_capturer = StreamCapturer(
                stream_type=IOType.ERROR,
                callback=self._handle_message,
                source=IOSource.CONSOLE,
                keep_original=self.keep_original
            )
            self.error_capturer.start()
        
        if self.enable_input_capture:
            self.input_capturer = InputCapturer(
                callback=self._handle_message,
                source=IOSource.CONSOLE
            )
            self.input_capturer.start()
        
        self._active = True
        self.logger.info("控制台 IO 重定向已启动")
    
    def stop(self):
        """停止 IO 重定向"""
        if not self._active:
            return
        
        self.logger.info("停止控制台 IO 重定向")
        
        # 停止捕获器
        if self.output_capturer:
            self.output_capturer.stop()
        if self.error_capturer:
            self.error_capturer.stop()
        if self.input_capturer:
            self.input_capturer.stop()
        
        # 停止消息处理
        self._stop_processor = True
        if self._processor_thread:
            self._processor_thread.join(timeout=2)
        
        self._active = False
        self.logger.info("控制台 IO 重定向已停止")
    
    def get_messages(self, limit: int = 100) -> List[Dict]:
        """获取最近的消息"""
        messages = []
        while len(messages) < limit and not self._message_queue.empty():
            try:
                messages.append(self._message_queue.get_nowait())
            except queue.Empty:
                break
        return messages
    
    def send_message(self, message: IOMessage):
        """发送消息（用于工具输出）"""
        self._handle_message(message)
    
    def send_tool_output(self, content: str, tool_id: str = ""):
        """发送工具输出"""
        message = IOMessage(
            type=IOType.TOOL_OUTPUT,
            source=IOSource.OPENCODE if "opencode" in tool_id.lower() else IOSource.QWEN,
            content=content,
            timestamp=datetime.now().timestamp(),
            meta={"tool_id": tool_id}
        )
        self.send_message(message)
    
    def send_status(self, status: str, meta: Dict[str, Any] = None):
        """发送状态信息"""
        message = IOMessage(
            type=IOType.STATUS,
            source=IOSource.SYSTEM,
            content=status,
            timestamp=datetime.now().timestamp(),
            meta=meta or {}
        )
        self.send_message(message)


# 全局实例
_global_redirector: Optional[ConsoleIORedirector] = None


def get_console_redirector() -> ConsoleIORedirector:
    """获取全局 IO 重定向器"""
    global _global_redirector
    if _global_redirector is None:
        _global_redirector = ConsoleIORedirector()
    return _global_redirector


def start_console_capture(on_message: Optional[Callable[[IOMessage], None]] = None):
    """启动控制台捕获（便捷函数）"""
    redirector = get_console_redirector()
    if on_message:
        redirector.on_io_message = on_message
    redirector.start()


def stop_console_capture():
    """停止控制台捕获"""
    redirector = get_console_redirector()
    redirector.stop()
