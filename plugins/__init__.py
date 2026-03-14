"""
插件系统
"""

from .base import (
    Plugin,
    PluginManager,
    PluginContext,
    PluginMetadata,
    get_plugin_manager,
    GitHubPlugin,
    DockerPlugin,
)

__all__ = [
    "Plugin",
    "PluginManager",
    "PluginContext",
    "PluginMetadata",
    "get_plugin_manager",
    "GitHubPlugin",
    "DockerPlugin",
]
