"""
插件系统模块
支持扩展功能，无需修改核心代码
"""

import importlib
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

try:
    from ..utils import get_logger
    from ..core.events import EventBus, Event, publish_event
except ImportError:
    from utils import get_logger
    from core.events import EventBus, Event, publish_event


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str = "Unknown"
    email: str = ""
    homepage: str = ""
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "email": self.email,
            "homepage": self.homepage,
            "dependencies": self.dependencies,
        }


class PluginContext:
    """插件上下文"""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.commands: Dict[str, Callable] = {}
        self.handlers: Dict[str, Callable] = {}
        self.config: Dict[str, Any] = {}
    
    def register_command(self, name: str, handler: Callable):
        """注册命令"""
        self.commands[name] = handler
    
    def register_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self.handlers[event_type] = handler
        publish_event("plugin.handler_registered", {
            "event_type": event_type,
            "handler": handler.__name__
        })
    
    def get(self, key: str, default=None) -> Any:
        """获取数据"""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置数据"""
        self.data[key] = value


class Plugin(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """获取插件元数据"""
        pass
    
    @abstractmethod
    def activate(self, context: PluginContext):
        """激活插件"""
        pass
    
    @abstractmethod
    def deactivate(self):
        """停用插件"""
        pass
    
    def on_event(self, event: Event):
        """处理事件（可选实现）"""
        pass
    
    def get_commands(self) -> Dict[str, str]:
        """获取插件提供的命令列表"""
        return {}


class PluginManager:
    """插件管理器"""
    
    def __init__(self, plugins_dir: str = "plugins"):
        self.logger = get_logger()
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self._plugins: Dict[str, Plugin] = {}
        self._plugin_contexts: Dict[str, PluginContext] = {}
        self._context = PluginContext()
        
        self.logger.info(f"插件管理器已初始化，目录：{self.plugins_dir}")
    
    def register(self, plugin: Plugin):
        """注册插件"""
        name = plugin.metadata.name
        
        if name in self._plugins:
            self.logger.warning(f"插件已存在：{name}")
            return
        
        self._plugins[name] = plugin
        self._plugin_contexts[name] = PluginContext()
        
        self.logger.info(f"插件已注册：{name} v{plugin.metadata.version}")
        
        # 发布事件
        publish_event("plugin.registered", {
            "name": name,
            "version": plugin.metadata.version,
        })
    
    def unregister(self, name: str):
        """注销插件"""
        if name not in self._plugins:
            return
        
        # 先停用
        self.deactivate(name)
        
        del self._plugins[name]
        del self._plugin_contexts[name]
        
        self.logger.info(f"插件已注销：{name}")
    
    def activate(self, name: str) -> bool:
        """激活插件"""
        if name not in self._plugins:
            self.logger.error(f"插件不存在：{name}")
            return False
        
        plugin = self._plugins[name]
        context = self._plugin_contexts[name]
        
        try:
            plugin.activate(context)
            self.logger.info(f"插件已激活：{name}")
            
            # 注册命令
            for cmd_name, handler in context.commands.items():
                self._context.commands[f"{name}:{cmd_name}"] = handler
            
            # 注册事件处理器
            for event_type, handler in context.handlers.items():
                from core.events import get_event_bus
                bus = get_event_bus()
                bus.subscribe_async(event_type, handler)
            
            publish_event("plugin.activated", {"name": name})
            return True
            
        except Exception as e:
            self.logger.error(f"插件激活失败：{name} - {e}")
            return False
    
    def deactivate(self, name: str) -> bool:
        """停用插件"""
        if name not in self._plugins:
            return False
        
        plugin = self._plugins[name]
        
        try:
            plugin.deactivate()
            self.logger.info(f"插件已停用：{name}")
            
            # 移除命令
            keys_to_remove = [k for k in self._context.commands if k.startswith(f"{name}:")]
            for key in keys_to_remove:
                del self._context.commands[key]
            
            publish_event("plugin.deactivated", {"name": name})
            return True
            
        except Exception as e:
            self.logger.error(f"插件停用失败：{name} - {e}")
            return False
    
    def load_all(self):
        """加载所有插件"""
        self.logger.info("开始加载插件...")
        
        # 扫描插件目录
        for plugin_file in self.plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            
            try:
                self.load_from_file(plugin_file)
            except Exception as e:
                self.logger.error(f"加载插件失败 {plugin_file}: {e}")
        
        self.logger.info(f"插件加载完成，共 {len(self._plugins)} 个插件")
    
    def load_from_file(self, file_path: Path):
        """从文件加载插件"""
        module_name = file_path.stem
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 查找插件类
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr != Plugin:
                plugin = attr()
                self.register(plugin)
    
    def get_plugin(self, name: str) -> Optional[Plugin]:
        """获取插件实例"""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[Dict]:
        """列出所有插件"""
        return [
            {
                **plugin.metadata.to_dict(),
                "activated": name in [p for p in self._plugins if self._plugin_contexts.get(p)],
            }
            for name, plugin in self._plugins.items()
        ]
    
    def get_context(self) -> PluginContext:
        """获取全局上下文"""
        return self._context
    
    def execute_command(self, command: str, **kwargs) -> Any:
        """执行插件命令"""
        if command not in self._context.commands:
            raise KeyError(f"命令不存在：{command}")
        
        handler = self._context.commands[command]
        return handler(**kwargs)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_plugins": len(self._plugins),
            "plugins": list(self._plugins.keys()),
            "commands": len(self._context.commands),
        }


# 全局插件管理器实例
_global_manager: Optional[PluginManager] = None


def get_plugin_manager(plugins_dir: str = "plugins") -> PluginManager:
    """获取全局插件管理器实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = PluginManager(plugins_dir)
    return _global_manager


# 示例插件：GitHub 集成
class GitHubPlugin(Plugin):
    """GitHub 集成插件示例"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="github",
            version="1.0.0",
            description="GitHub 集成插件 - 创建仓库、PR 等",
            author="Auto-Agent",
        )
    
    def activate(self, context: PluginContext):
        context.register_command("create_repo", self.create_repo)
        context.register_command("create_pr", self.create_pr)
        context.register_handler("task.completed", self.on_task_completed)
    
    def deactivate(self):
        pass
    
    async def create_repo(self, name: str, private: bool = True, description: str = ""):
        """创建 GitHub 仓库"""
        # 这里实现 GitHub API 调用
        return {
            "success": True,
            "repo": f"https://github.com/{name}",
            "private": private,
        }
    
    async def create_pr(self, repo: str, title: str, body: str = ""):
        """创建 Pull Request"""
        return {
            "success": True,
            "pr": f"https://github.com/{repo}/pull/1",
        }
    
    async def on_task_completed(self, event: Event):
        """任务完成时通知"""
        # 可以在这里发送通知到 GitHub
        pass
    
    def get_commands(self) -> Dict[str, str]:
        return {
            "create_repo": "创建 GitHub 仓库",
            "create_pr": "创建 Pull Request",
        }


# 示例插件：Docker 集成
class DockerPlugin(Plugin):
    """Docker 集成插件示例"""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="docker",
            version="1.0.0",
            description="Docker 集成插件 - 构建镜像、运行容器",
            author="Auto-Agent",
        )
    
    def activate(self, context: PluginContext):
        context.register_command("build", self.build_image)
        context.register_command("run", self.run_container)
    
    def deactivate(self):
        pass
    
    async def build_image(self, path: str, tag: str):
        """构建 Docker 镜像"""
        return {"success": True, "tag": tag}
    
    async def run_container(self, image: str, name: str):
        """运行 Docker 容器"""
        return {"success": True, "container": name}
    
    def get_commands(self) -> Dict[str, str]:
        return {
            "build": "构建 Docker 镜像",
            "run": "运行 Docker 容器",
        }
