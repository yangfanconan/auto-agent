"""
Auto-Agent 包初始化模块单元测试

测试所有公共模块、类和函数的导入
"""

import pytest
from unittest.mock import patch, MagicMock


class TestModuleImports:
    """测试模块导入"""
    
    def test_version(self):
        """测试版本号"""
        import auto_agent
        assert hasattr(auto_agent, '__version__')
        assert auto_agent.__version__ == "1.0.0"
    
    def test_author(self):
        """测试作者信息"""
        import auto_agent
        assert hasattr(auto_agent, '__author__')
        assert auto_agent.__author__ == "Auto-Agent Team"


class TestCoreImports:
    """测试核心模块导入"""
    
    def test_import_auto_agent(self):
        """测试导入 AutoAgent"""
        from auto_agent import AutoAgent
        assert AutoAgent is not None
    
    def test_import_task_parser(self):
        """测试导入 TaskParser"""
        from auto_agent import TaskParser
        assert TaskParser is not None
    
    def test_import_task_tracker(self):
        """测试导入 TaskTracker"""
        from auto_agent import TaskTracker
        assert TaskTracker is not None
    
    def test_import_task_scheduler(self):
        """测试导入 TaskScheduler"""
        from auto_agent import TaskScheduler
        assert TaskScheduler is not None


class TestModulesImports:
    """测试功能模块导入"""
    
    def test_import_environment_manager(self):
        """测试导入 EnvironmentManager"""
        from auto_agent import EnvironmentManager
        assert EnvironmentManager is not None
    
    def test_import_code_generator(self):
        """测试导入 CodeGenerator"""
        from auto_agent import CodeGenerator
        assert CodeGenerator is not None
    
    def test_import_test_runner(self):
        """测试导入 TestRunner"""
        from auto_agent import TestRunner
        assert TestRunner is not None
    
    def test_import_git_manager(self):
        """测试导入 GitManager"""
        from auto_agent import GitManager
        assert GitManager is not None
    
    def test_import_delivery_manager(self):
        """测试导入 DeliveryManager"""
        from auto_agent import DeliveryManager
        assert DeliveryManager is not None


class TestAdaptersImports:
    """测试适配器模块导入"""
    
    def test_import_opencode_adapter(self):
        """测试导入 OpencodeAdapter"""
        from auto_agent import OpencodeAdapter
        assert OpencodeAdapter is not None
    
    def test_import_qwencode_adapter(self):
        """测试导入 QwencodeAdapter"""
        from auto_agent import QwencodeAdapter
        assert QwencodeAdapter is not None
    
    def test_import_get_tool(self):
        """测试导入 get_tool"""
        from auto_agent import get_tool
        assert callable(get_tool)
    
    def test_import_list_tools(self):
        """测试导入 list_tools"""
        from auto_agent import list_tools
        assert callable(list_tools)


class TestUtilsImports:
    """测试工具模块导入"""
    
    def test_import_load_config(self):
        """测试导入 load_config"""
        from auto_agent import load_config
        assert callable(load_config)
    
    def test_import_save_config(self):
        """测试导入 save_config"""
        from auto_agent import save_config
        assert callable(save_config)
    
    def test_import_get_logger(self):
        """测试导入 get_logger"""
        from auto_agent import get_logger
        assert callable(get_logger)


class TestAllExports:
    """测试 __all__ 导出列表"""
    
    def test_all_exports_available(self):
        """测试所有 __all__ 中的导出都可访问"""
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
            assert hasattr(auto_agent, export), f"Missing export: {export}"
    
    def test_all_list_completeness(self):
        """测试 __all__ 列表完整性"""
        import auto_agent
        
        assert '__all__' in dir(auto_agent)
        
        all_list = auto_agent.__all__
        assert len(all_list) == 16
        
        expected_items = {
            'AutoAgent', 'TaskParser', 'TaskTracker', 'TaskScheduler',
            'EnvironmentManager', 'CodeGenerator', 'TestRunner',
            'GitManager', 'DeliveryManager',
            'OpencodeAdapter', 'QwencodeAdapter', 'get_tool', 'list_tools',
            'load_config', 'save_config', 'get_logger',
        }
        
        assert set(all_list) == expected_items


class TestCoreClassesInstantiation:
    """测试核心类实例化"""
    
    @patch('auto_agent.core.scheduler.get_logger')
    @patch('auto_agent.core.scheduler.TaskTracker')
    def test_auto_agent_instantiation(self, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试 AutoAgent 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        from auto_agent import AutoAgent
        
        agent = AutoAgent(workspace=temp_workspace)
        assert agent.workspace == temp_workspace
        assert agent.config == {}
    
    @patch('auto_agent.core.task_parser.get_logger')
    def test_task_parser_instantiation(self, mock_get_logger):
        """测试 TaskParser 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        from auto_agent import TaskParser
        
        parser = TaskParser()
        assert parser is not None
        assert parser.use_llm is False
    
    @patch('auto_agent.core.task_tracker.get_logger')
    def test_task_tracker_instantiation(self, mock_get_logger, temp_workspace):
        """测试 TaskTracker 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        from auto_agent import TaskTracker
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        assert tracker is not None
    
    @patch('auto_agent.core.scheduler.get_logger')
    def test_task_scheduler_instantiation(self, mock_get_logger):
        """测试 TaskScheduler 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        from auto_agent import TaskScheduler, TaskTracker
        
        tracker = MagicMock()
        scheduler = TaskScheduler(tracker)
        assert scheduler is not None


class TestModulesClassesInstantiation:
    """测试功能模块类实例化"""
    
    @patch('auto_agent.modules.environment.get_logger')
    @patch('auto_agent.modules.environment.get_tool')
    def test_environment_manager_instantiation(self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试 EnvironmentManager 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None
        
        from auto_agent import EnvironmentManager
        
        manager = EnvironmentManager(workspace=temp_workspace)
        assert manager is not None
        assert str(manager.workspace) == temp_workspace
    
    @patch('auto_agent.modules.code_generator.get_logger')
    @patch('auto_agent.modules.code_generator.get_tool')
    def test_code_generator_instantiation(self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试 CodeGenerator 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None
        
        from auto_agent import CodeGenerator
        
        generator = CodeGenerator(workspace=temp_workspace)
        assert generator is not None
    
    @patch('auto_agent.modules.test_runner.get_logger')
    @patch('auto_agent.modules.test_runner.get_tool')
    def test_test_runner_instantiation(self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试 TestRunner 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None
        
        from auto_agent import TestRunner
        
        runner = TestRunner(workspace=temp_workspace)
        assert runner is not None
    
    @patch('auto_agent.modules.git_manager.get_logger')
    def test_git_manager_instantiation(self, mock_get_logger, temp_workspace):
        """测试 GitManager 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        from auto_agent import GitManager
        
        manager = GitManager(workspace=temp_workspace)
        assert manager is not None
    
    @patch('auto_agent.modules.delivery.get_logger')
    def test_delivery_manager_instantiation(self, mock_get_logger, temp_workspace):
        """测试 DeliveryManager 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        from auto_agent import DeliveryManager
        
        manager = DeliveryManager(workspace=temp_workspace)
        assert manager is not None


class TestAdaptersClassesInstantiation:
    """测试适配器类实例化"""
    
    @patch('auto_agent.adapters.opencode_adapter.get_logger')
    def test_opencode_adapter_instantiation(self, mock_get_logger):
        """测试 OpencodeAdapter 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        from auto_agent import OpencodeAdapter
        from auto_agent.utils.config import ToolConfig
        
        config = ToolConfig(enabled=True, timeout=300)
        adapter = OpencodeAdapter(config)
        assert adapter is not None
    
    @patch('auto_agent.adapters.qwencode_adapter.get_logger')
    def test_qwencode_adapter_instantiation(self, mock_get_logger):
        """测试 QwencodeAdapter 实例化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        from auto_agent import QwencodeAdapter
        from auto_agent.utils.config import ToolConfig
        
        config = ToolConfig(enabled=True, timeout=180)
        adapter = QwencodeAdapter(config)
        assert adapter is not None


class TestUtilsFunctions:
    """测试工具函数"""
    
    @patch('auto_agent.utils.config.Path')
    def test_load_config_default(self, mock_path, temp_config_file):
        """测试 load_config 使用默认路径"""
        from auto_agent import load_config
        
        mock_path.return_value.exists.return_value = False
        config = load_config()
        assert config is not None
    
    def test_load_config_with_path(self, temp_config_file):
        """测试 load_config 指定路径"""
        from auto_agent import load_config
        
        config = load_config(temp_config_file)
        assert config is not None
        assert config.name == "test-agent"
    
    def test_save_config(self, temp_workspace):
        """测试 save_config"""
        from auto_agent import save_config, load_config
        from auto_agent.utils.config import AgentConfig
        
        config = AgentConfig(name="test-save", version="2.0.0")
        save_path = f"{temp_workspace}/test_save_config.yaml"
        
        save_config(config, save_path)
        
        loaded = load_config(save_path)
        assert loaded.name == "test-save"
        assert loaded.version == "2.0.0"
    
    def test_get_logger(self, temp_workspace, reset_global_logger):
        """测试 get_logger"""
        from auto_agent import get_logger
        
        logger = get_logger("test-logger", log_dir=temp_workspace)
        assert logger is not None
        assert logger.name == "test-logger"


class TestToolRegistry:
    """测试工具注册中心"""
    
    def test_list_tools(self, reset_tool_registry):
        """测试 list_tools"""
        from auto_agent import list_tools
        
        tools = list_tools()
        assert isinstance(tools, dict)
        assert "opencode" in tools
        assert "qwencode" in tools
    
    def test_get_tool_existing(self, reset_tool_registry):
        """测试 get_tool 获取存在的工具"""
        from auto_agent import get_tool, list_tools
        
        tools = list_tools()
        if tools.get("opencode", {}).get("enabled"):
            tool = get_tool("opencode")
            if tools.get("opencode", {}).get("available"):
                assert tool is not None
    
    def test_get_tool_non_existing(self, reset_tool_registry):
        """测试 get_tool 获取不存在的工具"""
        from auto_agent import get_tool
        
        tool = get_tool("non_existent_tool")
        assert tool is None


class TestModuleStructure:
    """测试模块结构"""
    
    def test_core_module_structure(self):
        """测试核心模块结构"""
        from auto_agent import core
        
        assert hasattr(core, 'AutoAgent')
        assert hasattr(core, 'TaskParser')
        assert hasattr(core, 'TaskTracker')
        assert hasattr(core, 'TaskScheduler')
    
    def test_modules_module_structure(self):
        """测试功能模块结构"""
        from auto_agent import modules
        
        assert hasattr(modules, 'EnvironmentManager')
        assert hasattr(modules, 'CodeGenerator')
        assert hasattr(modules, 'TestRunner')
        assert hasattr(modules, 'GitManager')
        assert hasattr(modules, 'DeliveryManager')
    
    def test_adapters_module_structure(self):
        """测试适配器模块结构"""
        from auto_agent import adapters
        
        assert hasattr(adapters, 'OpencodeAdapter')
        assert hasattr(adapters, 'QwencodeAdapter')
        assert hasattr(adapters, 'get_tool')
        assert hasattr(adapters, 'list_tools')
    
    def test_utils_module_structure(self):
        """测试工具模块结构"""
        from auto_agent import utils
        
        assert hasattr(utils, 'load_config')
        assert hasattr(utils, 'save_config')
        assert hasattr(utils, 'get_logger')
        assert hasattr(utils, 'AutoAgentException')


class TestIntegration:
    """集成测试"""
    
    @patch('auto_agent.core.scheduler.get_logger')
    @patch('auto_agent.core.scheduler.TaskTracker')
    @patch('auto_agent.core.task_parser.get_logger')
    def test_full_workflow_mock(self, mock_parser_logger, mock_tracker_class, mock_scheduler_logger, temp_workspace):
        """测试完整工作流程（使用 Mock）"""
        mock_logger = MagicMock()
        mock_parser_logger.return_value = mock_logger
        mock_scheduler_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        from auto_agent import AutoAgent, TaskParser
        
        parser = TaskParser()
        plan = parser.parse("写一个 hello world 函数")
        
        assert plan is not None
        assert plan.original_request == "写一个 hello world 函数"
        assert len(plan.subtasks) > 0
    
    def test_exception_imports(self):
        """测试异常类导入"""
        from auto_agent.utils import (
            AutoAgentException,
            EnvironmentException,
            ToolNotFoundException,
            ToolCallException,
            TaskParseException,
            CodeGenerationException,
            TestException,
            GitException,
            DeliveryException,
            ExceptionLevel,
        )
        
        assert AutoAgentException is not None
        assert EnvironmentException is not None
        assert ToolNotFoundException is not None
        assert ToolCallException is not None
        assert TaskParseException is not None
        assert CodeGenerationException is not None
        assert TestException is not None
        assert GitException is not None
        assert DeliveryException is not None
        assert ExceptionLevel is not None
    
    def test_exception_functionality(self):
        """测试异常功能"""
        from auto_agent.utils import AutoAgentException, ExceptionLevel
        
        exc = AutoAgentException(
            message="Test error",
            level=ExceptionLevel.HIGH,
            details={"key": "value"},
            suggestion="Test suggestion"
        )
        
        assert exc.message == "Test error"
        assert exc.level == ExceptionLevel.HIGH
        assert exc.details == {"key": "value"}
        assert exc.suggestion == "Test suggestion"
        
        exc_dict = exc.to_dict()
        assert exc_dict["type"] == "AutoAgentException"
        assert exc_dict["message"] == "Test error"
        assert exc_dict["level"] == "high"
    
    def test_config_classes(self):
        """测试配置类"""
        from auto_agent.utils.config import (
            AgentConfig,
            ToolConfig,
            GitConfig,
            TestConfig,
            EnvironmentConfig,
            LogConfig,
        )
        
        tool_config = ToolConfig(enabled=True, timeout=300)
        assert tool_config.enabled is True
        assert tool_config.timeout == 300
        
        git_config = GitConfig(auto_commit=True, auto_push=False)
        assert git_config.auto_commit is True
        assert git_config.auto_push is False
        
        test_config = TestConfig(coverage_threshold=90.0)
        assert test_config.coverage_threshold == 90.0
        
        env_config = EnvironmentConfig(python_version="3.13")
        assert env_config.python_version == "3.13"
        
        log_config = LogConfig(level="DEBUG")
        assert log_config.level == "DEBUG"
        
        agent_config = AgentConfig(
            name="test-agent",
            version="1.0.0",
            opencode=tool_config,
            git=git_config,
            test=test_config,
            environment=env_config,
            log=log_config,
        )
        assert agent_config.name == "test-agent"
        assert agent_config.version == "1.0.0"
