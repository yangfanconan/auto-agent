"""
主题配置模块
定义不同颜色主题和样式
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ColorScheme:
    """颜色方案"""
    # 状态颜色
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "blue"
    
    # 进度颜色
    progress_primary: str = "cyan"
    progress_secondary: str = "blue"
    
    # 文本颜色
    text_primary: str = "white"
    text_secondary: str = "bright_black"
    text_muted: str = "dim"
    
    # 边框颜色
    border_primary: str = "blue"
    border_success: str = "green"
    border_warning: str = "yellow"
    border_error: str = "red"


@dataclass
class StyleConfig:
    """样式配置"""
    # 面板样式
    panel_border: str = "rounded"
    panel_padding: int = 1
    
    # 表格样式
    table_show_header: bool = True
    table_row_styles: Dict = None
    
    # 进度条样式
    progress_bar_width: int = 40
    progress_show_percentage: bool = True
    
    def __post_init__(self):
        if self.table_row_styles is None:
            self.table_row_styles = {
                "completed": "green",
                "in_progress": "cyan",
                "failed": "red",
                "pending": "dim"
            }


class ThemeManager:
    """主题管理器"""
    
    THEMES = {
        "default": {
            "colors": ColorScheme(),
            "style": StyleConfig(),
        },
        "dark": {
            "colors": ColorScheme(
                text_primary="bright_white",
                text_secondary="white",
            ),
            "style": StyleConfig(),
        },
        "light": {
            "colors": ColorScheme(
                text_primary="black",
                text_secondary="dim",
                border_primary="blue",
            ),
            "style": StyleConfig(),
        },
        "monokai": {
            "colors": ColorScheme(
                success="#A6E22E",
                warning="#E6DB74",
                error="#F92672",
                info="#66D9EF",
                progress_primary="#AE81FF",
            ),
            "style": StyleConfig(panel_border="double"),
        },
    }
    
    def __init__(self, theme_name: str = "default"):
        self.current_theme = theme_name
        self.load_theme(theme_name)
    
    def load_theme(self, theme_name: str):
        """加载主题"""
        if theme_name not in self.THEMES:
            theme_name = "default"
        
        theme = self.THEMES[theme_name]
        self.colors: ColorScheme = theme["colors"]
        self.style: StyleConfig = theme["style"]
        self.current_theme = theme_name
    
    def get_status_color(self, status: str) -> str:
        """获取状态对应的颜色"""
        status_colors = {
            "completed": self.colors.success,
            "success": self.colors.success,
            "in_progress": self.colors.progress_primary,
            "running": self.colors.progress_primary,
            "failed": self.colors.error,
            "error": self.colors.error,
            "warning": self.colors.warning,
            "pending": self.colors.text_muted,
        }
        return status_colors.get(status.lower(), self.colors.info)
    
    def get_status_icon(self, status: str) -> str:
        """获取状态对应的图标"""
        status_icons = {
            "completed": "✅",
            "success": "✅",
            "in_progress": "🔄",
            "running": "🔄",
            "failed": "❌",
            "error": "❌",
            "warning": "⚠️",
            "pending": "⏳",
        }
        return status_icons.get(status.lower(), "❓")
    
    @classmethod
    def list_themes(cls) -> list:
        """列出所有可用主题"""
        return list(cls.THEMES.keys())
