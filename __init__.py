"""
Auto-Agent 全自动工程化编程智能体

支持 qwencode/opencode 等工具，实现从任务解析→环境搭建→代码开发→测试→交付→Git 提交的全流程自动化
"""

__version__ = "1.0.0"
__author__ = "Auto-Agent Team"

from .core import AutoAgent, TaskParser, TaskTracker, TaskScheduler
from .modules import (
    EnvironmentManager,
    CodeGenerator,
    TestRunner,
    GitManager,
    DeliveryManager,
)
from .adapters import (
    OpencodeAdapter,
    QwencodeAdapter,
    get_tool,
    list_tools,
)
from .utils import (
    load_config,
    save_config,
    get_logger,
)

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
