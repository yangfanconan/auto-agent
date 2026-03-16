"""
Auto-Agent 全自动工程化编程智能体

支持 qwencode/opencode 等工具，实现从任务解析→环境搭建→代码开发→测试→交付→Git 提交的全流程自动化
"""

__version__ = "1.0.0"
__author__ = "Auto-Agent Team"

# 延迟导入，避免在包初始化时出现问题


def __getattr__(name):
    """延迟导入属性"""
    if name in ('AutoAgent', 'TaskParser', 'TaskTracker', 'TaskScheduler'):
        from .core import AutoAgent, TaskParser, TaskTracker, TaskScheduler
        return locals()[name]
    elif name in ('EnvironmentManager', 'CodeGenerator', 'TestRunner', 'GitManager', 'DeliveryManager'):
        from .modules import EnvironmentManager, CodeGenerator, TestRunner, GitManager, DeliveryManager
        return locals()[name]
    elif name in ('OpencodeAdapter', 'QwencodeAdapter', 'get_tool', 'list_tools'):
        from .adapters import OpencodeAdapter, QwencodeAdapter, get_tool, list_tools
        return locals()[name]
    elif name in ('load_config', 'save_config', 'get_logger'):
        from .utils import load_config, save_config, get_logger
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core
    'AutoAgent',
    'TaskParser',
    'TaskTracker',
    'TaskScheduler',
    # Modules
    'EnvironmentManager',
    'CodeGenerator',
    'TestRunner',
    'GitManager',
    'DeliveryManager',
    # Adapters
    'OpencodeAdapter',
    'QwencodeAdapter',
    'get_tool',
    'list_tools',
    # Utils
    'load_config',
    'save_config',
    'get_logger',
]
