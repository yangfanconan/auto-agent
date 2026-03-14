"""
测试核心功能包的导出
"""

import pytest
from core import (
    TaskParser,
    TaskPlan,
    SubTask,
    TaskType,
    TaskPriority,
    TaskTracker,
    TaskEvent,
    TaskProgress,
    TaskScheduler,
    AutoAgent,
)


class TestCoreImports:
    """测试核心模块导入"""
    
    def test_import_task_parser_classes(self):
        """测试导入任务解析器类"""
        assert TaskParser is not None
        assert TaskPlan is not None
        assert SubTask is not None
        assert TaskType is not None
        assert TaskPriority is not None
    
    def test_import_task_tracker_classes(self):
        """测试导入任务跟踪器类"""
        assert TaskTracker is not None
        assert TaskEvent is not None
        assert TaskProgress is not None
    
    def test_import_scheduler_classes(self):
        """测试导入调度器类"""
        assert TaskScheduler is not None
        assert AutoAgent is not None
    
    def test_task_type_enum(self):
        """测试任务类型枚举"""
        assert hasattr(TaskType, 'CODE_GENERATION')
        assert hasattr(TaskType, 'ENVIRONMENT_SETUP')
        assert hasattr(TaskType, 'TESTING')
        assert hasattr(TaskType, 'GIT_OPERATION')
        assert hasattr(TaskType, 'DELIVERY')
        assert hasattr(TaskType, 'DOCUMENTATION')
        assert hasattr(TaskType, 'CODE_REVIEW')
        assert hasattr(TaskType, 'OPTIMIZATION')
        assert hasattr(TaskType, 'PROJECT_INIT')
        assert hasattr(TaskType, 'UNKNOWN')
    
    def test_task_priority_enum(self):
        """测试任务优先级枚举"""
        assert hasattr(TaskPriority, 'HIGH')
        assert hasattr(TaskPriority, 'MEDIUM')
        assert hasattr(TaskPriority, 'LOW')
    
    def test_create_task_parser(self):
        """测试创建任务解析器实例"""
        parser = TaskParser()
        assert parser is not None
        assert hasattr(parser, 'parse')
    
    def test_create_task_tracker(self):
        """测试创建任务跟踪器实例"""
        tracker = TaskTracker()
        assert tracker is not None
        assert hasattr(tracker, 'register_plan')
    
    def test_create_task_scheduler(self):
        """测试创建任务调度器实例"""
        tracker = TaskTracker()
        scheduler = TaskScheduler(tracker)
        assert scheduler is not None
        assert hasattr(scheduler, 'execute_plan')
    
    def test_create_auto_agent(self):
        """测试创建自动代理实例"""
        agent = AutoAgent()
        assert agent is not None
        assert hasattr(agent, 'execute')
    
    def test_create_task_plan(self):
        """测试创建任务计划实例"""
        plan = TaskPlan(
            id="test_001",
            title="测试",
            description="描述",
            original_request="请求"
        )
        assert plan is not None
        assert plan.id == "test_001"
    
    def test_create_subtask(self):
        """测试创建子任务实例"""
        subtask = SubTask(
            id="sub_001",
            name="任务",
            description="描述",
            task_type=TaskType.CODE_GENERATION
        )
        assert subtask is not None
        assert subtask.id == "sub_001"
    
    def test_create_task_event(self):
        """测试创建任务事件实例"""
        event = TaskEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="started",
            task_id="task_001",
            message="开始"
        )
        assert event is not None
        assert event.task_id == "task_001"
    
    def test_create_task_progress(self):
        """测试创建任务进度实例"""
        progress = TaskProgress(
            task_id="task_001",
            task_name="任务",
            status="in_progress",
            progress=50.0
        )
        assert progress is not None
        assert progress.task_id == "task_001"
    
    def test_integration(self):
        """测试集成使用"""
        parser = TaskParser()
        plan = parser.parse("写一个函数")
        
        assert plan is not None
        assert len(plan.subtasks) > 0
        
        tracker = TaskTracker()
        tracker.register_plan(plan)
        
        assert tracker.get_plan(plan.id) is not None
