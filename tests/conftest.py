"""
Pytest 配置文件
定义通用 fixtures 和测试配置
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_workspace():
    """创建临时工作目录"""
    workspace = tempfile.mkdtemp()
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def temp_config_file(temp_workspace):
    """创建临时配置文件"""
    config_content = """
name: test-agent
version: 1.0.0
workspace: .

opencode:
  enabled: true
  path: ""
  timeout: 300
  max_retries: 3

qwencode:
  enabled: true
  path: ""
  timeout: 180
  max_retries: 3

git:
  auto_commit: true
  auto_push: false
  branch_prefix: feature

test:
  auto_test: true
  coverage_threshold: 90.0
  test_framework: pytest

environment:
  python_version: "3.13"
  node_version: "22"
  auto_install: true

log:
  level: DEBUG
  save_json: true
"""
    config_path = Path(temp_workspace) / "test_config.yaml"
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    yield str(config_path)


@pytest.fixture
def mock_logger():
    """Mock logger"""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.critical = MagicMock()
    logger.tool_call = MagicMock()
    return logger


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run"""
    with patch('subprocess.run') as mock:
        yield mock


@pytest.fixture
def sample_task_plan():
    """创建示例任务计划"""
    from core.task_parser import TaskPlan, SubTask, TaskType, TaskPriority
    
    return TaskPlan(
        id="test_plan_001",
        title="测试任务计划",
        description="这是一个测试任务计划",
        original_request="请帮我写一个 Python 函数",
        subtasks=[
            SubTask(
                id="subtask_001",
                name="环境检查",
                description="检查开发环境",
                task_type=TaskType.ENVIRONMENT_SETUP,
                priority=TaskPriority.HIGH
            ),
            SubTask(
                id="subtask_002",
                name="代码生成",
                description="生成 Python 代码",
                task_type=TaskType.CODE_GENERATION,
                priority=TaskPriority.HIGH,
                dependencies=["subtask_001"]
            ),
            SubTask(
                id="subtask_003",
                name="测试执行",
                description="执行单元测试",
                task_type=TaskType.TESTING,
                priority=TaskPriority.HIGH,
                dependencies=["subtask_002"]
            ),
        ],
        status="pending"
    )


@pytest.fixture
def sample_subtask():
    """创建示例子任务"""
    from core.task_parser import SubTask, TaskType, TaskPriority
    
    return SubTask(
        id="test_subtask_001",
        name="测试子任务",
        description="这是一个测试子任务",
        task_type=TaskType.CODE_GENERATION,
        priority=TaskPriority.HIGH,
        metadata={"language": "python"}
    )


@pytest.fixture
def reset_global_logger():
    """重置全局 logger"""
    import utils.logger as logger_module
    logger_module._global_logger = None
    yield
    logger_module._global_logger = None


@pytest.fixture
def reset_tool_registry():
    """重置工具注册中心"""
    import adapters.tool_registry as registry_module
    registry_module._global_registry = None
    yield
    registry_module._global_registry = None
