"""
测试 UI 组件模块
"""

import pytest
from ui.themes import ThemeManager, ColorScheme, StyleConfig
from ui.components import TaskPanel, StatusTable, ProgressDisplay


class TestThemeManager:
    """主题管理器测试"""

    def test_default_theme_exists(self):
        """测试默认主题存在"""
        theme = ThemeManager()
        assert theme.current_theme == "default"
        assert theme.colors is not None

    def test_list_themes(self):
        """测试列出主题"""
        themes = ThemeManager.list_themes()
        assert "default" in themes
        assert len(themes) >= 4  # default, dark, light, monokai

    def test_load_theme(self):
        """测试加载主题"""
        theme = ThemeManager()
        theme.load_theme("dark")
        assert theme.current_theme == "dark"

    def test_get_status_color(self):
        """测试获取状态颜色"""
        theme = ThemeManager()

        assert theme.get_status_color("completed") == "green"
        assert theme.get_status_color("success") == "green"
        assert theme.get_status_color("failed") == "red"
        assert theme.get_status_color("in_progress") == "cyan"
        assert theme.get_status_color("pending") == "dim"

    def test_get_status_icon(self):
        """测试获取状态图标"""
        theme = ThemeManager()

        assert theme.get_status_icon("completed") == "✅"
        assert theme.get_status_icon("failed") == "❌"
        assert theme.get_status_icon("in_progress") == "🔄"
        assert theme.get_status_icon("pending") == "⏳"

    def test_unknown_status(self):
        """测试未知状态"""
        theme = ThemeManager()

        color = theme.get_status_color("unknown_status")
        assert color is not None  # 应返回默认颜色

        icon = theme.get_status_icon("unknown_status")
        assert icon is not None


class TestTaskPanel:
    """任务面板测试"""

    def test_create_panel(self):
        """测试创建面板"""
        panel = TaskPanel()
        result = panel.create("测试标题", "测试内容", "info")

        assert result is not None
        assert hasattr(result, 'renderable')

    def test_create_success_panel(self):
        """测试创建成功面板"""
        panel = TaskPanel()
        result = panel.create("成功", "操作完成", "success")

        assert result is not None

    def test_create_error_panel(self):
        """测试创建错误面板"""
        panel = TaskPanel()
        result = panel.create_error("发生错误", "建议操作")

        assert result is not None
        assert "💡" in str(result.renderable)

    def test_create_help_panel(self):
        """测试创建帮助面板"""
        panel = TaskPanel()
        commands = {"help": "显示帮助", "quit": "退出"}
        result = panel.create_help(commands)

        assert result is not None

    def test_create_task_result(self):
        """测试创建任务结果面板"""
        panel = TaskPanel()
        result_data = {
            "success": True,
            "overall_progress": 100.0,
            "subtasks": [
                {"name": "任务 1", "status": "completed"},
                {"name": "任务 2", "status": "completed"},
            ]
        }
        result = panel.create_task_result(result_data)

        assert result is not None


class TestStatusTable:
    """状态表格测试"""

    def test_create_subtasks_table(self):
        """测试创建子任务表格"""
        table = StatusTable()
        subtasks = [
            {"name": "任务 1",
             "status": "completed",
             "task_type": "code_generation",
             "progress": 100},
            {"name": "任务 2", "status": "in_progress",
                "task_type": "testing", "progress": 50},
            {"name": "任务 3",
             "status": "pending",
             "task_type": "git_operation",
             "progress": 0},
        ]

        result = table.create_subtasks_table(subtasks)
        assert result is not None

    def test_create_environment_table(self):
        """测试创建环境表格"""
        table = StatusTable()
        env_report = {
            "os_info": "macOS 14.0",
            "python_version": "3.11.0",
            "git_version": "2.40.0",
            "opencode_available": True,
            "qwencode_available": False,
        }

        result = table.create_environment_table(env_report)
        assert result is not None


class TestProgressDisplay:
    """进度显示测试"""

    def test_create_progress(self):
        """测试创建进度条"""
        display = ProgressDisplay()
        progress = display.create_progress("测试中...")

        assert progress is not None

    def test_default_theme(self):
        """测试默认主题"""
        display = ProgressDisplay()
        assert display.theme is not None
