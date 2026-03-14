"""
工具适配器包
"""

from .opencode_adapter import OpencodeAdapter, OpencodeResult
from .qwencode_adapter import QwencodeAdapter, QwencodeResult
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
    # Qwencode
    'QwencodeAdapter',
    'QwencodeResult',
    # Registry
    'ToolRegistry',
    'ToolInfo',
    'get_registry',
    'get_tool',
    'list_tools',
]
