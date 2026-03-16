"""
异常定义模块
定义智能体运行时的各类异常
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class ExceptionLevel(Enum):
    """异常级别枚举"""
    LOW = "low"           # 低危：格式警告、日志缺失
    MEDIUM = "medium"     # 中危：代码报错、测试失败
    HIGH = "high"         # 高危：环境崩溃、工具无法调用、Git 仓库损坏


@dataclass
class ErrorSuggestion:
    """错误建议"""
    message: str
    command: Optional[str] = None
    doc_link: Optional[str] = None


@dataclass
class FriendlyErrorInfo:
    """友好错误信息"""
    title: str
    message: str
    suggestion: str
    level: str = "error"
    icon: str = "❌"
    details: Dict[str, Any] = field(default_factory=dict)


# 错误模板配置
ERROR_TEMPLATES = {
    "ToolNotFoundException": FriendlyErrorInfo(
        title="😕 工具未找到",
        message="找不到所需的工具 '{tool_name}'",
        suggestion="请检查工具是否已安装，或查看配置文件中路径设置",
        icon="🔧",
    ),
    "ToolCallException": FriendlyErrorInfo(
        title="😕 工具调用失败",
        message="调用工具 '{tool_name}' 时出错：{reason}",
        suggestion="检查工具配置或尝试重新安装",
        icon="⚠️",
    ),
    "EnvironmentException": FriendlyErrorInfo(
        title="😕 环境异常",
        message="环境检查或修复失败：{message}",
        suggestion="尝试运行 'python main.py --check' 检查环境",
        icon="🌍",
    ),
    "TaskParseException": FriendlyErrorInfo(
        title="😕 任务解析失败",
        message="无法理解任务需求：{message}",
        suggestion="请尝试用更清晰的描述，或拆分任务",
        icon="📝",
    ),
    "CodeGenerationException": FriendlyErrorInfo(
        title="😕 代码生成失败",
        message="代码生成过程中出错：{message}",
        suggestion="检查 Opencode 是否可用，或尝试简化需求",
        icon="💻",
    ),
    "TestException": FriendlyErrorInfo(
        title="😕 测试执行失败",
        message="测试过程中出错：{message}",
        suggestion="检查测试配置或手动运行 pytest",
        icon="✅",
    ),
    "GitException": FriendlyErrorInfo(
        title="😕 Git 操作失败",
        message="Git 操作出错：{message}",
        suggestion="请确认已配置 Git 用户信息：git config --global user.name 'Your Name'",
        icon="🔄",
    ),
    "DeliveryException": FriendlyErrorInfo(
        title="😕 交付打包失败",
        message="交付打包过程中出错：{message}",
        suggestion="检查文件权限和磁盘空间",
        icon="📦",
    ),
    "AutoAgentException": FriendlyErrorInfo(
        title="😕 发生错误",
        message="{message}",
        suggestion="查看日志文件获取详细信息",
        icon="❌",
    ),
}


class AutoAgentException(Exception):
    """智能体基础异常类"""

    def __init__(
        self,
        message: str,
        level: ExceptionLevel = ExceptionLevel.MEDIUM,
        details: dict = None,
        suggestion: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.level = level
        self.details = details or {}
        self.suggestion = suggestion
        self._error_info: Optional[FriendlyErrorInfo] = None

    def get_friendly_info(self) -> FriendlyErrorInfo:
        """获取友好错误信息"""
        if self._error_info:
            return self._error_info

        template = ERROR_TEMPLATES.get(
            type(self).__name__,
            ERROR_TEMPLATES["AutoAgentException"]
        )

        # 格式化消息
        format_kwargs = {"message": self.message, **self.details}

        return FriendlyErrorInfo(
            title=template.title,
            message=template.message.format(**format_kwargs),
            suggestion=self.suggestion or template.suggestion,
            level="error" if self.level == ExceptionLevel.HIGH else "warning",
            icon=template.icon,
            details=self.details,
        )

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "level": self.level.value,
            "details": self.details,
            "suggestion": self.suggestion,
        }


class EnvironmentException(AutoAgentException):
    """环境异常"""

    def __init__(self, message: str, details: dict = None,
                 suggestion: Optional[str] = None):
        super().__init__(message, ExceptionLevel.HIGH, details, suggestion)


class ToolNotFoundException(AutoAgentException):
    """工具未找到异常"""

    def __init__(self, tool_name: str, details: dict = None):
        message = f"工具 '{tool_name}' 未找到或不可用"
        super().__init__(
            message,
            ExceptionLevel.HIGH,
            {"tool_name": tool_name, **details},
            suggestion=f"请安装或配置 {tool_name} 工具"
        )


class ToolCallException(AutoAgentException):
    """工具调用失败异常"""

    def __init__(self, tool_name: str, reason: str, details: dict = None):
        message = f"调用工具 '{tool_name}' 失败：{reason}"
        super().__init__(
            message,
            ExceptionLevel.MEDIUM,
            {"tool_name": tool_name, "reason": reason, **details},
        )


class TaskParseException(AutoAgentException):
    """任务解析异常"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ExceptionLevel.MEDIUM, details)


class CodeGenerationException(AutoAgentException):
    """代码生成异常"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ExceptionLevel.MEDIUM, details)


class TestException(AutoAgentException):
    """测试执行异常"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ExceptionLevel.MEDIUM, details)


class GitException(AutoAgentException):
    """Git 操作异常"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ExceptionLevel.HIGH, details)


class DeliveryException(AutoAgentException):
    """交付打包异常"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ExceptionLevel.MEDIUM, details)


def show_friendly_error(error: Exception, console=None):
    """
    显示友好错误信息

    Args:
        error: 异常对象
        console: Rich Console 实例（可选）
    """
    if console is None:
        from rich.console import Console
        console = Console()

    if isinstance(error, AutoAgentException):
        info = error.get_friendly_info()
    else:
        info = FriendlyErrorInfo(
            title="😕 未知错误",
            message=str(error),
            suggestion="查看日志文件或联系开发者",
        )

    # 显示错误
    from rich.panel import Panel

    content = f"[bold]{info.message}[/bold]\n\n"
    content += f"[yellow]💡 {info.suggestion}[/yellow]"

    border_color = {"error": "red", "warning": "yellow"}.get(info.level, "red")

    console.print(Panel(
        content,
        title=f"[bold {border_color}]{
            info.icon} {
            info.title}[/bold {border_color}]",
        border_style=border_color,
        padding=(1, 2),
    ))
