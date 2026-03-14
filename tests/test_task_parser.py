"""
测试任务解析器模块
"""

import pytest
from core.task_parser import TaskParser, TaskType, TaskPriority, PROJECT_TEMPLATES, TASK_TEMPLATES


class TestTaskParser:
    """任务解析器测试"""
    
    def test_parse_simple_request(self):
        """测试简单请求解析"""
        parser = TaskParser()
        plan = parser.parse("用 Python 写一个计算器")
        
        assert plan.id.startswith("task_")
        assert plan.title is not None
        assert len(plan.subtasks) >= 2
        assert any(t.task_type == TaskType.CODE_GENERATION for t in plan.subtasks)
    
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
        
        assert any(t.task_type == TaskType.GIT_OPERATION for t in plan.subtasks)
    
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
        assert any(t.task_type == TaskType.DOCUMENTATION for t in plan.subtasks)
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


class TestTaskPlan:
    """任务计划测试"""
    
    def test_plan_to_dict(self):
        """测试计划转字典"""
        parser = TaskParser()
        plan = parser.parse("测试任务")
        
        plan_dict = plan.to_dict()
        
        assert "id" in plan_dict
        assert "title" in plan_dict
        assert "subtasks" in plan_dict
    
    def test_plan_progress(self):
        """测试进度计算"""
        parser = TaskParser()
        plan = parser.parse("测试任务")
        
        # 初始进度应为 0
        assert plan.get_progress() == 0.0
        
        # 更新子任务进度
        for task in plan.subtasks:
            task.progress = 100.0
            task.status = "completed"
        
        # 完成后的进度应为 100
        assert plan.get_progress() == 100.0
    
    def test_completed_count(self):
        """测试完成计数"""
        parser = TaskParser()
        plan = parser.parse("测试任务")
        
        initial_count = plan.get_completed_count()
        assert initial_count == 0
        
        # 完成一个子任务
        if plan.subtasks:
            plan.subtasks[0].status = "completed"
            assert plan.get_completed_count() == 1
