"""
测试 __init__.py 模块导出
"""

import pytest


class TestModuleImports:
    """测试模块导入"""

    def test_import_auto_agent(self):
        """测试主模块导入"""
        import auto_agent

        assert hasattr(auto_agent, '__version__')
        assert hasattr(auto_agent, '__author__')
        assert auto_agent.__version__ == "1.0.0"

    def test_import_core_classes(self):
        """测试核心类导入"""
        from auto_agent import (
            AutoAgent,
            TaskParser,
            TaskTracker,
            TaskScheduler,
        )

        assert AutoAgent is not None
        assert TaskParser is not None
        assert TaskTracker is not None
        assert TaskScheduler is not None

    def test_import_module_classes(self):
        """测试模块类导入"""
        from auto_agent import (
            EnvironmentManager,
            CodeGenerator,
            TestRunner,
            GitManager,
            DeliveryManager,
        )

        assert EnvironmentManager is not None
        assert CodeGenerator is not None
        assert TestRunner is not None
        assert GitManager is not None
        assert DeliveryManager is not None

    def test_import_adapter_classes(self):
        """测试适配器类导入"""
        from auto_agent import (
            OpencodeAdapter,
            QwencodeAdapter,
            get_tool,
            list_tools,
        )

        assert OpencodeAdapter is not None
        assert QwencodeAdapter is not None
        assert callable(get_tool)
        assert callable(list_tools)

    def test_import_util_functions(self):
        """测试工具函数导入"""
        from auto_agent import (
            load_config,
            save_config,
            get_logger,
        )

        assert callable(load_config)
        assert callable(save_config)
        assert callable(get_logger)

    def test_all_exports_defined(self):
        """测试 __all__ 导出"""
        import auto_agent

        expected_exports = [
            'AutoAgent',
            'TaskParser',
            'TaskTracker',
            'TaskScheduler',
            'EnvironmentManager',
            'CodeGenerator',
            'TestRunner',
            'GitManager',
            'DeliveryManager',
            'OpencodeAdapter',
            'QwencodeAdapter',
            'get_tool',
            'list_tools',
            'load_config',
            'save_config',
            'get_logger',
        ]

        for export in expected_exports:
            assert export in auto_agent.__all__, f"Missing export: {export}"
