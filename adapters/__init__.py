"""
工具适配器包
"""

from .opencode_adapter import OpencodeAdapter, OpencodeResult
from .qwen_adapter import QwenAdapter, QwenResult
from .tool_registry import (
    ToolRegistry,
    ToolInfo,
    get_registry,
    get_tool,
    list_tools,
)

__all__ = [
    # Opencode
    'OpencodeAdapter',
    'OpencodeResult',
    # Qwen
    'QwenAdapter',
    'QwenResult',
    # Registry
    'ToolRegistry',
    'ToolInfo',
    'get_registry',
    'get_tool',
    'list_tools',
]
