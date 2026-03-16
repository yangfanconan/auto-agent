"""
测试任务解析器模块
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from core.task_parser import (
    TaskParser, TaskPlan, SubTask, TaskType, TaskPriority,
    PROJECT_TEMPLATES, TASK_TEMPLATES
)


class TestSubTask:
    """测试 SubTask 数据类"""

    def test_subtask_creation(self):
        """测试创建子任务"""
        subtask = SubTask(
            id="task_001",
            name="测试任务",
            description="测试描述",
            task_type=TaskType.CODE_GENERATION
        )

        assert subtask.id == "task_001"
        assert subtask.name == "测试任务"
        assert subtask.task_type == TaskType.CODE_GENERATION
        assert subtask.priority == TaskPriority.MEDIUM
        assert subtask.status == "pending"
        assert subtask.progress == 0.0
        assert subtask.dependencies == []
        assert subtask.metadata == {}

    def test_subtask_to_dict(self):
        """测试子任务转换为字典"""
        subtask = SubTask(
            id="task_001",
            name="测试任务",
            description="测试描述",
            task_type=TaskType.CODE_GENERATION,
            priority=TaskPriority.HIGH,
            dependencies=["task_000"],
            status="completed",
            result="成功",
            error=None,
            progress=100.0,
            estimated_duration=60,
            actual_duration=55.5,
            metadata={"key": "value"}
        )

        result = subtask.to_dict()

        assert result["id"] == "task_001"
        assert result["name"] == "测试任务"
        assert result["task_type"] == "code_generation"
        assert result["priority"] == "high"
        assert result["dependencies"] == ["task_000"]
        assert result["status"] == "completed"
        assert result["result"] == "成功"
        assert result["progress"] == 100.0
        assert result["estimated_duration"] == 60
        assert result["actual_duration"] == 55.5
        assert result["metadata"] == {"key": "value"}


class TestTaskPlan:
    """测试 TaskPlan 数据类"""

    def test_plan_creation(self):
        """测试创建任务计划"""
        plan = TaskPlan(
            id="plan_001",
            title="测试计划",
            description="描述",
            original_request="请求"
        )

        assert plan.id == "plan_001"
        assert plan.status == "pending"
        assert plan.subtasks == []
        assert plan.metadata == {}

    def test_plan_to_dict(self):
        """测试计划转字典"""
        subtask = SubTask(
            id="task_001",
            name="任务",
            description="描述",
            task_type=TaskType.CODE_GENERATION
        )

        plan = TaskPlan(
            id="plan_001",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=[subtask],
            status="in_progress",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T01:00:00",
            metadata={"key": "value"},
            template_name="test_template"
        )

        result = plan.to_dict()

        assert result["id"] == "plan_001"
        assert result["title"] == "测试计划"
        assert len(result["subtasks"]) == 1
        assert result["status"] == "in_progress"
        assert result["template_name"] == "test_template"

    def test_plan_progress_empty(self):
        """测试空计划的进度"""
        plan = TaskPlan(
            id="plan_001",
            title="空计划",
            description="描述",
            original_request="请求"
        )

        assert plan.get_progress() == 0.0

    def test_plan_progress(self):
        """测试进度计算"""
        subtasks = [
            SubTask(
                id="t1",
                name="T1",
                description="D1",
                task_type=TaskType.CODE_GENERATION,
                progress=50.0),
            SubTask(
                id="t2",
                name="T2",
                description="D2",
                task_type=TaskType.TESTING,
                progress=100.0),
        ]

        plan = TaskPlan(
            id="plan_001",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=subtasks
        )

        assert plan.get_progress() == 75.0

    def test_completed_count(self):
        """测试完成计数"""
        subtasks = [
            SubTask(
                id="t1",
                name="T1",
                description="D1",
                task_type=TaskType.CODE_GENERATION,
                status="completed"),
            SubTask(
                id="t2",
                name="T2",
                description="D2",
                task_type=TaskType.TESTING,
                status="completed"),
            SubTask(
                id="t3",
                name="T3",
                description="D3",
                task_type=TaskType.TESTING,
                status="pending"),
        ]

        plan = TaskPlan(
            id="plan_001",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=subtasks
        )

        assert plan.get_completed_count() == 2

    def test_failed_count(self):
        """测试失败计数"""
        subtasks = [
            SubTask(
                id="t1",
                name="T1",
                description="D1",
                task_type=TaskType.CODE_GENERATION,
                status="failed"),
            SubTask(
                id="t2",
                name="T2",
                description="D2",
                task_type=TaskType.TESTING,
                status="completed"),
            SubTask(
                id="t3",
                name="T3",
                description="D3",
                task_type=TaskType.TESTING,
                status="failed"),
        ]

        plan = TaskPlan(
            id="plan_001",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=subtasks
        )

        assert plan.get_failed_count() == 2


class TestTaskParser:
    """任务解析器测试"""

    def test_parse_simple_request(self):
        """测试简单请求解析"""
        parser = TaskParser()
        plan = parser.parse("用 Python 写一个计算器")

        assert plan.id.startswith("task_")
        assert plan.title is not None
        assert len(plan.subtasks) >= 2
        assert any(
            t.task_type == TaskType.CODE_GENERATION for t in plan.subtasks)

    def test_parse_project_init(self):
        """测试项目初始化请求"""
        parser = TaskParser()
        plan = parser.parse("创建一个 Python 包项目")

        assert any(t.task_type == TaskType.PROJECT_INIT for t in plan.subtasks)
        assert plan.metadata.get("project_type") == "python_package"

    def test_parse_web_api_request(self):
        """测试 Web API 请求解析"""
        parser = TaskParser()
        plan = parser.parse("用 FastAPI 创建一个 Web API 服务")

        assert plan.metadata.get("project_type") == "web_api"
        assert any(t.task_type == TaskType.PROJECT_INIT for t in plan.subtasks)

    def test_parse_with_template(self):
        """测试模板匹配"""
        parser = TaskParser()
        plan = parser.parse("开发一个 Web 应用，包含前后端")

        # 应该匹配 web_app 模板
        assert plan.template_name is not None or len(plan.subtasks) >= 4

    def test_parse_test_request(self):
        """测试测试请求解析"""
        parser = TaskParser()
        plan = parser.parse("为 calculator.py 编写单元测试")

        assert any(t.task_type == TaskType.TESTING for t in plan.subtasks)

    def test_parse_git_request(self):
        """测试 Git 请求解析"""
        parser = TaskParser()
        plan = parser.parse("提交代码到 git 仓库")

        assert any(
            t.task_type == TaskType.GIT_OPERATION for t in plan.subtasks)

    def test_identify_project_type(self):
        """测试项目类型识别"""
        parser = TaskParser()

        assert parser._identify_project_type("创建一个 vue 前端项目") == "frontend_vue"
        assert parser._identify_project_type("react 前端开发") == "frontend_react"
        assert parser._identify_project_type("数据分析项目") == "data_science"
        assert parser._identify_project_type("普通 Python 脚本") is None

    def test_infer_commit_type(self):
        """测试提交类型推断"""
        parser = TaskParser()

        # 测试关键词匹配
        request = "创建一个新的 Python 包"
        task_types = parser._identify_task_types(request)
        assert TaskType.PROJECT_INIT in task_types or TaskType.CODE_GENERATION in task_types

    def test_generate_subtasks_with_dependencies(self):
        """测试子任务依赖生成"""
        parser = TaskParser()
        plan = parser.parse("用 Python 写一个排序算法并测试")

        # 检查依赖关系
        for task in plan.subtasks:
            if task.dependencies:
                for dep_id in task.dependencies:
                    # 依赖的任务应该存在
                    assert any(t.id == dep_id for t in plan.subtasks)

    def test_task_template_exists(self):
        """测试任务模板存在"""
        assert "web_app" in TASK_TEMPLATES
        assert "cli_tool" in TASK_TEMPLATES
        assert "python_lib" in TASK_TEMPLATES

    def test_project_template_exists(self):
        """测试项目模板存在"""
        assert "python_package" in PROJECT_TEMPLATES
        assert "web_api" in PROJECT_TEMPLATES
        assert "cli_tool" in PROJECT_TEMPLATES

    def test_parse_complex_request(self):
        """测试复杂请求解析"""
        parser = TaskParser()
        plan = parser.parse("""
        创建一个命令行工具项目，要求：
        1. 支持多个子命令
        2. 有完善的帮助文档
        3. 包含单元测试
        4. 可以发布到 PyPI
        """)

        assert len(plan.subtasks) >= 3
        assert any(
            t.task_type == TaskType.DOCUMENTATION for t in plan.subtasks)
        assert any(t.task_type == TaskType.TESTING for t in plan.subtasks)

    def test_get_available_templates(self):
        """测试获取可用模板"""
        parser = TaskParser()
        templates = parser.get_available_templates()

        assert len(templates) > 0
        assert "web_app" in templates

    def test_get_project_templates(self):
        """测试获取项目模板"""
        parser = TaskParser()
        templates = parser.get_project_templates()

        assert len(templates) > 0
        assert "python_package" in templates

    @patch('core.task_parser.get_logger')
    def test_parser_initialization(self, mock_get_logger):
        """测试解析器初始化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        parser = TaskParser(use_llm=True)

        assert parser.logger == mock_logger
        assert parser.use_llm is True

    def test_parse_empty_request(self):
        """测试空请求"""
        parser = TaskParser()
        plan = parser.parse("")

        assert plan is not None
        assert plan.title == "未命名任务"

    def test_parse_multiline_request(self):
        """测试多行请求"""
        parser = TaskParser()
        plan = parser.parse("第一行\n第二行\n第三行")

        assert plan.title == "第一行"

    def test_parse_long_title(self):
        """测试长标题截断"""
        parser = TaskParser()
        long_title = "这是一个非常长的标题" * 20
        plan = parser.parse(long_title)

        assert len(plan.title) <= 80

    def test_identify_task_types_multiple(self):
        """测试识别多个任务类型"""
        parser = TaskParser()
        task_types = parser._identify_task_types("写代码并测试")

        assert TaskType.CODE_GENERATION in task_types
        assert TaskType.TESTING in task_types

    def test_identify_task_types_unknown(self):
        """测试未知任务类型"""
        parser = TaskParser()
        task_types = parser._identify_task_types("随机文本无关键词")

        assert TaskType.CODE_GENERATION in task_types or TaskType.UNKNOWN in task_types

    def test_identify_task_types_optimization(self):
        """测试优化任务类型"""
        parser = TaskParser()
        task_types = parser._identify_task_types("优化代码性能")

        assert TaskType.OPTIMIZATION in task_types

    def test_match_task_template_cli(self):
        """测试匹配 CLI 工具模板"""
        parser = TaskParser()
        template = parser._match_task_template(
            "开发一个命令行工具", [TaskType.PROJECT_INIT])

        assert template is not None
        assert template["name"] == "命令行工具"

    def test_match_task_template_python_lib(self):
        """测试匹配 Python 库模板"""
        parser = TaskParser()
        template = parser._match_task_template(
            "创建一个 Python 库", [TaskType.PROJECT_INIT])

        assert template is not None
        assert template["name"] == "Python 库开发"

    def test_match_task_template_refactor(self):
        """测试匹配重构模板"""
        parser = TaskParser()
        template = parser._match_task_template(
            "审查并优化代码", [TaskType.CODE_REVIEW])

        assert template is not None

    def test_has_explicit_template(self):
        """测试检查显式模板标记"""
        parser = TaskParser()

        assert parser._has_explicit_template("简单快速实现") is True
        assert parser._has_explicit_template("只要核心功能") is True
        assert parser._has_explicit_template("完整功能实现") is False

    def test_estimate_duration(self):
        """测试预估任务耗时"""
        parser = TaskParser()

        assert parser._estimate_duration(TaskType.PROJECT_INIT) == 60
        assert parser._estimate_duration(TaskType.ENVIRONMENT_SETUP) == 120
        assert parser._estimate_duration(TaskType.CODE_GENERATION) == 300
        assert parser._estimate_duration(TaskType.UNKNOWN) == 120

    def test_get_dependencies(self):
        """测试获取依赖列表"""
        parser = TaskParser()
        subtasks = [
            SubTask(
                id="task_001",
                name="T1",
                description="D1",
                task_type=TaskType.CODE_GENERATION),
            SubTask(
                id="task_002",
                name="T2",
                description="D2",
                task_type=TaskType.TESTING),
        ]

        deps = parser._get_dependencies(
            subtasks, ["task_001", "task_002", "task_003"])

        assert deps == ["task_001", "task_002"]

    def test_refine_task(self):
        """测试优化任务计划"""
        parser = TaskParser()
        plan = parser.parse("测试任务")
        original_description = plan.description

        refined_plan = parser.refine_task(plan, "增加新功能")

        assert "增加新功能" in refined_plan.description
        assert refined_plan.updated_at is not None

    def test_parse_with_delivery(self):
        """测试包含交付的请求"""
        parser = TaskParser()
        plan = parser.parse("打包并发布项目")

        assert any(t.task_type == TaskType.DELIVERY for t in plan.subtasks)

    def test_parse_documentation_request(self):
        """测试文档请求"""
        parser = TaskParser()
        plan = parser.parse("编写 API 文档")

        assert any(
            t.task_type == TaskType.DOCUMENTATION for t in plan.subtasks)

    def test_parse_code_review_request(self):
        """测试代码审查请求"""
        parser = TaskParser()
        plan = parser.parse("审查这段代码")

        assert any(t.task_type == TaskType.CODE_REVIEW for t in plan.subtasks)

    def test_generate_subtasks_from_template(self):
        """测试从模板生成子任务"""
        parser = TaskParser()
        template = TASK_TEMPLATES["cli_tool"]

        subtasks = parser._generate_subtasks_from_template(template, "测试请求")

        assert len(subtasks) == len(template["subtasks"])
        assert all(s.estimated_duration is not None for s in subtasks)

    def test_generate_subtasks_with_project_type(self):
        """测试带项目类型生成子任务"""
        parser = TaskParser()
        subtasks = parser._generate_subtasks(
            "创建项目", [TaskType.PROJECT_INIT], "web_api")

        assert any(t.task_type == TaskType.PROJECT_INIT for t in subtasks)

    def test_generate_subtasks_empty(self):
        """测试生成通用子任务"""
        parser = TaskParser()
        subtasks = parser._generate_subtasks("随机文本", [])

        assert len(subtasks) > 0


class TestEnums:
    """测试枚举类"""

    def test_task_type_values(self):
        """测试任务类型枚举值"""
        assert TaskType.CODE_GENERATION.value == "code_generation"
        assert TaskType.ENVIRONMENT_SETUP.value == "environment_setup"
        assert TaskType.TESTING.value == "testing"
        assert TaskType.UNKNOWN.value == "unknown"

    def test_task_priority_values(self):
        """测试优先级枚举值"""
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"
