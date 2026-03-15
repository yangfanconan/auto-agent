"""
TaskScheduler 单元测试
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.scheduler import TaskScheduler
from core.task_tracker import TaskTracker
from core.task_parser import TaskPlan, SubTask, TaskType


class TestTaskScheduler:
    """TaskScheduler 测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.tracker = TaskTracker()
        self.scheduler = TaskScheduler(self.tracker)

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        assert self.scheduler is not None
        assert self.scheduler.tracker is not None
        assert len(self.scheduler._handlers) == 0

    def test_register_handler(self):
        """测试注册处理器"""
        def dummy_handler(plan_id, subtask):
            return {"success": True}

        self.scheduler.register_handler(TaskType.CODE_GENERATION, dummy_handler)
        assert TaskType.CODE_GENERATION in self.scheduler._handlers

    def test_execute_plan_not_found(self):
        """测试执行不存在的计划"""
        result = self.scheduler.execute_plan(None)
        assert result is False


class TestTaskPlan:
    """TaskPlan 测试类"""

    def test_task_plan_creation(self):
        """测试任务计划创建"""
        plan = TaskPlan(
            name="测试计划",
            description="这是一个测试计划",
            goal="完成测试"
        )
        assert plan.name == "测试计划"
        assert plan.description == "这是一个测试计划"
        assert len(plan.subtasks) == 0

    def test_task_plan_add_subtask(self):
        """测试添加子任务"""
        plan = TaskPlan(name="测试计划")
        subtask = SubTask(
            name="子任务1",
            description="测试子任务",
            task_type=TaskType.CODE_GENERATION
        )
        plan.subtasks.append(subtask)
        assert len(plan.subtasks) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
