"""
任务调度器和 AutoAgent 单元测试
"""

import pytest
from unittest.mock import patch, MagicMock

from core.scheduler import TaskScheduler, AutoAgent
from core.task_parser import TaskPlan, SubTask, TaskType, TaskPriority
from core.task_tracker import TaskTracker


class TestTaskScheduler:
    """测试 TaskScheduler 类"""
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    def test_scheduler_initialization(self, mock_tracker_class, mock_get_logger):
        """测试调度器初始化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        scheduler = TaskScheduler(mock_tracker)
        
        assert scheduler.logger == mock_logger
        assert scheduler.tracker == mock_tracker
        assert scheduler._handlers == {}
        assert scheduler._current_plan is None
    
    @patch('core.scheduler.get_logger')
    def test_register_handler(self, mock_get_logger):
        """测试注册任务处理器"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        
        def handler(plan_id, subtask):
            return "result"
        
        scheduler.register_handler(TaskType.CODE_GENERATION, handler)
        
        assert TaskType.CODE_GENERATION in scheduler._handlers
    
    @patch('core.scheduler.get_logger')
    def test_execute_plan_success(self, mock_get_logger, sample_task_plan):
        """测试执行任务计划成功"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        
        def handler(plan_id, subtask):
            return "success"
        
        for task_type in TaskType:
            scheduler.register_handler(task_type, handler)
        
        result = scheduler.execute_plan(sample_task_plan)
        
        assert result is True
        tracker.register_plan.assert_called_once()
        tracker.start_task.assert_called_once()
    
    @patch('core.scheduler.get_logger')
    def test_execute_plan_with_failing_handler(self, mock_get_logger):
        """测试处理器失败的情况"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        
        def failing_handler(plan_id, subtask):
            raise Exception("Handler failed")
        
        plan = TaskPlan(
            id="test_plan",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=[
                SubTask(
                    id="sub_001",
                    name="任务",
                    description="描述",
                    task_type=TaskType.CODE_GENERATION,
                    priority=TaskPriority.HIGH
                )
            ]
        )
        
        scheduler.register_handler(TaskType.CODE_GENERATION, failing_handler)
        result = scheduler.execute_plan(plan)
        
        assert result is False
    
    @patch('core.scheduler.get_logger')
    def test_execute_plan_no_handler(self, mock_get_logger):
        """测试没有处理器的情况"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        
        plan = TaskPlan(
            id="test_plan",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=[
                SubTask(
                    id="sub_001",
                    name="任务",
                    description="描述",
                    task_type=TaskType.CODE_GENERATION
                )
            ]
        )
        
        result = scheduler.execute_plan(plan)
        
        assert result is True
    
    @patch('core.scheduler.get_logger')
    def test_find_ready_tasks(self, mock_get_logger, sample_task_plan):
        """测试查找可执行的任务"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        
        completed = set()
        failed = set()
        
        ready = scheduler._find_ready_tasks(sample_task_plan, completed, failed)
        
        assert len(ready) > 0
        assert all(t.id not in completed and t.id not in failed for t in ready)
    
    @patch('core.scheduler.get_logger')
    def test_find_ready_tasks_with_dependencies(self, mock_get_logger):
        """测试有依赖关系的任务查找"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        
        plan = TaskPlan(
            id="test_plan",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=[
                SubTask(
                    id="sub_001",
                    name="任务1",
                    description="描述1",
                    task_type=TaskType.CODE_GENERATION
                ),
                SubTask(
                    id="sub_002",
                    name="任务2",
                    description="描述2",
                    task_type=TaskType.TESTING,
                    dependencies=["sub_001"]
                )
            ]
        )
        
        completed = set()
        failed = set()
        
        ready = scheduler._find_ready_tasks(plan, completed, failed)
        assert len(ready) == 1
        assert ready[0].id == "sub_001"
        
        completed.add("sub_001")
        ready = scheduler._find_ready_tasks(plan, completed, failed)
        assert len(ready) == 1
        assert ready[0].id == "sub_002"
    
    @patch('core.scheduler.get_logger')
    def test_find_ready_tasks_with_failed_dependency(self, mock_get_logger):
        """测试依赖任务失败的情况"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        
        plan = TaskPlan(
            id="test_plan",
            title="测试计划",
            description="描述",
            original_request="请求",
            subtasks=[
                SubTask(
                    id="sub_001",
                    name="任务1",
                    description="描述1",
                    task_type=TaskType.CODE_GENERATION
                ),
                SubTask(
                    id="sub_002",
                    name="任务2",
                    description="描述2",
                    task_type=TaskType.TESTING,
                    dependencies=["sub_001"]
                )
            ]
        )
        
        completed = set()
        failed = {"sub_001"}
        
        ready = scheduler._find_ready_tasks(plan, completed, failed)
        assert len(ready) == 0
    
    @patch('core.scheduler.get_logger')
    def test_get_status(self, mock_get_logger, sample_task_plan):
        """测试获取调度器状态"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        tracker = MagicMock()
        
        scheduler = TaskScheduler(tracker)
        scheduler._current_plan = sample_task_plan
        
        status = scheduler.get_status()
        
        assert status["current_plan"] == sample_task_plan.id
        assert "registered_handlers" in status


class TestAutoAgent:
    """测试 AutoAgent 类"""
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    def test_auto_agent_initialization(self, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试 AutoAgent 初始化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        agent = AutoAgent(workspace=temp_workspace)
        
        assert agent.workspace == temp_workspace
        assert agent.config == {}
        assert agent.tracker == mock_tracker
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    def test_auto_agent_with_config(self, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试带配置的 AutoAgent 初始化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        config = {"name": "test-agent", "version": "1.0.0"}
        agent = AutoAgent(workspace=temp_workspace, config=config)
        
        assert agent.config == config
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    def test_set_modules(self, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试设置功能模块"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        agent = AutoAgent(workspace=temp_workspace)
        
        env = MagicMock()
        code_gen = MagicMock()
        test_runner = MagicMock()
        git_mgr = MagicMock()
        delivery = MagicMock()
        
        agent.set_modules(
            environment=env,
            code_generator=code_gen,
            test_runner=test_runner,
            git_manager=git_mgr,
            delivery=delivery
        )
        
        assert agent._environment == env
        assert agent._code_generator == code_gen
        assert agent._test_runner == test_runner
        assert agent._git_manager == git_mgr
        assert agent._delivery == delivery
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    @patch('core.scheduler.TaskParser')
    def test_execute(self, mock_parser_class, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试执行用户请求"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        
        mock_plan = MagicMock()
        mock_plan.id = "test_plan"
        mock_parser.parse.return_value = mock_plan
        
        mock_tracker.get_progress_report.return_value = {
            "plan_id": "test_plan",
            "status": "completed"
        }
        
        agent = AutoAgent(workspace=temp_workspace)
        
        def success_handler(plan_id, subtask):
            return "success"
        
        for task_type in TaskType:
            agent.scheduler.register_handler(task_type, success_handler)
        
        result = agent.execute("写一个函数")
        
        assert "success" in result
        mock_parser.parse.assert_called_once()
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    def test_get_progress(self, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试获取任务进度"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        mock_tracker.get_progress_report.return_value = {"progress": 50.0}
        
        agent = AutoAgent(workspace=temp_workspace)
        progress = agent.get_progress("plan_001")
        
        assert progress["progress"] == 50.0
        mock_tracker.get_progress_report.assert_called_with("plan_001")
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    def test_get_briefing(self, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试获取任务简报"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        mock_tracker.generate_briefing.return_value = "任务简报内容"
        
        agent = AutoAgent(workspace=temp_workspace)
        briefing = agent.get_briefing("plan_001")
        
        assert briefing == "任务简报内容"
        mock_tracker.generate_briefing.assert_called_with("plan_001")
    
    @patch('core.scheduler.get_logger')
    @patch('core.scheduler.TaskTracker')
    def test_register_default_handlers(self, mock_tracker_class, mock_get_logger, temp_workspace):
        """测试注册默认处理器"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        agent = AutoAgent(workspace=temp_workspace)
        
        assert TaskType.ENVIRONMENT_SETUP in agent.scheduler._handlers
        assert TaskType.CODE_GENERATION in agent.scheduler._handlers
        assert TaskType.TESTING in agent.scheduler._handlers
        assert TaskType.GIT_OPERATION in agent.scheduler._handlers
        assert TaskType.DELIVERY in agent.scheduler._handlers
