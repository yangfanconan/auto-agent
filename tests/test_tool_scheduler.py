"""
工具调度器单元测试
测试任务提交、执行、状态监控等功能
"""

from adapters.base_tool import ToolStatus, ToolResult
from core.tool_scheduler import (
    ToolScheduler, Task, TaskPlan, TaskStatus, TaskPriority,
    get_scheduler, run_scheduler_loop
)
import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTask:
    """测试任务定义"""

    def test_task_creation(self):
        """测试任务创建"""
        task = Task(
            id="task_001",
            name="测试任务",
            description="这是一个测试任务",
            tool_name="opencode",
            input_text="用 Python 写一个 hello world"
        )

        assert task.id == "task_001"
        assert task.name == "测试任务"
        assert task.tool_name == "opencode"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.NORMAL

    def test_task_to_dict(self):
        """测试任务转字典"""
        task = Task(
            id="task_002",
            name="测试任务 2",
            description="测试",
            tool_name="qwen",
            input_text="测试输入",
            priority=TaskPriority.HIGH,
            meta={"key": "value"}
        )

        data = task.to_dict()

        assert data["id"] == "task_002"
        assert data["name"] == "测试任务 2"
        assert data["priority"] == 2  # HIGH = 2
        assert data["meta"]["key"] == "value"
        assert data["status"] == "pending"


class TestTaskPlan:
    """测试任务计划"""

    def test_plan_creation(self):
        """测试任务计划创建"""
        plan = TaskPlan(
            id="plan_001",
            name="测试计划",
            description="这是一个测试计划"
        )

        assert plan.id == "plan_001"
        assert plan.status == TaskStatus.PENDING
        assert plan.progress == 0.0

    def test_plan_progress_calculation(self):
        """测试计划进度计算"""
        plan = TaskPlan(
            id="plan_002",
            name="测试计划 2",
            description="测试"
        )

        # 添加 4 个任务，2 个完成，1 个失败，1 个等待
        plan.tasks = [
            Task(
                id="t1",
                name="T1",
                description="D1",
                tool_name="opencode",
                input_text="",
                status=TaskStatus.COMPLETED),
            Task(
                id="t2",
                name="T2",
                description="D2",
                tool_name="opencode",
                input_text="",
                status=TaskStatus.COMPLETED),
            Task(
                id="t3",
                name="T3",
                description="D3",
                tool_name="opencode",
                input_text="",
                status=TaskStatus.FAILED),
            Task(
                id="t4",
                name="T4",
                description="D4",
                tool_name="opencode",
                input_text="",
                status=TaskStatus.PENDING),
        ]

        # 进度应该是 50% (2/4 完成)
        assert plan.progress == 50.0

    def test_plan_to_dict(self):
        """测试计划转字典"""
        plan = TaskPlan(
            id="plan_003",
            name="测试计划 3",
            description="测试"
        )
        plan.tasks = [
            Task(
                id="t1",
                name="T1",
                description="D1",
                tool_name="opencode",
                input_text="")
        ]

        data = plan.to_dict()

        assert data["id"] == "plan_003"
        assert len(data["tasks"]) == 1
        assert "progress" in data


class TestToolScheduler:
    """测试工具调度器"""

    def setup_method(self):
        """每个测试前的设置"""
        self.scheduler = ToolScheduler()

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        assert self.scheduler._tasks == {}
        assert self.scheduler._plans == {}
        assert self.scheduler._current_task is None

    def test_get_stats_empty(self):
        """测试空状态统计"""
        stats = self.scheduler.get_stats()

        assert stats["total_tasks"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["pending"] == 0

    @pytest.mark.asyncio
    async def test_submit_task(self):
        """测试提交任务"""
        task_id = await self.scheduler.submit_task(
            name="测试任务",
            description="这是一个测试任务",
            tool_name="opencode",
            input_text="用 Python 写一个快速排序"
        )

        assert task_id.startswith("task_")

        task = self.scheduler.get_task(task_id)
        assert task is not None
        assert task.name == "测试任务"
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_submit_plan(self):
        """测试提交任务计划"""
        plan_id = await self.scheduler.submit_plan(
            name="测试计划",
            description="包含多个子任务的测试计划",
            subtasks=[
                {"name": "子任务 1", "description": "D1",
                    "tool": "qwen", "input": "输入 1"},
                {"name": "子任务 2", "description": "D2",
                    "tool": "opencode", "input": "输入 2"},
            ]
        )

        assert plan_id.startswith("plan_")

        plan = self.scheduler.get_plan(plan_id)
        assert plan is not None
        assert len(plan.tasks) == 2

    @pytest.mark.asyncio
    async def test_task_priority(self):
        """测试任务优先级"""
        # 提交不同优先级的任务
        await self.scheduler.submit_task(
            name="低优先级任务",
            description="L",
            tool_name="opencode",
            input_text="",
            priority=TaskPriority.LOW
        )

        await self.scheduler.submit_task(
            name="高优先级任务",
            description="H",
            tool_name="opencode",
            input_text="",
            priority=TaskPriority.HIGH
        )

        await self.scheduler.submit_task(
            name="普通优先级任务",
            description="N",
            tool_name="opencode",
            input_text="",
            priority=TaskPriority.NORMAL
        )

        # 高优先级任务应该先执行
        task_id = await self.scheduler.execute_next()
        task = self.scheduler.get_task(task_id)
        assert task.name == "高优先级任务"

    def test_list_tasks(self):
        """测试列出任务"""
        # 任务列表应该为空或包含之前的任务
        tasks = self.scheduler.list_tasks()
        assert isinstance(tasks, list)

    def test_list_plans(self):
        """测试列出任务计划"""
        plans = self.scheduler.list_plans()
        assert isinstance(plans, list)

    def test_get_tool_status(self):
        """测试获取工具状态"""
        status = self.scheduler.get_tool_status()
        assert isinstance(status, dict)


class TestTaskStatus:
    """测试任务状态"""

    def test_task_status_values(self):
        """测试任务状态值"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"
        assert TaskStatus.WAITING_USER.value == "waiting_user"


class TestTaskPriority:
    """测试任务优先级"""

    def test_priority_values(self):
        """测试优先级值"""
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.CRITICAL.value == 3


class TestSchedulerCallbacks:
    """测试调度器回调"""

    def setup_method(self):
        """每个测试前的设置"""
        self.scheduler = ToolScheduler()
        self.completed_tasks = []
        self.failed_tasks = []

    def test_set_callbacks(self):
        """测试设置回调"""
        def on_complete(task):
            self.completed_tasks.append(task.id)

        def on_failed(task, decision):
            self.failed_tasks.append(task.id)

        self.scheduler.set_task_callbacks(
            on_complete=on_complete,
            on_failed=on_failed
        )

        assert self.scheduler._on_task_complete == on_complete
        assert self.scheduler._on_task_failed == on_failed


@pytest.mark.asyncio
class TestAsyncScheduler:
    """测试异步调度器"""

    def setup_method(self):
        """每个测试前的设置"""
        self.scheduler = ToolScheduler()

    async def test_execute_next_empty_queue(self):
        """测试空队列执行"""
        result = await self.scheduler.execute_next()
        # 空队列应该返回 None 或超时
        assert result is None

    async def test_monitoring_start_stop(self):
        """测试监控启动停止"""
        await self.scheduler.start_monitoring()
        assert self.scheduler._monitoring is True

        await asyncio.sleep(0.5)  # 运行一小段时间

        await self.scheduler.stop_monitoring()
        assert self.scheduler._monitoring is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
