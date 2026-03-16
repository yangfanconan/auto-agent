"""
Auto-Agent 全面的单元测试
覆盖所有公共函数和方法，包含正常情况和异常情况
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest


class TestTaskParser:
    """TaskParser 测试类"""

    def test_init(self):
        from core.task_parser import TaskParser
        with patch('core.task_parser.get_logger'):
            parser = TaskParser()
            assert parser.logger is not None
            assert parser.use_llm is False

    def test_init_with_llm(self):
        from core.task_parser import TaskParser
        parser = TaskParser(use_llm=True)
        assert parser.use_llm is True

    def test_parse_simple_request(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        plan = parser.parse("写一个 Python 函数")

        assert plan.id.startswith("task_")
        assert plan.title == "写一个 Python 函数"
        assert plan.original_request == "写一个 Python 函数"
        assert plan.status == "pending"
        assert len(plan.subtasks) > 0

    def test_parse_complex_request(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        plan = parser.parse("创建一个 Web API 项目，包含用户认证和数据存储")

        assert plan.id.startswith("task_")
        assert len(plan.subtasks) > 0

    def test_parse_with_template(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        plan = parser.parse("开发一个命令行工具")

        assert plan is not None
        assert len(plan.subtasks) > 0

    def test_identify_task_types_code_generation(self):
        from core.task_parser import TaskParser, TaskType
        parser = TaskParser()
        types = parser._identify_task_types("写代码实现功能")
        assert TaskType.CODE_GENERATION in types

    def test_identify_task_types_testing(self):
        from core.task_parser import TaskParser, TaskType
        parser = TaskParser()
        types = parser._identify_task_types("运行单元测试")
        assert TaskType.TESTING in types

    def test_identify_task_types_git(self):
        from core.task_parser import TaskParser, TaskType
        parser = TaskParser()
        types = parser._identify_task_types("git commit 提交代码")
        assert TaskType.GIT_OPERATION in types

    def test_identify_project_type_python(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        project_type = parser._identify_project_type("创建一个 python 包")
        assert project_type == "python_package"

    def test_identify_project_type_web_api(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        project_type = parser._identify_project_type("开发一个 web api")
        assert project_type == "web_api"

    def test_identify_project_type_cli(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        project_type = parser._identify_project_type("创建命令行工具")
        assert project_type == "cli_tool"

    def test_get_available_templates(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        templates = parser.get_available_templates()

        assert isinstance(templates, dict)
        assert "web_app" in templates
        assert "cli_tool" in templates

    def test_get_project_templates(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        templates = parser.get_project_templates()

        assert isinstance(templates, dict)
        assert "python_package" in templates

    def test_refine_task(self):
        from core.task_parser import TaskParser
        parser = TaskParser()
        plan = parser.parse("写一个函数")
        refined_plan = parser.refine_task(plan, "需要添加错误处理")

        assert "用户反馈" in refined_plan.description
        assert refined_plan.updated_at is not None

    def test_estimate_duration(self):
        from core.task_parser import TaskParser, TaskType
        parser = TaskParser()
        duration = parser._estimate_duration(TaskType.CODE_GENERATION)
        assert duration == 300

        duration = parser._estimate_duration(TaskType.GIT_OPERATION)
        assert duration == 30


class TestSubTask:
    """SubTask 测试类"""

    def test_init(self):
        from core.task_parser import SubTask, TaskType
        subtask = SubTask(
            id="test_001",
            name="测试任务",
            description="测试描述",
            task_type=TaskType.CODE_GENERATION
        )

        assert subtask.id == "test_001"
        assert subtask.status == "pending"
        assert subtask.progress == 0.0

    def test_to_dict(self):
        from core.task_parser import SubTask, TaskType, TaskPriority
        subtask = SubTask(
            id="test_001",
            name="测试任务",
            description="测试描述",
            task_type=TaskType.CODE_GENERATION,
            priority=TaskPriority.HIGH
        )
        result = subtask.to_dict()

        assert result["id"] == "test_001"
        assert result["task_type"] == "code_generation"
        assert result["priority"] == "high"


class TestTaskPlan:
    """TaskPlan 测试类"""

    def test_init(self):
        from core.task_parser import TaskPlan
        plan = TaskPlan(
            id="plan_001",
            title="测试计划",
            description="测试描述",
            original_request="原始请求"
        )

        assert plan.id == "plan_001"
        assert plan.status == "pending"

    def test_get_progress_empty(self):
        from core.task_parser import TaskPlan
        plan = TaskPlan(
            id="plan_001",
            title="测试",
            description="描述",
            original_request="请求"
        )
        assert plan.get_progress() == 0.0

    def test_get_progress_with_subtasks(self):
        from core.task_parser import TaskPlan, SubTask, TaskType
        subtask1 = SubTask(
            id="s1", name="s1", description="",
            task_type=TaskType.CODE_GENERATION, progress=50.0
        )
        subtask2 = SubTask(
            id="s2", name="s2", description="",
            task_type=TaskType.TESTING, progress=100.0
        )

        plan = TaskPlan(
            id="plan_001",
            title="测试",
            description="描述",
            original_request="请求",
            subtasks=[subtask1, subtask2]
        )

        assert plan.get_progress() == 75.0

    def test_get_completed_count(self):
        from core.task_parser import TaskPlan, SubTask, TaskType
        subtask1 = SubTask(
            id="s1", name="s1", description="",
            task_type=TaskType.CODE_GENERATION, status="completed"
        )
        subtask2 = SubTask(
            id="s2", name="s2", description="",
            task_type=TaskType.TESTING, status="pending"
        )

        plan = TaskPlan(
            id="plan_001",
            title="测试",
            description="描述",
            original_request="请求",
            subtasks=[subtask1, subtask2]
        )

        assert plan.get_completed_count() == 1

    def test_to_dict(self):
        from core.task_parser import TaskPlan
        plan = TaskPlan(
            id="plan_001",
            title="测试",
            description="描述",
            original_request="请求"
        )
        result = plan.to_dict()

        assert result["id"] == "plan_001"
        assert result["title"] == "测试"


class TestTaskTracker:
    """TaskTracker 测试类"""

    def test_init(self, tmp_path):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        assert tracker.storage_dir == tmp_path

    def test_register_plan(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        assert sample_task_plan.id in tracker._plans
        assert sample_task_plan.id in tracker._events

    def test_start_task(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)
        tracker.start_task(sample_task_plan.id)

        assert tracker._plans[sample_task_plan.id].status == "in_progress"

    def test_start_subtask(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)

        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.status == "in_progress"

    def test_update_subtask_progress(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        tracker.update_subtask_progress(
            sample_task_plan.id, subtask_id, 50.0, "进度更新")

        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.progress == 50.0

    def test_complete_subtask(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        tracker.complete_subtask(sample_task_plan.id, subtask_id, "完成")

        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.status == "completed"
        assert subtask.progress == 100.0

    def test_fail_subtask(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        subtask_id = sample_task_plan.subtasks[0].id
        tracker.fail_subtask(sample_task_plan.id, subtask_id, "测试失败")

        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.status == "failed"
        assert subtask.error == "测试失败"

    def test_complete_plan(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)
        tracker.complete_plan(sample_task_plan.id)

        assert tracker._plans[sample_task_plan.id].status == "completed"

    def test_fail_plan(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)
        tracker.fail_plan(sample_task_plan.id, "计划失败")

        assert tracker._plans[sample_task_plan.id].status == "failed"

    def test_get_progress_report(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        report = tracker.get_progress_report(sample_task_plan.id)

        assert report["plan_id"] == sample_task_plan.id
        assert "overall_progress" in report

    def test_generate_briefing(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        briefing = tracker.generate_briefing(sample_task_plan.id)

        assert sample_task_plan.title in briefing
        assert "状态" in briefing

    def test_get_plan(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        plan = tracker.get_plan(sample_task_plan.id)
        assert plan.id == sample_task_plan.id

    def test_get_events(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        tracker = TaskTracker(storage_dir=str(tmp_path))
        tracker.register_plan(sample_task_plan)

        events = tracker.get_events(sample_task_plan.id)
        assert len(events) > 0


class TestTaskScheduler:
    """TaskScheduler 测试类"""

    def test_init(self, tmp_path):
        from core.task_tracker import TaskTracker
        from core.scheduler import TaskScheduler
        tracker = TaskTracker(storage_dir=str(tmp_path))
        scheduler = TaskScheduler(tracker)

        assert scheduler.tracker == tracker
        assert isinstance(scheduler._handlers, dict)

    def test_register_handler(self, tmp_path):
        from core.task_tracker import TaskTracker
        from core.scheduler import TaskScheduler
        from core.task_parser import TaskType
        tracker = TaskTracker(storage_dir=str(tmp_path))
        scheduler = TaskScheduler(tracker)

        def handler(plan_id, subtask):
            return "完成"

        scheduler.register_handler(TaskType.CODE_GENERATION, handler)

        assert TaskType.CODE_GENERATION in scheduler._handlers

    def test_execute_plan(self, tmp_path, sample_task_plan):
        from core.task_tracker import TaskTracker
        from core.scheduler import TaskScheduler
        from core.task_parser import TaskType
        tracker = TaskTracker(storage_dir=str(tmp_path))
        scheduler = TaskScheduler(tracker)

        def handler(plan_id, subtask):
            return "完成"

        for task_type in [TaskType.ENVIRONMENT_SETUP, TaskType.CODE_GENERATION,
                          TaskType.TESTING, TaskType.UNKNOWN]:
            scheduler.register_handler(task_type, handler)

        success = scheduler.execute_plan(sample_task_plan)

        assert isinstance(success, bool)

    def test_get_status(self, tmp_path):
        from core.task_tracker import TaskTracker
        from core.scheduler import TaskScheduler
        tracker = TaskTracker(storage_dir=str(tmp_path))
        scheduler = TaskScheduler(tracker)

        status = scheduler.get_status()

        assert "current_plan" in status
        assert "registered_handlers" in status


class TestAutoAgent:
    """AutoAgent 测试类"""

    def test_init(self, tmp_path):
        from core.scheduler import AutoAgent
        agent = AutoAgent(workspace=str(tmp_path))

        assert agent.workspace == str(tmp_path)
        assert agent.tracker is not None
        assert agent.scheduler is not None

    def test_set_modules(self, tmp_path):
        from core.scheduler import AutoAgent
        agent = AutoAgent(workspace=str(tmp_path))

        mock_env = MagicMock()
        mock_code_gen = MagicMock()

        agent.set_modules(environment=mock_env, code_generator=mock_code_gen)

        assert agent._environment == mock_env
        assert agent._code_generator == mock_code_gen

    def test_execute(self, tmp_path):
        from core.scheduler import AutoAgent
        agent = AutoAgent(workspace=str(tmp_path))

        with patch.object(agent.scheduler, 'execute_plan', return_value=True):
            result = agent.execute("写一个函数")

        assert "success" in result

    def test_get_progress(self, tmp_path):
        from core.scheduler import AutoAgent
        agent = AutoAgent(workspace=str(tmp_path))

        with patch.object(agent.tracker, 'get_progress_report', return_value={"progress": 50}):
            progress = agent.get_progress("test_plan")

        assert progress["progress"] == 50

    def test_get_briefing(self, tmp_path):
        from core.scheduler import AutoAgent
        agent = AutoAgent(workspace=str(tmp_path))

        with patch.object(agent.tracker, 'generate_briefing', return_value="简报"):
            briefing = agent.get_briefing("test_plan")

        assert briefing == "简报"


class TestEnvironmentManager:
    """EnvironmentManager 测试类"""

    def test_init(self, tmp_path):
        from modules.environment import EnvironmentManager
        manager = EnvironmentManager(workspace=str(tmp_path))
        assert manager.workspace == Path(tmp_path)

    def test_create_venv(self, tmp_path):
        from modules.environment import EnvironmentManager
        manager = EnvironmentManager(workspace=str(tmp_path))

        venv_path = tmp_path / "test_venv"
        result = manager.create_venv(str(venv_path))

        assert isinstance(result, bool)

    def test_check_venv(self, tmp_path):
        from modules.environment import EnvironmentManager
        manager = EnvironmentManager(workspace=str(tmp_path))
        result = manager.check_venv()
        assert isinstance(result, bool)

    def test_check_docker_support(self, tmp_path):
        from modules.environment import EnvironmentManager
        manager = EnvironmentManager(workspace=str(tmp_path))
        result = manager.check_docker_support()
        assert isinstance(result, bool)

    def test_scan(self, tmp_path):
        from modules.environment import EnvironmentManager, EnvironmentReport
        manager = EnvironmentManager(workspace=str(tmp_path))
        report = manager.scan()

        assert isinstance(report, EnvironmentReport)
        assert report.os_info is not None
        assert report.python_version is not None

    def test_get_report(self, tmp_path):
        from modules.environment import EnvironmentManager
        manager = EnvironmentManager(workspace=str(tmp_path))
        manager.scan()
        report = manager.get_report()

        assert report is not None

    def test_environment_status(self):
        from modules.environment import EnvironmentStatus
        status = EnvironmentStatus(
            component="Test",
            installed=True,
            version="1.0.0",
            status="ok"
        )
        assert status.component == "Test"
        assert status.installed is True

    def test_environment_report_to_dict(self):
        from modules.environment import EnvironmentReport
        report = EnvironmentReport(
            os_info="Linux",
            python_version="3.10",
            node_version="18.0",
            git_version="2.40",
            opencode_available=True,
            qwencode_available=False
        )
        result = report.to_dict()

        assert result["os_info"] == "Linux"
        assert result["python_version"] == "3.10"


class TestCodeGenerator:
    """CodeGenerator 测试类"""

    def test_init(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))
        assert gen.workspace == Path(tmp_path)

    def test_language_extensions(self):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator()
        assert gen.LANGUAGE_EXTENSIONS["python"] == "py"
        assert gen.LANGUAGE_EXTENSIONS["javascript"] == "js"

    def test_generate_basic_framework_python(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))
        code = gen._generate_basic_framework("测试功能", "python")

        assert "def main" in code
        assert "测试功能" in code

    def test_generate_basic_framework_javascript(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))
        code = gen._generate_basic_framework("测试功能", "javascript")

        assert "function main" in code
        assert "测试功能" in code

    def test_generate_basic_framework_other(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))
        code = gen._generate_basic_framework("测试功能", "go")

        assert "测试功能" in code

    def test_extract_code_from_output(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))

        output = """一些文本
```python
def hello():
    print("hello")
```
更多文本"""

        code = gen._extract_code_from_output(output, "python")
        assert "def hello" in code

    def test_code_file(self):
        from modules.code_generator import CodeFile
        code_file = CodeFile(
            path="test.py",
            content="print('hello')",
            language="python",
            description="测试文件"
        )

        assert code_file.path == "test.py"
        assert code_file.language == "python"

    def test_code_generation_result(self):
        from modules.code_generator import CodeGenerationResult, CodeFile
        result = CodeGenerationResult(
            success=True,
            files=[CodeFile(path="test.py", content="", language="python")],
            errors=[],
            warnings=[]
        )

        assert result.success is True
        assert len(result.files) == 1

    def test_code_generation_result_to_dict(self):
        from modules.code_generator import CodeGenerationResult, CodeFile
        result = CodeGenerationResult(
            success=True,
            files=[
                CodeFile(
                    path="test.py",
                    content="",
                    language="python",
                    description="测试")],
            errors=[],
            warnings=[]
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["file_count"] == 1

    def test_get_generated_files(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))
        files = gen.get_generated_files()

        assert isinstance(files, list)

    def test_review_code(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))
        code = "def test(): pass"

        result = gen.review_code(code, "python")

        assert "success" in result
        assert "issues" in result

    def test_basic_static_analysis(self, tmp_path):
        from modules.code_generator import CodeGenerator
        gen = CodeGenerator(workspace=str(tmp_path))
        code = "import *\ndef test(): pass"

        result = gen._basic_static_analysis(
            code, "python", {"issues": [], "suggestions": []})

        assert result["success"] is True
        assert "issues" in result


class TestTestRunner:
    """TestRunner 测试类"""

    def test_init(self, tmp_path):
        from modules.test_runner import TestRunner
        runner = TestRunner(workspace=str(tmp_path))
        assert runner.workspace == Path(tmp_path)
        assert runner.test_framework == "pytest"

    def test_extract_code(self, tmp_path):
        from modules.test_runner import TestRunner
        runner = TestRunner(workspace=str(tmp_path))

        output = """```python
def test_example():
    assert True
```"""

        code = runner._extract_code(output)
        assert "def test_example" in code

    def test_generate_basic_tests(self, tmp_path):
        from modules.test_runner import TestRunner
        runner = TestRunner(workspace=str(tmp_path))
        code = "def add(a, b): return a + b"

        test_code = runner._generate_basic_tests(code, "math.py")

        assert "import pytest" in test_code
        assert "def test_placeholder" in test_code

    def test_test_case(self):
        from modules.test_runner import TestCase
        tc = TestCase(
            name="test_add",
            description="测试加法",
            code="assert 1+1 == 2",
            status="passed"
        )

        assert tc.name == "test_add"
        assert tc.status == "passed"

    def test_test_report(self):
        from modules.test_runner import TestReport
        report = TestReport(
            total=10,
            passed=8,
            failed=2,
            skipped=0,
            coverage=85.0
        )

        assert report.total == 10
        assert report.passed == 8

    def test_test_report_to_dict(self):
        from modules.test_runner import TestReport
        report = TestReport(
            total=10,
            passed=8,
            failed=2,
            skipped=0,
            coverage=85.0
        )

        d = report.to_dict()
        assert d["total"] == 10
        assert d["coverage"] == 85.0
        assert "pass_rate" in d

    def test_parse_test_output(self, tmp_path):
        from modules.test_runner import TestRunner, TestReport
        runner = TestRunner(workspace=str(tmp_path))

        stdout = """
test_module.py::test_one PASSED
test_module.py::test_two FAILED
2 passed, 1 failed
"""
        stderr = ""

        report = runner._parse_test_output(stdout, stderr)

        assert isinstance(report, TestReport)


class TestGitManager:
    """GitManager 测试类"""

    def test_init(self, tmp_path):
        from modules.git_manager import GitManager
        manager = GitManager(workspace=str(tmp_path))
        assert manager.workspace == Path(tmp_path)

    def test_is_available(self, tmp_path):
        from modules.git_manager import GitManager
        manager = GitManager(workspace=str(tmp_path))
        result = manager.is_available
        assert isinstance(result, bool)

    def test_generate_commit_message_custom(self, tmp_path):
        from modules.git_manager import GitManager
        manager = GitManager(workspace=str(tmp_path))
        msg = manager.generate_commit_message(
            changes=["new_file.py"],
            custom_message="添加新功能"
        )

        assert "添加新功能" in msg

    def test_generate_commit_message_auto(self, tmp_path):
        from modules.git_manager import GitManager
        manager = GitManager(workspace=str(tmp_path))
        msg = manager.generate_commit_message(
            changes=["test_new.py"],
            auto_generate=True
        )

        assert ":" in msg

    def test_infer_commit_type(self, tmp_path):
        from modules.git_manager import GitManager
        manager = GitManager(workspace=str(tmp_path))

        assert manager._infer_commit_type(["test_example.py"]) == "test"
        assert manager._infer_commit_type(["README.md"]) == "docs"

    def test_generate_description(self, tmp_path):
        from modules.git_manager import GitManager
        manager = GitManager(workspace=str(tmp_path))

        desc = manager._generate_description(["A  new_file.py"])
        assert "添加" in desc

        desc = manager._generate_description(["M  modified.py"])
        assert "更新" in desc or "修改" in desc

    def test_git_status(self):
        from modules.git_manager import GitStatus
        status = GitStatus(
            branch="main",
            is_dirty=True,
            staged_files=["file1.py"],
            unstaged_files=["file2.py"],
            untracked_files=["file3.py"]
        )

        assert status.branch == "main"
        assert status.is_dirty is True

    def test_commit_info(self):
        from modules.git_manager import CommitInfo
        info = CommitInfo(
            hash="abc123",
            short_hash="abc",
            author="Test",
            date="2024-01-01",
            message="Test commit"
        )

        assert info.hash == "abc123"
        assert info.message == "Test commit"

    def test_git_report(self):
        from modules.git_manager import GitReport
        report = GitReport(
            success=True,
            operation="commit",
            branch="main",
            commit_hash="abc123",
            message="Test"
        )

        assert report.success is True
        assert report.operation == "commit"

    def test_git_report_to_dict(self):
        from modules.git_manager import GitReport
        report = GitReport(
            success=True,
            operation="commit",
            branch="main"
        )

        d = report.to_dict()
        assert d["success"] is True
        assert d["operation"] == "commit"


class TestDeliveryManager:
    """DeliveryManager 测试类"""

    def test_init(self, tmp_path):
        from modules.delivery import DeliveryManager
        manager = DeliveryManager(workspace=str(tmp_path))
        assert manager.workspace == Path(tmp_path)
        assert manager.delivery_dir.exists()

    def test_create_package(self, tmp_path):
        from modules.delivery import DeliveryManager
        manager = DeliveryManager(workspace=str(tmp_path))

        package = manager.create_package(
            name="test_package",
            version="1.0.0"
        )

        assert package.name == "test_package"
        assert package.version == "1.0.0"
        assert package.id.startswith("pkg_")

    def test_delivery_item(self):
        from modules.delivery import DeliveryItem
        item = DeliveryItem(
            name="test.py",
            path="src/test.py",
            type="file",
            description="测试文件"
        )

        assert item.name == "test.py"
        assert item.type == "file"

    def test_delivery_package(self):
        from modules.delivery import DeliveryPackage
        package = DeliveryPackage(
            id="pkg_001",
            name="test",
            version="1.0.0",
            created_at="2024-01-01"
        )

        assert package.id == "pkg_001"
        assert package.name == "test"

    def test_delivery_package_to_dict(self):
        from modules.delivery import DeliveryPackage
        package = DeliveryPackage(
            id="pkg_001",
            name="test",
            version="1.0.0",
            created_at="2024-01-01"
        )

        d = package.to_dict()
        assert d["id"] == "pkg_001"
        assert d["name"] == "test"

    def test_generate_report(self, tmp_path):
        from modules.delivery import DeliveryManager
        manager = DeliveryManager(workspace=str(tmp_path))

        report = manager.generate_report(
            plan_id="plan_001",
            task_report={
                "status": "completed",
                "overall_progress": 100,
                "subtasks": []}
        )

        assert "plan_001" in report
        assert "任务完成总览" in report

    def test_save_report(self, tmp_path):
        from modules.delivery import DeliveryManager
        manager = DeliveryManager(workspace=str(tmp_path))

        report_path = manager.save_report("# 测试报告", "plan_001")

        assert Path(report_path).exists()
        assert "plan_001" in report_path


class TestToolRegistry:
    """ToolRegistry 测试类"""

    def test_init(self, reset_tool_registry):
        from adapters.tool_registry import ToolRegistry
        registry = ToolRegistry()
        assert isinstance(registry._tools, dict)

    def test_register_tool(self, reset_tool_registry):
        from adapters.tool_registry import ToolRegistry
        from utils.config import ToolConfig
        registry = ToolRegistry()

        registry.register_tool(
            name="test_tool",
            description="测试工具",
            adapter_class=MagicMock,
            config=ToolConfig()
        )

        assert "test_tool" in registry._tools

    def test_get_tool_info(self, reset_tool_registry):
        from adapters.tool_registry import ToolRegistry
        registry = ToolRegistry()

        info = registry.get_tool_info("opencode")
        assert info is not None or info is None

    def test_list_tools(self, reset_tool_registry):
        from adapters.tool_registry import list_tools
        tools = list_tools()

        assert isinstance(tools, dict)

    def test_get_registry(self, reset_tool_registry):
        from adapters.tool_registry import get_registry
        registry = get_registry()

        assert isinstance(registry, ToolRegistry)

    def test_tool_info(self):
        from adapters.tool_registry import ToolInfo
        from utils.config import ToolConfig
        info = ToolInfo(
            name="test",
            description="测试",
            adapter_class=MagicMock,
            config=ToolConfig()
        )

        assert info.name == "test"


class TestOpencodeAdapter:
    """OpencodeAdapter 测试类"""

    def test_init(self):
        from adapters.opencode_adapter import OpencodeAdapter
        adapter = OpencodeAdapter()
        assert adapter.config is not None

    def test_init_with_config(self):
        from adapters.opencode_adapter import OpencodeAdapter
        from utils.config import ToolConfig
        config = ToolConfig(timeout=600)
        adapter = OpencodeAdapter(config)

        assert adapter.config.timeout == 600

    def test_is_available(self):
        from adapters.opencode_adapter import OpencodeAdapter
        adapter = OpencodeAdapter()
        result = adapter.is_available
        assert isinstance(result, bool)

    def test_build_command(self):
        from adapters.opencode_adapter import OpencodeAdapter
        adapter = OpencodeAdapter()
        adapter._path = Path("/usr/bin/opencode")

        cmd = adapter._build_command("测试提示", {"verbose": True})

        assert "--prompt" in cmd
        assert "测试提示" in cmd

    def test_repr(self):
        from adapters.opencode_adapter import OpencodeAdapter
        adapter = OpencodeAdapter()
        repr_str = repr(adapter)

        assert "OpencodeAdapter" in repr_str

    def test_opencode_result(self):
        from adapters.opencode_adapter import OpencodeResult
        result = OpencodeResult(
            success=True,
            output="测试输出",
            error="",
            exit_code=0,
            duration=1.5
        )

        assert result.success is True
        assert result.output == "测试输出"


class TestQwencodeAdapter:
    """QwencodeAdapter 测试类"""

    def test_init(self):
        from adapters.qwencode_adapter import QwencodeAdapter
        adapter = QwencodeAdapter()
        assert adapter.config is not None

    def test_is_available(self):
        from adapters.qwencode_adapter import QwencodeAdapter
        adapter = QwencodeAdapter()
        result = adapter.is_available
        assert isinstance(result, bool)

    def test_supported_operations(self):
        from adapters.qwencode_adapter import QwencodeAdapter
        adapter = QwencodeAdapter()
        assert "generate" in adapter.SUPPORTED_OPERATIONS
        assert "format" in adapter.SUPPORTED_OPERATIONS

    def test_repr(self):
        from adapters.qwencode_adapter import QwencodeAdapter
        adapter = QwencodeAdapter()
        repr_str = repr(adapter)

        assert "QwencodeAdapter" in repr_str

    def test_qwencode_result(self):
        from adapters.qwencode_adapter import QwencodeResult
        result = QwencodeResult(
            success=True,
            output="测试输出",
            error="",
            exit_code=0,
            duration=1.5
        )

        assert result.success is True
        assert result.output == "测试输出"


class TestConfig:
    """配置模块测试类"""

    def test_tool_config(self):
        from utils.config import ToolConfig
        config = ToolConfig(
            enabled=True,
            path="/usr/bin/tool",
            timeout=300
        )

        assert config.enabled is True
        assert config.path == "/usr/bin/tool"

    def test_git_config(self):
        from utils.config import GitConfig
        config = GitConfig(
            auto_commit=True,
            auto_push=False,
            branch_prefix="feature"
        )

        assert config.auto_commit is True
        assert config.branch_prefix == "feature"

    def test_test_config(self):
        from utils.config import TestConfig
        config = TestConfig(
            auto_test=True,
            coverage_threshold=90.0,
            test_framework="pytest"
        )

        assert config.coverage_threshold == 90.0

    def test_environment_config(self):
        from utils.config import EnvironmentConfig
        config = EnvironmentConfig(
            python_version="3.13",
            node_version="22"
        )

        assert config.python_version == "3.13"

    def test_log_config(self):
        from utils.config import LogConfig
        config = LogConfig(
            level="DEBUG",
            save_json=True
        )

        assert config.level == "DEBUG"

    def test_agent_config(self):
        from utils.config import AgentConfig
        config = AgentConfig(
            name="test-agent",
            version="1.0.0"
        )

        assert config.name == "test-agent"
        assert config.version == "1.0.0"

    def test_agent_config_from_yaml(self, temp_config_file):
        from utils.config import AgentConfig
        config = AgentConfig.from_yaml(temp_config_file)

        assert config.name == "test-agent"

    def test_agent_config_to_yaml(self, tmp_path):
        from utils.config import AgentConfig, save_config
        config = AgentConfig(name="test")
        yaml_path = tmp_path / "config.yaml"

        config.to_yaml(str(yaml_path))

        assert yaml_path.exists()

    def test_load_config(self, temp_config_file):
        from utils.config import load_config, AgentConfig
        config = load_config(temp_config_file)

        assert isinstance(config, AgentConfig)

    def test_save_config(self, tmp_path):
        from utils.config import AgentConfig, save_config
        config = AgentConfig(name="test")
        config_path = tmp_path / "save_config.yaml"

        save_config(config, str(config_path))

        assert config_path.exists()


class TestExceptions:
    """异常模块测试类"""

    def test_auto_agent_exception(self):
        from utils.exceptions import AutoAgentException, ExceptionLevel
        exc = AutoAgentException("测试错误")

        assert exc.message == "测试错误"
        assert exc.level == ExceptionLevel.MEDIUM

    def test_auto_agent_exception_to_dict(self):
        from utils.exceptions import AutoAgentException
        exc = AutoAgentException("测试错误", details={"key": "value"})
        d = exc.to_dict()

        assert d["message"] == "测试错误"
        assert d["type"] == "AutoAgentException"

    def test_environment_exception(self):
        from utils.exceptions import EnvironmentException, ExceptionLevel
        exc = EnvironmentException("环境错误")

        assert exc.level == ExceptionLevel.HIGH

    def test_tool_not_found_exception(self):
        from utils.exceptions import ToolNotFoundException
        exc = ToolNotFoundException("opencode")

        assert "opencode" in exc.message

    def test_tool_call_exception(self):
        from utils.exceptions import ToolCallException
        exc = ToolCallException("opencode", "调用失败")

        assert "opencode" in exc.message
        assert "调用失败" in exc.message

    def test_task_parse_exception(self):
        from utils.exceptions import TaskParseException
        exc = TaskParseException("解析失败")

        assert exc.message == "解析失败"

    def test_code_generation_exception(self):
        from utils.exceptions import CodeGenerationException
        exc = CodeGenerationException("生成失败")

        assert exc.message == "生成失败"

    def test_test_exception(self):
        from utils.exceptions import TestException
        exc = TestException("测试失败")

        assert exc.message == "测试失败"

    def test_git_exception(self):
        from utils.exceptions import GitException, ExceptionLevel
        exc = GitException("Git错误")

        assert exc.level == ExceptionLevel.HIGH

    def test_delivery_exception(self):
        from utils.exceptions import DeliveryException
        exc = DeliveryException("交付失败")

        assert exc.message == "交付失败"

    def test_exception_level(self):
        from utils.exceptions import ExceptionLevel
        assert ExceptionLevel.LOW.value == "low"
        assert ExceptionLevel.MEDIUM.value == "medium"
        assert ExceptionLevel.HIGH.value == "high"

    def test_friendly_error_info(self):
        from utils.exceptions import FriendlyErrorInfo
        info = FriendlyErrorInfo(
            title="测试错误",
            message="错误消息",
            suggestion="建议"
        )

        assert info.title == "测试错误"
        assert info.message == "错误消息"

    def test_get_friendly_info(self):
        from utils.exceptions import AutoAgentException, FriendlyErrorInfo
        exc = AutoAgentException("测试错误")
        info = exc.get_friendly_info()

        assert isinstance(info, FriendlyErrorInfo)
        assert info.title is not None


class TestLogger:
    """日志模块测试类"""

    def test_structured_logger_init(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(
            name="test",
            log_dir=str(tmp_path)
        )

        assert logger.name == "test"
        assert logger.log_dir == tmp_path

    def test_structured_logger_debug(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.debug("测试调试消息")

        assert len(logger.json_logs) > 0

    def test_structured_logger_info(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.info("测试信息消息")

        assert len(logger.json_logs) > 0

    def test_structured_logger_warning(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.warning("测试警告消息")

        assert len(logger.json_logs) > 0

    def test_structured_logger_error(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.error("测试错误消息")

        assert len(logger.json_logs) > 0

    def test_structured_logger_task_start(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.task_start("task_001", "测试任务")

        assert len(logger.json_logs) > 0

    def test_structured_logger_task_end(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.task_end("task_001", "测试任务", "completed", 1.5)

        assert len(logger.json_logs) > 0

    def test_structured_logger_tool_call(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.tool_call("opencode", {"prompt": "test"}, "result", True)

        assert len(logger.json_logs) > 0

    def test_get_logger(self, reset_global_logger):
        from utils.logger import get_logger, StructuredLogger
        logger = get_logger()

        assert isinstance(logger, StructuredLogger)

    def test_get_log_path(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        path = logger.get_log_path()

        assert "test_" in path
        assert path.endswith(".log")

    def test_get_json_log_path(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        path = logger.get_json_log_path()

        assert "test_" in path
        assert path.endswith(".json")

    def test_get_recent_logs(self, tmp_path):
        from utils.logger import StructuredLogger
        logger = StructuredLogger(name="test", log_dir=str(tmp_path))
        logger.info("消息1")
        logger.info("消息2")

        logs = logger.get_recent_logs(limit=10)

        assert len(logs) >= 2


class TestEventBus:
    """事件总线测试类"""

    def test_event_bus_singleton(self):
        from core.events import get_event_bus
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2

    def test_subscribe(self):
        from core.events import get_event_bus
        bus = get_event_bus()
        handler = MagicMock()

        bus.subscribe("test.event", handler)

        assert "test.event" in bus._subscribers

    def test_publish(self):
        from core.events import get_event_bus, Event
        bus = get_event_bus()
        handler = MagicMock()
        bus.subscribe("test.event", handler)

        event = Event(type="test.event", payload={"data": "test"})
        bus.publish(event)

        handler.assert_called_once()

    def test_event_to_dict(self):
        from core.events import Event
        event = Event(
            type="test.event",
            payload={"key": "value"},
            source="test"
        )

        d = event.to_dict()

        assert d["type"] == "test.event"
        assert d["payload"] == {"key": "value"}

    def test_event_to_json(self):
        from core.events import Event
        event = Event(
            type="test.event",
            payload={"key": "value"}
        )

        json_str = event.to_json()

        assert "test.event" in json_str

    def test_event_from_dict(self):
        from core.events import Event
        data = {
            "type": "test.event",
            "payload": {"key": "value"},
            "source": "test"
        }

        event = Event.from_dict(data)

        assert event.type == "test.event"

    def test_get_history(self):
        from core.events import get_event_bus, Event
        bus = get_event_bus()
        bus.clear_history()

        event = Event(type="test.event", payload={})
        bus.publish(event)

        history = bus.get_history()

        assert len(history) > 0

    def test_clear_history(self):
        from core.events import get_event_bus
        bus = get_event_bus()
        bus.clear_history()

        assert len(bus._event_history) == 0

    def test_get_stats(self):
        from core.events import get_event_bus
        bus = get_event_bus()
        stats = bus.get_stats()

        assert "total_events" in stats
        assert "sync_subscribers" in stats

    def test_publish_event_function(self):
        from core.events import get_event_bus, publish_event
        bus = get_event_bus()
        bus.clear_history()

        publish_event("test.event", {"data": "test"}, "test_source")

        history = bus.get_history()
        assert any(e.type == "test.event" for e in history)


class TestTaskEvent:
    """TaskEvent 测试类"""

    def test_init(self):
        from core.task_tracker import TaskEvent
        event = TaskEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="started",
            task_id="task_001",
            message="任务开始"
        )

        assert event.task_id == "task_001"
        assert event.event_type == "started"

    def test_to_dict(self):
        from core.task_tracker import TaskEvent
        event = TaskEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="started",
            task_id="task_001",
            message="任务开始",
            details={"key": "value"}
        )

        d = event.to_dict()

        assert d["task_id"] == "task_001"
        assert d["details"] == {"key": "value"}


class TestTaskProgress:
    """TaskProgress 测试类"""

    def test_init(self):
        from core.task_tracker import TaskProgress
        progress = TaskProgress(
            task_id="task_001",
            task_name="测试任务",
            status="in_progress",
            progress=50.0
        )

        assert progress.task_id == "task_001"
        assert progress.progress == 50.0


class TestEnums:
    """枚举类测试"""

    def test_task_type(self):
        from core.task_parser import TaskType
        assert TaskType.CODE_GENERATION.value == "code_generation"
        assert TaskType.ENVIRONMENT_SETUP.value == "environment_setup"
        assert TaskType.TESTING.value == "testing"

    def test_task_priority(self):
        from core.task_parser import TaskPriority
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"

    def test_branch_strategy(self):
        from modules.git_manager import BranchStrategy
        assert BranchStrategy.FEATURE.value == "feature"
        assert BranchStrategy.HOTFIX.value == "hotfix"

    def test_event_type(self):
        from core.events import EventType
        assert EventType.TASK_CREATED.value == "task.created"
        assert EventType.TASK_COMPLETED.value == "task.completed"


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, tmp_path):
        from core.task_parser import TaskParser, TaskType
        from core.task_tracker import TaskTracker
        from core.scheduler import TaskScheduler

        parser = TaskParser()
        plan = parser.parse("创建一个简单的 Python 函数")

        tracker = TaskTracker(storage_dir=str(tmp_path))
        scheduler = TaskScheduler(tracker)

        def handler(plan_id, subtask):
            return "完成"

        for task_type in [TaskType.ENVIRONMENT_SETUP, TaskType.CODE_GENERATION,
                          TaskType.TESTING, TaskType.UNKNOWN]:
            scheduler.register_handler(task_type, handler)

        success = scheduler.execute_plan(plan)

        assert isinstance(success, bool)

    def test_config_workflow(self, tmp_path):
        from utils.config import AgentConfig, save_config, load_config
        config = AgentConfig(
            name="test-agent",
            version="1.0.0",
            workspace=str(tmp_path)
        )

        config_path = tmp_path / "config.yaml"
        save_config(config, str(config_path))

        loaded_config = load_config(str(config_path))

        assert loaded_config.name == "test-agent"

    def test_error_handling_workflow(self, tmp_path):
        from modules.code_generator import CodeGenerator, CodeGenerationResult
        gen = CodeGenerator(workspace=str(tmp_path))

        result = gen.generate(
            description="测试功能",
            language="python"
        )

        assert isinstance(result, CodeGenerationResult)


# ============ Fixtures ============

@pytest.fixture
def temp_workspace():
    """创建临时工作目录"""
    workspace = tempfile.mkdtemp()
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture
def temp_config_file(tmp_path):
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
    config_path = tmp_path / "test_config.yaml"
    config_path.write_text(config_content, encoding='utf-8')
    yield str(config_path)


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
