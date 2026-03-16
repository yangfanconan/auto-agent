"""
环境管理器单元测试
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from modules.environment import (
    EnvironmentManager,
    EnvironmentReport,
    EnvironmentStatus
)


class TestEnvironmentStatus:
    """测试 EnvironmentStatus 数据类"""

    def test_environment_status_creation(self):
        """测试创建环境状态"""
        status = EnvironmentStatus(
            component="Python",
            installed=True,
            version="3.13.0",
            path="/usr/bin/python3",
            status="ok",
            message="Python 已安装",
            auto_fixable=False
        )

        assert status.component == "Python"
        assert status.installed is True
        assert status.version == "3.13.0"
        assert status.path == "/usr/bin/python3"
        assert status.status == "ok"
        assert status.message == "Python 已安装"
        assert status.auto_fixable is False

    def test_environment_status_defaults(self):
        """测试默认值"""
        status = EnvironmentStatus(
            component="Test",
            installed=False
        )

        assert status.version is None
        assert status.path is None
        assert status.status == "unknown"
        assert status.message is None
        assert status.auto_fixable is False


class TestEnvironmentReport:
    """测试 EnvironmentReport 数据类"""

    def test_environment_report_creation(self):
        """测试创建环境报告"""
        report = EnvironmentReport(
            os_info="macOS 14.0",
            python_version="3.13.0",
            node_version="22.0.0",
            git_version="2.42.0",
            opencode_available=True,
            qwencode_available=False
        )

        assert report.os_info == "macOS 14.0"
        assert report.python_version == "3.13.0"
        assert report.node_version == "22.0.0"
        assert report.git_version == "2.42.0"
        assert report.opencode_available is True
        assert report.qwencode_available is False
        assert report.components == []
        assert report.issues == []
        assert report.recommendations == []

    def test_environment_report_to_dict(self):
        """测试转换为字典"""
        status = EnvironmentStatus(
            component="Python",
            installed=True,
            status="ok"
        )

        report = EnvironmentReport(
            os_info="macOS",
            python_version="3.13.0",
            node_version=None,
            git_version="2.42.0",
            opencode_available=True,
            qwencode_available=False,
            components=[status],
            issues=["Node.js 未安装"],
            recommendations=["安装 Node.js"]
        )

        result = report.to_dict()

        assert result["os_info"] == "macOS"
        assert result["python_version"] == "3.13.0"
        assert result["node_version"] is None
        assert len(result["components"]) == 1
        assert result["issues"] == ["Node.js 未安装"]
        assert result["recommendations"] == ["安装 Node.js"]


class TestEnvironmentManager:
    """测试 EnvironmentManager 类"""

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_manager_initialization(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试管理器初始化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        assert manager.workspace == Path(temp_workspace)
        assert manager._report is None

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    @patch('modules.environment.platform')
    @patch('modules.environment.sys')
    def test_scan_environment(
            self, mock_sys, mock_platform, mock_get_tool, mock_get_logger, temp_workspace):
        """测试扫描环境"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "23.0.0"
        mock_platform.machine.return_value = "arm64"

        mock_sys.version_info = MagicMock()
        mock_sys.version_info.major = 3
        mock_sys.version_info.minor = 13
        mock_sys.version_info.micro = 0

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch.object(manager, '_check_command') as mock_check:
            mock_check.return_value = (None, None)

            report = manager.scan()

            assert report is not None
            assert "Darwin" in report.os_info
            assert report.python_version == "3.13.0"

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_check_command_success(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试检查命令成功"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch('modules.environment.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="/usr/bin/node\nv22.0.0\n"
            )

            version, path = manager._check_command("node", "--version")

            assert version is not None or path is not None

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_check_command_failure(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试检查命令失败"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch('modules.environment.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")

            version, path = manager._check_command("nonexistent", "--version")

            assert version is None

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_check_command_exception(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试检查命令异常"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch('modules.environment.subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Command failed")

            version, path = manager._check_command("cmd", "--version")

            assert version is None
            assert path is None

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_fix_environment(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试修复环境"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch.object(manager, '_install_package') as mock_install:
            mock_install.return_value = True

            with patch.object(manager, 'scan') as mock_scan:
                mock_report = MagicMock()
                mock_report.components = []
                mock_scan.return_value = mock_report

                result = manager.fix()

                assert result is True

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_install_package_success(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试安装包成功"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch('modules.environment.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="", stderr="")

            result = manager._install_package("pytest")

            assert result is True

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_install_package_failure(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试安装包失败"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch('modules.environment.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="Error")

            result = manager._install_package("nonexistent-package")

            assert result is False

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_get_report(self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试获取报告"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        assert manager.get_report() is None

        manager._report = EnvironmentReport(
            os_info="Test",
            python_version="3.13.0",
            node_version=None,
            git_version=None,
            opencode_available=False,
            qwencode_available=False
        )

        assert manager.get_report() is not None

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_setup_task_handler(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试任务处理器接口"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        with patch.object(manager, 'scan') as mock_scan:
            mock_report = MagicMock()
            mock_report.os_info = "Test OS"
            mock_report.python_version = "3.13.0"
            mock_report.node_version = "22.0.0"
            mock_report.git_version = "2.42.0"
            mock_report.opencode_available = True
            mock_report.qwencode_available = False
            mock_report.issues = []
            mock_scan.return_value = mock_report

            mock_subtask = MagicMock()

            result = manager.setup("plan_001", mock_subtask)

            assert "环境检查完成" in result

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_check_python_dependencies(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试检查 Python 依赖"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        components = []
        issues = []
        recommendations = []

        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = MagicMock()

            manager._check_python_dependencies(
                components, issues, recommendations)

            assert len(components) > 0

    @patch('modules.environment.get_logger')
    @patch('modules.environment.get_tool')
    def test_check_project_dependencies(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试检查项目依赖"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        manager = EnvironmentManager(workspace=temp_workspace)

        Path(temp_workspace, "requirements.txt").write_text("pytest")
        Path(temp_workspace, "package.json").write_text("{}")

        components = []
        issues = []
        recommendations = []

        manager._check_project_dependencies(
            components, issues, recommendations)

        component_names = [c.component for c in components]
        assert "requirements.txt" in component_names
        assert "package.json" in component_names
