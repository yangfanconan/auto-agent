"""
任务跟踪器
实时跟踪任务进度、记录卡点、生成简报
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict

try:
    from ..utils import get_logger
except ImportError:
    from utils import get_logger

try:
    from .task_parser import TaskPlan, SubTask, TaskType
except ImportError:
    from task_parser import TaskPlan, SubTask, TaskType


@dataclass
class TaskEvent:
    """任务事件"""
    timestamp: str
    event_type: str  # started, completed, failed, progress, log
    task_id: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "message": self.message,
            "details": self.details
        }


@dataclass
class TaskProgress:
    """任务进度"""
    task_id: str
    task_name: str
    status: str
    progress: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)


class TaskTracker:
    """任务跟踪器"""
    
    def __init__(self, storage_dir: str = "logs"):
        self.logger = get_logger()
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存中的任务状态
        self._plans: Dict[str, TaskPlan] = {}
        self._events: Dict[str, List[TaskEvent]] = {}
        self._current_task_id: Optional[str] = None
    
    def register_plan(self, plan: TaskPlan):
        """注册任务计划"""
        self._plans[plan.id] = plan
        self._events[plan.id] = []
        self.logger.info(f"注册任务计划：{plan.id}")
        
        # 记录事件
        self._add_event(plan.id, TaskEvent(
            timestamp=datetime.now().isoformat(),
            event_type="registered",
            task_id=plan.id,
            message=f"任务计划已注册：{plan.title}",
            details={"subtasks_count": len(plan.subtasks)}
        ))
    
    def start_task(self, task_id: str):
        """开始执行任务"""
        self._current_task_id = task_id
        
        if task_id in self._plans:
            plan = self._plans[task_id]
            plan.status = "in_progress"
            plan.updated_at = datetime.now().isoformat()
            
            self._add_event(task_id, TaskEvent(
                timestamp=datetime.now().isoformat(),
                event_type="started",
                task_id=task_id,
                message=f"任务开始执行：{plan.title}"
            ))
            
            self.logger.info(f"任务开始：{task_id}")
    
    def start_subtask(self, plan_id: str, subtask_id: str):
        """开始执行子任务"""
        if plan_id not in self._plans:
            self.logger.warning(f"任务计划不存在：{plan_id}")
            return
        
        plan = self._plans[plan_id]
        subtask = self._get_subtask(plan, subtask_id)
        
        if subtask:
            subtask.status = "in_progress"
            subtask.progress = 0.0
            subtask_start = datetime.now()
            subtask.metadata["start_time"] = subtask_start.isoformat()
            
            self._add_event(plan_id, TaskEvent(
                timestamp=datetime.now().isoformat(),
                event_type="subtask_started",
                task_id=subtask_id,
                message=f"子任务开始：{subtask.name}"
            ))
            
            self.logger.info(f"子任务开始：{subtask_id} - {subtask.name}")
    
    def update_subtask_progress(self, plan_id: str, subtask_id: str, progress: float, log: Optional[str] = None):
        """更新子任务进度"""
        if plan_id not in self._plans:
            return
        
        subtask = self._get_subtask(self._plans[plan_id], subtask_id)
        if subtask:
            subtask.progress = min(100.0, max(0.0, progress))
            if log:
                subtask.metadata["last_log"] = log
                self._add_event(plan_id, TaskEvent(
                    timestamp=datetime.now().isoformat(),
                    event_type="progress",
                    task_id=subtask_id,
                    message=log,
                    details={"progress": progress}
                ))
    
    def complete_subtask(self, plan_id: str, subtask_id: str, result: Optional[str] = None):
        """完成子任务"""
        if plan_id not in self._plans:
            return
        
        plan = self._plans[plan_id]
        subtask = self._get_subtask(plan, subtask_id)
        
        if subtask:
            subtask.status = "completed"
            subtask.progress = 100.0
            subtask.result = result
            subtask.completed_at = datetime.now().isoformat()
            
            # 计算实际耗时
            if "start_time" in subtask.metadata:
                start = datetime.fromisoformat(subtask.metadata["start_time"])
                end = datetime.fromisoformat(subtask.completed_at)
                subtask.actual_duration = (end - start).total_seconds()
            
            self._add_event(plan_id, TaskEvent(
                timestamp=datetime.now().isoformat(),
                event_type="subtask_completed",
                task_id=subtask_id,
                message=f"子任务完成：{subtask.name}",
                details={"result": result}
            ))
            
            self.logger.info(f"子任务完成：{subtask_id}")
            
            # 更新计划进度
            self._update_plan_progress(plan)
    
    def fail_subtask(self, plan_id: str, subtask_id: str, error: str):
        """子任务失败"""
        if plan_id not in self._plans:
            return
        
        subtask = self._get_subtask(self._plans[plan_id], subtask_id)
        
        if subtask:
            subtask.status = "failed"
            subtask.error = error
            subtask.progress = 0.0
            
            self._add_event(plan_id, TaskEvent(
                timestamp=datetime.now().isoformat(),
                event_type="subtask_failed",
                task_id=subtask_id,
                message=f"子任务失败：{subtask.name}",
                details={"error": error}
            ))
            
            self.logger.error(f"子任务失败：{subtask_id} - {error}")
            
            # 更新计划进度
            self._update_plan_progress(self._plans[plan_id])
    
    def complete_plan(self, plan_id: str):
        """完成任务计划"""
        if plan_id not in self._plans:
            return
        
        plan = self._plans[plan_id]
        plan.status = "completed"
        plan.updated_at = datetime.now().isoformat()
        
        self._add_event(plan_id, TaskEvent(
            timestamp=datetime.now().isoformat(),
            event_type="completed",
            task_id=plan_id,
            message=f"任务计划完成：{plan.title}"
        ))
        
        self.logger.info(f"任务计划完成：{plan_id}")
        self._save_plan(plan_id)
    
    def fail_plan(self, plan_id: str, error: str):
        """任务计划失败"""
        if plan_id not in self._plans:
            return
        
        plan = self._plans[plan_id]
        plan.status = "failed"
        plan.updated_at = datetime.now().isoformat()
        plan.metadata["failure_reason"] = error
        
        self._add_event(plan_id, TaskEvent(
            timestamp=datetime.now().isoformat(),
            event_type="failed",
            task_id=plan_id,
            message=f"任务计划失败：{plan.title}",
            details={"error": error}
        ))
        
        self.logger.error(f"任务计划失败：{plan_id} - {error}")
        self._save_plan(plan_id)
    
    def _get_subtask(self, plan: TaskPlan, subtask_id: str) -> Optional[SubTask]:
        """获取子任务"""
        for subtask in plan.subtasks:
            if subtask.id == subtask_id:
                return subtask
        return None
    
    def _update_plan_progress(self, plan: TaskPlan):
        """更新任务计划进度"""
        plan.updated_at = datetime.now().isoformat()
    
    def _add_event(self, plan_id: str, event: TaskEvent):
        """添加事件"""
        if plan_id in self._events:
            self._events[plan_id].append(event)
    
    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """获取任务计划"""
        return self._plans.get(plan_id)
    
    def get_events(self, plan_id: str) -> List[TaskEvent]:
        """获取事件列表"""
        return self._events.get(plan_id, [])
    
    def get_progress_report(self, plan_id: str) -> Dict:
        """获取进度报告"""
        if plan_id not in self._plans:
            return {"error": "任务计划不存在"}
        
        plan = self._plans[plan_id]
        
        return {
            "plan_id": plan.id,
            "title": plan.title,
            "status": plan.status,
            "overall_progress": plan.get_progress(),
            "completed_count": plan.get_completed_count(),
            "failed_count": plan.get_failed_count(),
            "total_subtasks": len(plan.subtasks),
            "subtasks": [t.to_dict() for t in plan.subtasks],
            "recent_events": [e.to_dict() for e in self._events.get(plan_id, [])[-10:]]
        }
    
    def generate_briefing(self, plan_id: str) -> str:
        """生成任务简报"""
        if plan_id not in self._plans:
            return "任务计划不存在"
        
        plan = self._plans[plan_id]
        report = self.get_progress_report(plan_id)
        
        lines = [
            f"## 任务简报：{plan.title}",
            f"",
            f"**状态**: {plan.status}",
            f"**进度**: {report['overall_progress']:.1f}%",
            f"**子任务**: {report['completed_count']}/{report['total_subtasks']} 完成",
            f"",
            "### 子任务状态",
        ]
        
        for subtask in plan.subtasks:
            status_icon = {"completed": "✅", "in_progress": "🔄", "failed": "❌", "pending": "⏳"}.get(subtask.status, "⏳")
            lines.append(f"- {status_icon} {subtask.name}: {subtask.status} ({subtask.progress:.0f}%)")
        
        return "\n".join(lines)
    
    def _save_plan(self, plan_id: str):
        """保存任务计划到文件"""
        plan = self._plans.get(plan_id)
        if not plan:
            return
        
        # 保存计划
        plan_file = self.storage_dir / f"plan_{plan_id}.json"
        with open(plan_file, 'w', encoding='utf-8') as f:
            json.dump(plan.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 保存事件
        events_file = self.storage_dir / f"events_{plan_id}.json"
        events = self._events.get(plan_id, [])
        with open(events_file, 'w', encoding='utf-8') as f:
            json.dump([e.to_dict() for e in events], f, ensure_ascii=False, indent=2)
        
        self.logger.debug(f"任务计划已保存：{plan_file}")
    
    def load_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """从文件加载任务计划"""
        plan_file = self.storage_dir / f"plan_{plan_id}.json"
        if not plan_file.exists():
            return None
        
        with open(plan_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建任务计划
        plan = TaskPlan(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            original_request=data["original_request"],
            status=data["status"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {})
        )
        
        # 重建子任务
        for subtask_data in data.get("subtasks", []):
            subtask = SubTask(
                id=subtask_data["id"],
                name=subtask_data["name"],
                description=subtask_data["description"],
                task_type=TaskType(subtask_data["task_type"]),
                priority=subtask_data.get("priority", "medium"),
                dependencies=subtask_data.get("dependencies", []),
                status=subtask_data.get("status", "pending"),
                result=subtask_data.get("result"),
                error=subtask_data.get("error"),
                progress=subtask_data.get("progress", 0.0),
                estimated_duration=subtask_data.get("estimated_duration"),
                actual_duration=subtask_data.get("actual_duration"),
                metadata=subtask_data.get("metadata", {})
            )
            plan.subtasks.append(subtask)
        
        self._plans[plan_id] = plan
        return plan
