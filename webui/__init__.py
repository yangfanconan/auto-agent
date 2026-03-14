"""
Web UI 模块
提供基于 FastAPI 的 Web 界面
"""

from .app import create_app, app

__all__ = ["create_app", "app"]
