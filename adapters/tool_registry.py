"""
工具注册中心
统一管理所有可用工具的适配器
"""

from typing import Dict, Optional, Any, Type
from dataclasses import dataclass

try:
    from ..utils import get_logger, ToolConfig, ToolNotFoundException
except ImportError:
    from utils import get_logger, ToolConfig, ToolNotFoundException


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    adapter_class: Type
    config: ToolConfig
    instance: Optional[Any] = None


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self.logger = get_logger()
        self._tools: Dict[str, ToolInfo] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """注册内置工具"""
        # 注册 opencode
        try:
            from .opencode_adapter import OpencodeAdapter
            self.register_tool(
                name="opencode",
                description="代码编写、架构设计、逻辑编码工具",
                adapter_class=OpencodeAdapter,
                config=ToolConfig(enabled=True, timeout=300, max_retries=3)
            )
            self.logger.info("已注册工具：opencode")
        except ImportError as e:
            self.logger.warning(f"无法导入 OpencodeAdapter: {e}")
        
        # 注册 qwencode
        try:
            from .qwencode_adapter import QwencodeAdapter
            self.register_tool(
                name="qwencode",
                description="批量代码生成、格式化、编码优化工具",
                adapter_class=QwencodeAdapter,
                config=ToolConfig(enabled=True, timeout=180, max_retries=3)
            )
            self.logger.info("已注册工具：qwencode")
        except ImportError as e:
            self.logger.warning(f"无法导入 QwencodeAdapter: {e}")
    
    def register_tool(
        self,
        name: str,
        description: str,
        adapter_class: Type,
        config: Optional[ToolConfig] = None
    ):
        """
        注册工具
        
        Args:
            name: 工具名称
            description: 工具描述
            adapter_class: 适配器类
            config: 工具配置
        """
        self._tools[name] = ToolInfo(
            name=name,
            description=description,
            adapter_class=adapter_class,
            config=config or ToolConfig()
        )
    
    def get_tool(self, name: str, lazy_init: bool = True) -> Optional[Any]:
        """
        获取工具实例
        
        Args:
            name: 工具名称
            lazy_init: 是否懒加载
        
        Returns:
            工具实例，如果不存在则返回 None
        """
        if name not in self._tools:
            self.logger.warning(f"工具不存在：{name}")
            return None
        
        tool_info = self._tools[name]
        
        if not tool_info.config.enabled:
            self.logger.warning(f"工具已禁用：{name}")
            return None
        
        if lazy_init and tool_info.instance is None:
            try:
                tool_info.instance = tool_info.adapter_class(tool_info.config)
                self.logger.info(f"已初始化工具：{name}")
            except Exception as e:
                self.logger.error(f"初始化工具 {name} 失败：{e}")
                return None
        
        return tool_info.instance
    
    def get_tool_info(self, name: str) -> Optional[ToolInfo]:
        """获取工具信息"""
        return self._tools.get(name)
    
    def list_tools(self) -> Dict[str, Dict]:
        """列出所有已注册工具"""
        result = {}
        for name, info in self._tools.items():
            result[name] = {
                "description": info.description,
                "enabled": info.config.enabled,
                "available": False
            }
            
            # 检查工具可用性
            if info.config.enabled:
                try:
                    adapter = info.adapter_class(info.config)
                    if hasattr(adapter, 'is_available'):
                        result[name]["available"] = adapter.is_available
                        if hasattr(adapter, 'version') and adapter.version:
                            result[name]["version"] = adapter.version
                except Exception:
                    pass
        
        return result
    
    def is_tool_available(self, name: str) -> bool:
        """检查工具是否可用"""
        tool = self.get_tool(name)
        if tool is None:
            return False
        
        if hasattr(tool, 'is_available'):
            return tool.is_available
        return True
    
    def get_available_tools(self) -> list:
        """获取所有可用工具名称"""
        available = []
        for name in self._tools:
            if self.is_tool_available(name):
                available.append(name)
        return available


# 全局工具注册实例
_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局工具注册实例"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def get_tool(name: str) -> Optional[Any]:
    """获取工具实例（快捷方式）"""
    return get_registry().get_tool(name)


def list_tools() -> Dict[str, Dict]:
    """列出所有工具（快捷方式）"""
    return get_registry().list_tools()
