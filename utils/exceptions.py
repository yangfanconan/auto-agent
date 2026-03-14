"""
异常定义模块
定义智能体运行时的各类异常
"""

from enum import Enum


class ExceptionLevel(Enum):
    """异常级别枚举"""
    LOW = "low"           # 低危：格式警告、日志缺失
    MEDIUM = "medium"     # 中危：代码报错、测试失败
    HIGH = "high"         # 高危：环境崩溃、工具无法调用、Git 仓库损坏


class AutoAgentException(Exception):
    """智能体基础异常类"""
    
    def __init__(self, message: str, level: ExceptionLevel = ExceptionLevel.MEDIUM, details: dict = None):
        super().__init__(message)
        self.message = message
        self.level = level
        self.details = details or {}
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "level": self.level.value,
            "details": self.details
        }


class EnvironmentException(AutoAgentException):
    """环境异常"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, ExceptionLevel.HIGH, details)


class ToolNotFoundException(AutoAgentException):
    """工具未找到异常"""
    
    def __init__(self, tool_name: str, details: dict = None):
        message = f"工具 '{tool_name}' 未找到或不可用"
        super().__init__(message, ExceptionLevel.HIGH, details)


class ToolCallException(AutoAgentException):
    """工具调用失败异常"""
    
    def __init__(self, tool_name: str, reason: str, details: dict = None):
        message = f"调用工具 '{tool_name}' 失败：{reason}"
        super().__init__(message, ExceptionLevel.MEDIUM, details)


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
