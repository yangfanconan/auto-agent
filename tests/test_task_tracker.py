"""
任务跟踪器单元测试
"""

import json
import os
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.task_tracker import TaskTracker, TaskEvent, TaskProgress
from core.task_parser import TaskPlan, SubTask, TaskType, TaskPriority


class TestTaskEvent:
    """测试 TaskEvent 数据类"""
    
    def test_task_event_creation(self):
        """测试创建任务事件"""
        event = TaskEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="started",
            task_id="task_001",
            message="任务开始"
        )
        
        assert event.timestamp == "2024-01-01T00:00:00"
        assert event.event_type == "started"
        assert event.task_id == "task_001"
        assert event.message == "任务开始"
        assert event.details == {}
    
    def test_task_event_to_dict(self):
        """测试事件转换为字典"""
        event = TaskEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="completed",
            task_id="task_001",
            message="任务完成",
            details={"duration": 10.5}
        )
        
        result = event.to_dict()
        
        assert result["timestamp"] == "2024-01-01T00:00:00"
        assert result["event_type"] == "completed"
        assert result["task_id"] == "task_001"
        assert result["details"]["duration"] == 10.5


class TestTaskProgress:
    """测试 TaskProgress 数据类"""
    
    def test_task_progress_creation(self):
        """测试创建任务进度"""
        progress = TaskProgress(
            task_id="task_001",
            task_name="测试任务",
            status="in_progress",
            progress=50.0
        )
        
        assert progress.task_id == "task_001"
        assert progress.task_name == "测试任务"
        assert progress.status == "in_progress"
        assert progress.progress == 50.0
        assert progress.started_at is None
        assert progress.logs == []


class TestTaskTracker:
    """测试 TaskTracker 类"""
    
    @patch('core.task_tracker.get_logger')
    def test_tracker_initialization(self, mock_get_logger, temp_workspace):
        """测试跟踪器初始化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        
        assert tracker.logger == mock_logger
        assert Path(temp_workspace).exists()
        assert tracker._plans == {}
        assert tracker._events == {}
    
    @patch('core.task_tracker.get_logger')
    def test_register_plan(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试注册任务计划"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        assert sample_task_plan.id in tracker._plans
        assert sample_task_plan.id in tracker._events
        assert len(tracker._events[sample_task_plan.id]) == 1
    
    @patch('core.task_tracker.get_logger')
    def test_start_task(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试开始任务"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        tracker.start_task(sample_task_plan.id)
        
        assert tracker._current_task_id == sample_task_plan.id
        assert tracker._plans[sample_task_plan.id].status == "in_progress"
    
    @patch('core.task_tracker.get_logger')
    def test_start_subtask(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试开始子任务"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.status == "in_progress"
        assert subtask.progress == 0.0
    
    @patch('core.task_tracker.get_logger')
    def test_update_subtask_progress(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试更新子任务进度"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        tracker.update_subtask_progress(
            sample_task_plan.id, 
            subtask_id, 
            50.0, 
            "进度更新"
        )
        
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.progress == 50.0
        assert subtask.metadata.get("last_log") == "进度更新"
    
    @patch('core.task_tracker.get_logger')
    def test_update_subtask_progress_clamp(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试进度值范围限制"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        
        tracker.update_subtask_progress(sample_task_plan.id, subtask_id, 150.0)
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.progress == 100.0
        
        tracker.update_subtask_progress(sample_task_plan.id, subtask_id, -10.0)
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.progress == 0.0
    
    @patch('core.task_tracker.get_logger')
    def test_complete_subtask(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试完成子任务"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        tracker.complete_subtask(sample_task_plan.id, subtask_id, "完成结果")
        
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.status == "completed"
        assert subtask.progress == 100.0
        assert subtask.result == "完成结果"
    
    @patch('core.task_tracker.get_logger')
    def test_fail_subtask(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试子任务失败"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        tracker.fail_subtask(sample_task_plan.id, subtask_id, "错误信息")
        
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.status == "failed"
        assert subtask.error == "错误信息"
    
    @patch('core.task_tracker.get_logger')
    def test_complete_plan(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试完成任务计划"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        tracker.complete_plan(sample_task_plan.id)
        
        assert tracker._plans[sample_task_plan.id].status == "completed"
    
    @patch('core.task_tracker.get_logger')
    def test_fail_plan(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试任务计划失败"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        tracker.fail_plan(sample_task_plan.id, "计划失败原因")
        
        plan = tracker._plans[sample_task_plan.id]
        assert plan.status == "failed"
        assert plan.metadata.get("failure_reason") == "计划失败原因"
    
    @patch('core.task_tracker.get_logger')
    def test_get_plan(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试获取任务计划"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        plan = tracker.get_plan(sample_task_plan.id)
        assert plan == sample_task_plan
        
        none_plan = tracker.get_plan("non_existent_id")
        assert none_plan is None
    
    @patch('core.task_tracker.get_logger')
    def test_get_events(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试获取事件列表"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        tracker.start_task(sample_task_plan.id)
        
        events = tracker.get_events(sample_task_plan.id)
        assert len(events) >= 2
        
        empty_events = tracker.get_events("non_existent_id")
        assert empty_events == []
    
    @patch('core.task_tracker.get_logger')
    def test_get_progress_report(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试获取进度报告"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        report = tracker.get_progress_report(sample_task_plan.id)
        
        assert report["plan_id"] == sample_task_plan.id
        assert report["title"] == sample_task_plan.title
        assert "overall_progress" in report
        assert "completed_count" in report
        assert "total_subtasks" in report
    
    @patch('core.task_tracker.get_logger')
    def test_get_progress_report_non_existent(self, mock_get_logger, temp_workspace):
        """测试获取不存在计划的进度报告"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        report = tracker.get_progress_report("non_existent_id")
        
        assert "error" in report
    
    @patch('core.task_tracker.get_logger')
    def test_generate_briefing(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试生成任务简报"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        briefing = tracker.generate_briefing(sample_task_plan.id)
        
        assert sample_task_plan.title in briefing
        assert "状态" in briefing
        assert "进度" in briefing
    
    @patch('core.task_tracker.get_logger')
    def test_generate_briefing_non_existent(self, mock_get_logger, temp_workspace):
        """测试生成不存在计划的简报"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        briefing = tracker.generate_briefing("non_existent_id")
        
        assert briefing == "任务计划不存在"
    
    @patch('core.task_tracker.get_logger')
    def test_save_and_load_plan(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试保存和加载任务计划"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        tracker.complete_plan(sample_task_plan.id)
        
        plan_file = Path(temp_workspace) / f"plan_{sample_task_plan.id}.json"
        assert plan_file.exists()
        
        loaded_plan = tracker.load_plan(sample_task_plan.id)
        
        assert loaded_plan is not None
        assert loaded_plan.id == sample_task_plan.id
        assert loaded_plan.title == sample_task_plan.title
    
    @patch('core.task_tracker.get_logger')
    def test_load_non_existent_plan(self, mock_get_logger, temp_workspace):
        """测试加载不存在的计划"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        plan = tracker.load_plan("non_existent_id")
        
        assert plan is None
    
    @patch('core.task_tracker.get_logger')
    def test_get_subtask(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试获取子任务"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        
        subtask_id = sample_task_plan.subtasks[0].id
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        
        assert subtask is not None
        assert subtask.id == subtask_id
        
        none_subtask = tracker._get_subtask(sample_task_plan, "non_existent")
        assert none_subtask is None
    
    @patch('core.task_tracker.get_logger')
    def test_operations_on_non_existent_plan(self, mock_get_logger, temp_workspace):
        """测试对不存在计划的安全操作"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        
        tracker.start_subtask("non_existent", "subtask")
        tracker.update_subtask_progress("non_existent", "subtask", 50.0)
        tracker.complete_subtask("non_existent", "subtask", "result")
        tracker.fail_subtask("non_existent", "subtask", "error")
        tracker.complete_plan("non_existent")
        tracker.fail_plan("non_existent", "error")
        
        assert True
    
    @patch('core.task_tracker.get_logger')
    def test_update_plan_progress(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试更新计划进度"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        old_updated_at = sample_task_plan.updated_at
        tracker._update_plan_progress(sample_task_plan)
        
        assert sample_task_plan.updated_at is not None
        assert sample_task_plan.updated_at != old_updated_at
    
    @patch('core.task_tracker.get_logger')
    def test_subtask_actual_duration_calculation(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试子任务实际耗时计算"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        
        import time
        time.sleep(0.1)
        
        tracker.complete_subtask(sample_task_plan.id, subtask_id, "完成")
        
        subtask = tracker._get_subtask(sample_task_plan, subtask_id)
        assert subtask.actual_duration is not None
        assert subtask.actual_duration >= 0.1
    
    @patch('core.task_tracker.get_logger')
    def test_add_event_to_non_existent_plan(self, mock_get_logger, temp_workspace):
        """测试向不存在的计划添加事件"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        
        event = TaskEvent(
            timestamp="2024-01-01T00:00:00",
            event_type="test",
            task_id="test",
            message="测试"
        )
        
        tracker._add_event("non_existent", event)
        
        assert "non_existent" not in tracker._events
    
    @patch('core.task_tracker.get_logger')
    def test_load_plan_with_full_data(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试加载完整的计划数据"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        tracker.complete_subtask(sample_task_plan.id, subtask_id, "完成")
        tracker.complete_plan(sample_task_plan.id)
        
        new_tracker = TaskTracker(storage_dir=temp_workspace)
        loaded_plan = new_tracker.load_plan(sample_task_plan.id)
        
        assert loaded_plan is not None
        assert len(loaded_plan.subtasks) == len(sample_task_plan.subtasks)
        assert loaded_plan.subtasks[0].task_type == sample_task_plan.subtasks[0].task_type
    
    @patch('core.task_tracker.get_logger')
    def test_get_subtask_not_found(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试获取不存在的子任务"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        
        subtask = tracker._get_subtask(sample_task_plan, "non_existent_id")
        
        assert subtask is None
    
    @patch('core.task_tracker.get_logger')
    def test_progress_report_with_failed_subtasks(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试包含失败子任务的进度报告"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        subtask_id = sample_task_plan.subtasks[0].id
        tracker.start_subtask(sample_task_plan.id, subtask_id)
        tracker.fail_subtask(sample_task_plan.id, subtask_id, "测试失败")
        
        report = tracker.get_progress_report(sample_task_plan.id)
        
        assert report["failed_count"] == 1
    
    @patch('core.task_tracker.get_logger')
    def test_briefing_with_various_statuses(self, mock_get_logger, temp_workspace, sample_task_plan):
        """测试各种状态的任务简报"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.register_plan(sample_task_plan)
        
        sample_task_plan.subtasks[0].status = "completed"
        sample_task_plan.subtasks[0].progress = 100.0
        
        sample_task_plan.subtasks[1].status = "in_progress"
        sample_task_plan.subtasks[1].progress = 50.0
        
        sample_task_plan.subtasks[2].status = "failed"
        
        briefing = tracker.generate_briefing(sample_task_plan.id)
        
        assert "✅" in briefing
        assert "🔄" in briefing
        assert "❌" in briefing
    
    @patch('core.task_tracker.get_logger')
    def test_start_subtask_non_existent_plan(self, mock_get_logger, temp_workspace):
        """测试对不存在的计划开始子任务"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker.start_subtask("non_existent", "subtask")
        
        assert True
    
    @patch('core.task_tracker.get_logger')
    def test_save_plan_without_plan(self, mock_get_logger, temp_workspace):
        """测试保存不存在的计划"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        tracker = TaskTracker(storage_dir=temp_workspace)
        tracker._save_plan("non_existent")
        
        plan_file = Path(temp_workspace) / "plan_non_existent.json"
        assert not plan_file.exists()
