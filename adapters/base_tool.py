"""
工具抽象层模块
统一 qwen/opencode 等工具的调用接口和状态管理

支持：
- 工具状态感知（RUNNING/WAITING/ERROR/IDLE）
- 异步调用
- 错误处理和重试
- 工具注册和发现
"""

import asyncio
import subprocess
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid

try:
    from ..utils import get_logger, ToolConfig
    from ..core.console_io import get_console_redirector
    from ..core.events import publish_event
except ImportError:
    from utils import get_logger, ToolConfig
    from core.console_io import get_console_redirector
    from core.events import publish_event


class ToolStatus(str, Enum):
    """工具状态枚举"""
    IDLE = "IDLE"              # 空闲
    RUNNING = "RUNNING"        # 工作中
    WAITING = "WAITING"        # 等待用户操作
    ERROR = "ERROR"            # 异常
    STOPPED = "STOPPED"        # 已停止


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "duration": self.duration,
            "meta": self.meta,
        }


class BaseTool(ABC):
    """工具抽象基类"""
    
    def __init__(self, name: str, config: Optional[ToolConfig] = None):
        self.name = name
        self.config = config or ToolConfig()
        self.logger = get_logger()
        self.console_io = get_console_redirector()
        
        # 状态
        self._status = ToolStatus.IDLE
        self._last_error: Optional[str] = None
        self._current_task_id: Optional[str] = None
        self._retry_count = 0
        
        # 回调
        self._on_status_change: Optional[Callable[[ToolStatus], None]] = None
        
        self.logger.info(f"工具已初始化：{name}")
    
    @property
    def status(self) -> ToolStatus:
        """获取工具状态"""
        return self._status
    
    @status.setter
    def status(self, value: ToolStatus):
        """设置工具状态"""
        old_status = self._status
        self._status = value
        
        # 状态变化回调
        if self._on_status_change:
            self._on_status_change(value)
        
        # 发布事件
        if old_status != value:
            publish_event(
                event_type="tool.status_changed",
                payload={
                    "tool_name": self.name,
                    "old_status": old_status.value,
                    "new_status": value.value,
                },
                source="tool"
            )
            
            # 发送控制台消息
            self.console_io.send_status(
                f"工具 {self.name} 状态变更：{old_status.value} → {value.value}",
                {"tool_name": self.name, "old": old_status.value, "new": value.value}
            )
    
    @abstractmethod
    async def run(self, input_text: str, **kwargs) -> ToolResult:
        """
        运行工具（异步）
        
        Args:
            input_text: 输入文本/指令
            **kwargs: 额外参数
        
        Returns:
            ToolResult: 执行结果
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取详细状态"""
        return {
            "name": self.name,
            "status": self._status.value,
            "last_error": self._last_error,
            "current_task": self._current_task_id,
        }
    
    @abstractmethod
    async def handle_error(self, error: str) -> bool:
        """
        处理错误
        
        Args:
            error: 错误信息
        
        Returns:
            bool: 是否已处理（True 表示可重试）
        """
        pass
    
    def set_status_change_callback(self, callback: Callable[[ToolStatus], None]):
        """设置状态变化回调"""
        self._on_status_change = callback
    
    async def run_with_retry(self, input_text: str, max_retries: int = 3, **kwargs) -> ToolResult:
        """带重试的执行"""
        self._retry_count = 0
        
        while self._retry_count <= max_retries:
            self.logger.info(f"执行工具 {self.name} (尝试 {self._retry_count + 1}/{max_retries + 1})")
            
            result = await self.run(input_text, **kwargs)
            
            if result.success:
                return result
            
            # 处理错误
            handled = await self.handle_error(result.error)
            
            if not handled:
                self.logger.error(f"工具 {self.name} 执行失败，无法恢复：{result.error}")
                return result
            
            self._retry_count += 1
            self.logger.warning(f"工具 {self.name} 重试中...")
            
            # 等待一段时间后重试
            if self._retry_count <= max_retries:
                await asyncio.sleep(1.0 * self._retry_count)
        
        # 所有重试失败
        return ToolResult(
            success=False,
            error=f"工具 {self.name} 执行失败，已重试 {max_retries} 次",
        )
    
    def stop(self):
        """停止工具"""
        self.status = ToolStatus.STOPPED
        self.logger.info(f"工具已停止：{self.name}")


class QwenTool(BaseTool):
    """Qwen 工具适配器"""
    
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__("qwen", config)
        self._process: Optional[asyncio.subprocess.Process] = None
    
    async def run(self, input_text: str, **kwargs) -> ToolResult:
        """运行 Qwen"""
        import time
        start_time = time.time()
        
        try:
            self.status = ToolStatus.RUNNING
            self._current_task_id = str(uuid.uuid4())[:8]
            
            # 发送开始消息
            self.console_io.send_tool_output(
                f"🤖 Qwen 开始执行任务：{input_text[:100]}...",
                self._current_task_id
            )
            
            # 构建命令
            # qwen 直接使用位置参数
            cmd = ["qwen", input_text]
            
            # 添加选项
            if kwargs.get("model"):
                cmd.extend(["-m", kwargs["model"]])
            if kwargs.get("sandbox"):
                cmd.append("--sandbox")
            
            self.logger.debug(f"执行 Qwen: {' '.join(cmd)}")
            
            # 异步执行
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
            )
            
            # 读取输出
            stdout, stderr = await self._process.communicate(timeout=kwargs.get("timeout", 300))
            
            duration = time.time() - start_time
            
            result = ToolResult(
                success=self._process.returncode == 0,
                output=stdout.decode('utf-8') if stdout else "",
                error=stderr.decode('utf-8') if stderr else "",
                exit_code=self._process.returncode,
                duration=duration,
                meta={"task_id": self._current_task_id},
            )
            
            # 发送结果消息
            if result.success:
                self.console_io.send_tool_output(
                    f"✅ Qwen 任务完成：{result.output[:200]}",
                    self._current_task_id
                )
            else:
                self.console_io.send_tool_output(
                    f"❌ Qwen 任务失败：{result.error[:200]}",
                    self._current_task_id
                )
            
            return result
            
        except asyncio.TimeoutError:
            if self._process:
                self._process.kill()
            return ToolResult(
                success=False,
                error=f"Qwen 执行超时（{kwargs.get('timeout', 300)}秒）",
            )
        except Exception as e:
            self.logger.error(f"Qwen 执行异常：{e}")
            return ToolResult(
                success=False,
                error=str(e),
            )
        finally:
            self.status = ToolStatus.IDLE
            self._current_task_id = None
    
    def get_status(self) -> Dict[str, Any]:
        """获取详细状态"""
        base_status = super().get_status()
        base_status["tool_type"] = "qwen"
        base_status["path"] = str(self._process.pid) if self._process else None
        return base_status
    
    async def handle_error(self, error: str) -> bool:
        """处理错误"""
        self._last_error = error
        self.status = ToolStatus.ERROR
        
        # 检查是否可恢复
        if "timeout" in error.lower():
            self.logger.warning("Qwen 超时，可重试")
            return True
        
        if "connection" in error.lower():
            self.logger.warning("Qwen 连接错误，可重试")
            return True
        
        # 其他错误不可恢复
        return False
    
    def stop(self):
        """停止 Qwen"""
        if self._process:
            self._process.kill()
        super().stop()


class OpenCodeTool(BaseTool):
    """OpenCode 工具适配器"""
    
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__("opencode", config)
        self._process: Optional[asyncio.subprocess.Process] = None
        self._opencode_path: Optional[Path] = None
        self._detect_path()
    
    def _detect_path(self):
        """检测 OpenCode 路径"""
        common_paths = [
            Path.home() / ".opencode" / "bin" / "opencode",
            Path("/usr/local/bin/opencode"),
            Path("/opt/homebrew/bin/opencode"),
        ]
        
        for path in common_paths:
            if path.exists():
                self._opencode_path = path
                self.logger.info(f"检测到 OpenCode: {self._opencode_path}")
                return
        
        # 尝试从 PATH 查找
        try:
            result = subprocess.run(
                ["which", "opencode"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                self._opencode_path = Path(result.stdout.strip())
                self.logger.info(f"从 PATH 找到 OpenCode: {self._opencode_path}")
        except:
            pass
    
    async def run(self, input_text: str, **kwargs) -> ToolResult:
        """运行 OpenCode"""
        import time
        start_time = time.time()
        
        if not self._opencode_path:
            return ToolResult(
                success=False,
                error="OpenCode 未找到，请检查安装",
            )
        
        try:
            self.status = ToolStatus.RUNNING
            self._current_task_id = str(uuid.uuid4())[:8]
            
            # 发送开始消息
            self.console_io.send_tool_output(
                f"⚡ OpenCode 开始执行任务：{input_text[:100]}...",
                self._current_task_id
            )
            
            # 构建命令 - opencode 使用 "run" 子命令
            cmd = [str(self._opencode_path), "run", input_text]
            
            self.logger.debug(f"执行 OpenCode: {' '.join(cmd)}")
            
            # 异步执行
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=kwargs.get("cwd"),
            )
            
            # 读取输出
            stdout, stderr = await self._process.communicate(timeout=kwargs.get("timeout", 300))
            
            duration = time.time() - start_time
            
            result = ToolResult(
                success=self._process.returncode == 0,
                output=stdout.decode('utf-8') if stdout else "",
                error=stderr.decode('utf-8') if stderr else "",
                exit_code=self._process.returncode,
                duration=duration,
                meta={"task_id": self._current_task_id},
            )
            
            # 发送结果消息
            if result.success:
                self.console_io.send_tool_output(
                    f"✅ OpenCode 任务完成",
                    self._current_task_id
                )
            else:
                self.console_io.send_tool_output(
                    f"❌ OpenCode 任务失败：{result.error[:200]}",
                    self._current_task_id
                )
            
            return result
            
        except asyncio.TimeoutError:
            if self._process:
                self._process.kill()
            return ToolResult(
                success=False,
                error=f"OpenCode 执行超时",
            )
        except Exception as e:
            self.logger.error(f"OpenCode 执行异常：{e}")
            return ToolResult(
                success=False,
                error=str(e),
            )
        finally:
            self.status = ToolStatus.IDLE
            self._current_task_id = None
    
    def get_status(self) -> Dict[str, Any]:
        """获取详细状态"""
        base_status = super().get_status()
        base_status["tool_type"] = "opencode"
        base_status["path"] = str(self._opencode_path) if self._opencode_path else None
        return base_status
    
    async def handle_error(self, error: str) -> bool:
        """处理错误"""
        self._last_error = error
        self.status = ToolStatus.ERROR
        
        # OpenCode 错误通常可重试
        return "not found" not in error.lower()
    
    def stop(self):
        """停止 OpenCode"""
        if self._process:
            self._process.kill()
        super().stop()


# 工具注册表
class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.logger = get_logger()
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool
        self.logger.info(f"工具已注册：{tool.name}")
    
    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        return [tool.get_status() for tool in self._tools.values()]
    
    async def run_tool(self, name: str, input_text: str, **kwargs) -> ToolResult:
        """运行指定工具"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"工具不存在：{name}",
            )
        return await tool.run_with_retry(input_text, **kwargs)


# 全局注册表
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        
        # 注册默认工具
        _global_registry.register(QwenTool())
        _global_registry.register(OpenCodeTool())
    
    return _global_registry
