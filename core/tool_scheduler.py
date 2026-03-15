"""
工具调度器模块
实现双工具（OpenCode + Qwen）的智能调度、状态监听、任务分发

支持：
- 工具状态实时监控
- 任务自动分发到合适工具
- 工具智能切换
- 并发任务管理
- 任务优先级调度
"""

import asyncio
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

try:
    from ..utils import get_logger, load_config
    from ..adapters.base_tool import (
        ToolStatus, ToolResult, BaseTool, 
        QwenTool, OpenCodeTool, get_tool_registry
    )
    from ..core.console_io import get_console_redirector
    from ..core.events import publish_event, EventType
    from ..core.decision_engine import (
        get_decision_engine, DecisionContext, DecisionResult, DecisionType, RiskLevel
    )
except ImportError:
    from utils import get_logger, load_config
    from adapters.base_tool import (
        ToolStatus, ToolResult, BaseTool,
        QwenTool, OpenCodeTool, get_tool_registry
    )
    from core.console_io import get_console_redirector
    from core.events import publish_event, EventType
    from core.decision_engine import (
        get_decision_engine, DecisionContext, DecisionResult, DecisionType, RiskLevel
    )


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"           # 等待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消
    WAITING_USER = "waiting_user" # 等待用户确认


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    description: str
    tool_name: str
    input_text: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[ToolResult] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tool_name": self.tool_name,
            "input_text": self.input_text,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result.to_dict() if self.result else None,
            "error": self.error,
            "retry_count": self.retry_count,
            "meta": self.meta,
        }


@dataclass
class TaskPlan:
    """任务计划（由多个子任务组成）"""
    id: str
    name: str
    description: str
    tasks: List[Task] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_at: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        """计算进度百分比"""
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return (completed / len(self.tasks)) * 100

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tasks": [t.to_dict() for t in self.tasks],
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "meta": self.meta,
        }


class ToolScheduler:
    """工具调度器"""

    def __init__(self, config: Optional[Dict] = None):
        self.logger = get_logger()
        self.config = config or {}
        self.console_io = get_console_redirector()

        # 工具注册表
        self.registry = get_tool_registry()

        # 决策引擎
        self.decision_engine = get_decision_engine(config)

        # 任务队列（按优先级排序）
        self._task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

        # 任务管理
        self._tasks: Dict[str, Task] = {}
        self._plans: Dict[str, TaskPlan] = {}
        self._current_task: Optional[Task] = None

        # 状态监控
        self._tool_status: Dict[str, ToolStatus] = {}
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

        # 回调
        self._on_task_complete: Optional[Callable] = None
        self._on_task_failed: Optional[Callable] = None
        self._on_user_confirm: Optional[Callable] = None

        # 锁
        self._lock = asyncio.Lock()

        self.logger.info("工具调度器已初始化")

    def set_task_callbacks(
        self,
        on_complete: Optional[Callable] = None,
        on_failed: Optional[Callable] = None,
        on_user_confirm: Optional[Callable] = None
    ):
        """设置任务回调"""
        self._on_task_complete = on_complete
        self._on_task_failed = on_failed
        self._on_user_confirm = on_user_confirm

    async def start_monitoring(self):
        """启动状态监控"""
        if self._monitoring:
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.logger.info("状态监控已启动")

    async def stop_monitoring(self):
        """停止状态监控"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("状态监控已停止")

    async def _monitor_loop(self):
        """状态监控循环"""
        while self._monitoring:
            try:
                # 检查工具状态
                for tool_name in ["qwen", "opencode"]:
                    tool = self.registry.get(tool_name)
                    if tool:
                        status = tool.status
                        if status != self._tool_status.get(tool_name):
                            self._tool_status[tool_name] = status
                            self.logger.debug(f"工具状态更新：{tool_name} = {status.value}")
                            
                            # 发布事件
                            publish_event(
                                event_type="tool.status_changed",
                                payload={
                                    "tool_name": tool_name,
                                    "status": status.value,
                                },
                                source="scheduler"
                            )

                # 检查是否需要处理等待中的任务
                await self._process_waiting_tasks()

                await asyncio.sleep(0.5)  # 500ms 检查一次

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控循环异常：{e}")

    async def _process_waiting_tasks(self):
        """处理等待中的任务"""
        for task_id, task in list(self._tasks.items()):
            if task.status == TaskStatus.WAITING_USER:
                # 检查用户是否已确认
                if task.meta.get("user_confirmed"):
                    self.logger.info(f"任务 {task_id} 已确认，继续执行")
                    task.status = TaskStatus.RUNNING
                    asyncio.create_task(self._execute_task(task))

    async def submit_task(
        self,
        name: str,
        description: str,
        tool_name: str,
        input_text: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        meta: Optional[Dict] = None
    ) -> str:
        """
        提交任务

        流程：
        1. 创建任务
        2. 加入任务队列
        3. 发布事件
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        task = Task(
            id=task_id,
            name=name,
            description=description,
            tool_name=tool_name,
            input_text=input_text,
            priority=priority,
            meta=meta or {},
        )

        async with self._lock:
            self._tasks[task_id] = task
            await self._task_queue.put((-priority.value, task_id))

        self.logger.info(f"任务已提交：{task_id} ({name})")

        # 发布事件
        publish_event(
            event_type="task.submitted",
            payload=task.to_dict(),
            source="scheduler"
        )

        # 发送控制台消息
        self.console_io.send_status(
            f"📋 任务已提交：{name}",
            {"task_id": task_id, "tool": tool_name}
        )

        return task_id

    async def submit_plan(
        self,
        name: str,
        description: str,
        subtasks: List[Dict],
        meta: Optional[Dict] = None
    ) -> str:
        """
        提交任务计划（批量任务）

        Args:
            name: 计划名称
            description: 计划描述
            subtasks: 子任务列表 [{"name", "description", "tool", "input", "priority"}]
            meta: 元数据

        Returns:
            str: 计划 ID
        """
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        tasks = []
        for i, st in enumerate(subtasks):
            task = Task(
                id=f"{plan_id}_step{i+1}",
                name=st.get("name", f"Step {i+1}"),
                description=st.get("description", ""),
                tool_name=st.get("tool", "opencode"),
                input_text=st.get("input", ""),
                priority=TaskPriority(st.get("priority", TaskPriority.NORMAL.value)),
                meta={"plan_id": plan_id, "step": i + 1},
            )
            tasks.append(task)

        plan = TaskPlan(
            id=plan_id,
            name=name,
            description=description,
            tasks=tasks,
            meta=meta or {},
        )

        async with self._lock:
            self._plans[plan_id] = plan

            # 将所有子任务加入队列
            for task in tasks:
                self._tasks[task.id] = task
                await self._task_queue.put((-task.priority.value, task.id))

        self.logger.info(f"任务计划已提交：{plan_id} ({name}), 共 {len(tasks)} 个子任务")

        # 发布事件
        publish_event(
            event_type="plan.submitted",
            payload=plan.to_dict(),
            source="scheduler"
        )

        # 发送控制台消息
        self.console_io.send_status(
            f"📋 任务计划已提交：{name} ({len(tasks)} 个子任务)",
            {"plan_id": plan_id}
        )

        return plan_id

    async def execute_next(self) -> Optional[str]:
        """
        执行下一个任务

        Returns:
            str: 任务 ID 或 None
        """
        try:
            # 从队列获取任务
            priority, task_id = await asyncio.wait_for(
                self._task_queue.get(),
                timeout=1.0
            )

            task = self._tasks.get(task_id)
            if not task:
                self.logger.warning(f"任务不存在：{task_id}")
                return None

            # 检查任务状态
            if task.status != TaskStatus.PENDING:
                self.logger.debug(f"任务状态异常，跳过：{task_id} ({task.status.value})")
                return task_id

            # 执行任务
            asyncio.create_task(self._execute_task(task))

            return task_id

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.logger.error(f"执行任务失败：{e}")
            return None

    async def _execute_task(self, task: Task):
        """执行单个任务"""
        self.logger.info(f"开始执行任务：{task.id} ({task.name})")

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().timestamp()
        self._current_task = task

        # 发布事件
        publish_event(
            event_type="task.started",
            payload=task.to_dict(),
            source="scheduler"
        )

        # 发送控制台消息
        self.console_io.send_status(
            f"🚀 任务执行中：{task.name}",
            {"task_id": task.id, "tool": task.tool_name}
        )

        try:
            # 获取工具
            tool = self.registry.get(task.tool_name)
            if not tool:
                raise RuntimeError(f"工具不存在：{task.tool_name}")

            # 执行工具
            result = await tool.run_with_retry(
                task.input_text,
                max_retries=task.max_retries,
                **task.meta.get("tool_kwargs", {})
            )

            task.result = result
            task.completed_at = datetime.now().timestamp()

            if result.success:
                task.status = TaskStatus.COMPLETED
                self.logger.info(f"任务完成：{task.id}")

                # 发布事件
                publish_event(
                    event_type="task.completed",
                    payload=task.to_dict(),
                    source="scheduler"
                )

                # 回调
                if self._on_task_complete:
                    self._on_task_complete(task)

            else:
                # 任务失败，请求决策
                self.logger.warning(f"任务失败：{task.id}, 错误：{result.error}")
                await self._handle_task_failure(task, result.error)

        except Exception as e:
            self.logger.error(f"任务执行异常：{task.id} - {e}")
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().timestamp()

            await self._handle_task_failure(task, str(e))

        finally:
            self._current_task = None

    async def _handle_task_failure(self, task: Task, error: str):
        """处理任务失败"""
        # 构建决策上下文
        context = DecisionContext(
            tool_name=task.tool_name,
            tool_status=ToolStatus.ERROR,
            error_message=error,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            task_id=task.id,
            task_description=task.description,
        )

        # 请求决策
        decision = await self.decision_engine.make_decision(context)

        self.logger.info(f"决策结果：{decision.decision_type.value} - {decision.reason}")

        # 执行决策
        if decision.decision_type == DecisionType.AUTO_RETRY:
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                await self._task_queue.put((-task.priority.value, task.id))
                self.logger.info(f"任务已重试：{task.id} ({task.retry_count}/{task.max_retries})")
            else:
                task.status = TaskStatus.FAILED
                task.error = error

        elif decision.decision_type == DecisionType.WAIT_USER:
            task.status = TaskStatus.WAITING_USER
            task.meta["user_confirmed"] = False
            task.meta["decision"] = decision.to_dict()

            # 推送确认请求到前端
            if self._on_user_confirm:
                self._on_user_confirm(task, decision)

            self.logger.info(f"任务等待用户确认：{task.id}")

        elif decision.decision_type == DecisionType.SWITCH_TOOL:
            # 切换到备用工具
            new_tool = "qwen" if task.tool_name == "opencode" else "opencode"
            self.logger.info(f"切换工具：{task.tool_name} -> {new_tool}")
            task.tool_name = new_tool
            task.status = TaskStatus.PENDING
            await self._task_queue.put((-task.priority.value, task.id))

        else:
            # 其他决策，标记为失败
            task.status = TaskStatus.FAILED
            task.error = error
            task.meta["decision"] = decision.to_dict()

        # 更新任务
        self._tasks[task.id] = task

        # 发布事件
        publish_event(
            event_type="task.failed",
            payload={
                "task": task.to_dict(),
                "decision": decision.to_dict(),
            },
            source="scheduler"
        )

        # 回调
        if self._on_task_failed:
            self._on_task_failed(task, decision)

    def confirm_task(self, task_id: str, confirmed: bool):
        """用户确认任务"""
        task = self._tasks.get(task_id)
        if not task:
            self.logger.warning(f"任务不存在：{task_id}")
            return

        if confirmed:
            task.meta["user_confirmed"] = True
            task.status = TaskStatus.RUNNING
            asyncio.create_task(self._execute_task(task))
            self.logger.info(f"用户确认任务：{task_id}")
        else:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().timestamp()
            self.logger.info(f"用户取消任务：{task_id}")

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """获取任务计划"""
        return self._plans.get(plan_id)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        return task.to_dict() if task else None

    def get_plan_status(self, plan_id: str) -> Optional[Dict]:
        """获取任务计划状态"""
        plan = self._plans.get(plan_id)
        return plan.to_dict() if plan else None

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict]:
        """列出任务"""
        tasks = self._tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [t.to_dict() for t in tasks]

    def list_plans(self) -> List[Dict]:
        """列出任务计划"""
        return [p.to_dict() for p in self._plans.values()]

    def get_tool_status(self) -> Dict[str, str]:
        """获取所有工具状态"""
        return {name: status.value for name, status in self._tool_status.items()}

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_tasks = len(self._tasks)
        completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
        pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
        waiting = sum(1 for t in self._tasks.values() if t.status == TaskStatus.WAITING_USER)

        return {
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "waiting_user": waiting,
            "total_plans": len(self._plans),
            "tool_status": self.get_tool_status(),
            "queue_size": self._task_queue.qsize(),
        }


# 全局实例
_global_scheduler: Optional[ToolScheduler] = None


def get_scheduler(config: Optional[Dict] = None) -> ToolScheduler:
    """获取全局工具调度器"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = ToolScheduler(config)
    return _global_scheduler


async def run_scheduler_loop(scheduler: ToolScheduler, interval: float = 0.1):
    """运行调度器循环"""
    await scheduler.start_monitoring()

    try:
        while True:
            await scheduler.execute_next()
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
    finally:
        await scheduler.stop_monitoring()
