"""
任务调度器
协调各模块，按依赖关系调度执行任务
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any

try:
    from ..utils import get_logger, AutoAgentException
except ImportError:
    from utils import get_logger, AutoAgentException

try:
    from .task_parser import TaskPlan, SubTask, TaskType
    from .task_tracker import TaskTracker
except ImportError:
    from task_parser import TaskPlan, SubTask, TaskType
    from task_tracker import TaskTracker


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, tracker: TaskTracker):
        self.logger = get_logger()
        self.tracker = tracker
        
        # 任务处理器注册表
        self._handlers: Dict[TaskType, Callable] = {}
        
        # 当前执行的计划
        self._current_plan: Optional[TaskPlan] = None
    
    def register_handler(self, task_type: TaskType, handler: Callable):
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数，签名：handler(plan_id, subtask) -> result
        """
        self._handlers[task_type] = handler
        self.logger.debug(f"注册任务处理器：{task_type.value}")
    
    def execute_plan(self, plan: TaskPlan) -> bool:
        """
        执行任务计划
        
        Args:
            plan: 任务计划
        
        Returns:
            bool: 是否成功完成
        """
        self._current_plan = plan
        self.tracker.register_plan(plan)
        self.tracker.start_task(plan.id)
        
        self.logger.info(f"开始执行任务计划：{plan.id} - {plan.title}")
        
        try:
            # 按依赖关系执行子任务
            completed = set()
            failed = set()
            
            while len(completed) + len(failed) < len(plan.subtasks):
                # 查找可执行的子任务
                ready_tasks = self._find_ready_tasks(plan, completed, failed)
                
                if not ready_tasks:
                    # 没有可执行的任务，检查是否有循环依赖或失败
                    if failed:
                        self.logger.warning(f"任务执行受阻，已有 {len(failed)} 个任务失败")
                        # 继续尝试执行其他不依赖失败任务的任务
                        remaining = [t for t in plan.subtasks if t.id not in completed and t.id not in failed]
                        if not remaining:
                            break
                    else:
                        self.logger.error("无法找到可执行的任务，可能存在循环依赖")
                        break
                
                # 执行可执行的任务
                for subtask in ready_tasks:
                    success = self._execute_subtask(plan, subtask)
                    if success:
                        completed.add(subtask.id)
                    else:
                        failed.add(subtask.id)
                        
                        # 如果关键任务失败，可能影响后续任务
                        if subtask.priority.value == "high":
                            self.logger.warning(f"高优先级任务失败：{subtask.id}")
            
            # 检查整体完成情况
            all_completed = len(completed) == len(plan.subtasks)
            
            if all_completed:
                self.tracker.complete_plan(plan.id)
                self.logger.info(f"任务计划完成：{plan.id}")
                return True
            else:
                # 部分完成
                plan.status = "completed" if not failed else "failed"
                self.tracker.complete_plan(plan.id)
                self.logger.warning(f"任务计划部分完成：{len(completed)}/{len(plan.subtasks)}")
                return len(failed) == 0
                
        except Exception as e:
            self.logger.error(f"任务计划执行异常：{e}")
            self.tracker.fail_plan(plan.id, str(e))
            return False
    
    def _find_ready_tasks(
        self,
        plan: TaskPlan,
        completed: set,
        failed: set
    ) -> List[SubTask]:
        """查找可执行的子任务"""
        ready = []
        
        for subtask in plan.subtasks:
            if subtask.id in completed or subtask.id in failed:
                continue
            
            # 检查依赖是否满足
            deps_satisfied = all(
                dep in completed for dep in subtask.dependencies
            )
            
            # 检查依赖是否有失败的
            deps_failed = any(
                dep in failed for dep in subtask.dependencies
            )
            
            if deps_failed:
                # 依赖失败，跳过该任务
                self.logger.warning(f"任务 {subtask.id} 的依赖失败，跳过执行")
                failed.add(subtask.id)
                self.tracker.fail_subtask(plan.id, subtask.id, "依赖任务失败")
                continue
            
            if deps_satisfied:
                ready.append(subtask)
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        ready.sort(key=lambda t: priority_order.get(t.priority.value, 1))
        
        return ready
    
    def _execute_subtask(self, plan: TaskPlan, subtask: SubTask) -> bool:
        """执行子任务"""
        self.logger.info(f"执行子任务：{subtask.id} - {subtask.name}")
        
        self.tracker.start_subtask(plan.id, subtask.id)
        
        # 查找处理器
        handler = self._handlers.get(subtask.task_type)
        
        if not handler:
            # 尝试使用通用处理器
            handler = self._handlers.get(TaskType.UNKNOWN)
        
        if not handler:
            self.logger.warning(f"未找到任务处理器：{subtask.task_type.value}，跳过执行")
            self.tracker.complete_subtask(plan.id, subtask.id, "无可用处理器，跳过")
            return True
        
        try:
            # 执行处理器
            result = handler(plan.id, subtask)
            
            self.tracker.complete_subtask(plan.id, subtask.id, result)
            return True
            
        except Exception as e:
            self.logger.error(f"子任务执行失败：{subtask.id} - {e}")
            self.tracker.fail_subtask(plan.id, subtask.id, str(e))
            return False
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "current_plan": self._current_plan.id if self._current_plan else None,
            "registered_handlers": list(self._handlers.keys()),
            "plan_status": self._current_plan.status if self._current_plan else None
        }


class AutoAgent:
    """
    全自动工程化编程智能体主控制器
    整合所有模块，提供统一的执行入口
    """
    
    def __init__(self, workspace: str = ".", config: Optional[Dict] = None):
        self.logger = get_logger()
        self.workspace = workspace
        self.config = config or {}
        
        # 初始化核心组件
        self.tracker = TaskTracker()
        self.scheduler = TaskScheduler(self.tracker)
        
        # 模块（延迟初始化）
        self._environment = None
        self._code_generator = None
        self._test_runner = None
        self._git_manager = None
        self._delivery = None
        
        # 注册默认处理器
        self._register_default_handlers()
        
        self.logger.info(f"AutoAgent 初始化完成，工作空间：{workspace}")
    
    def _register_default_handlers(self):
        """注册默认任务处理器"""
        
        # 环境设置处理器
        def env_handler(plan_id: str, subtask: SubTask):
            if self._environment:
                return self._environment.setup(plan_id, subtask)
            return "环境模块未初始化"
        
        self.scheduler.register_handler(TaskType.ENVIRONMENT_SETUP, env_handler)
        
        # 代码生成处理器
        def code_handler(plan_id: str, subtask: SubTask):
            if self._code_generator:
                return self._code_generator.generate_task(plan_id, subtask)
            return "代码生成模块未初始化"

        self.scheduler.register_handler(TaskType.CODE_GENERATION, code_handler)
        
        # 测试处理器
        def test_handler(plan_id: str, subtask: SubTask):
            if self._test_runner:
                return self._test_runner.run(plan_id, subtask)
            return "测试模块未初始化"
        
        self.scheduler.register_handler(TaskType.TESTING, test_handler)
        
        # Git 处理器
        def git_handler(plan_id: str, subtask: SubTask):
            if self._git_manager:
                return self._git_manager.commit(plan_id, subtask)
            return "Git 模块未初始化"
        
        self.scheduler.register_handler(TaskType.GIT_OPERATION, git_handler)
        
        # 交付处理器
        def delivery_handler(plan_id: str, subtask: SubTask):
            if self._delivery:
                return self._delivery.package(plan_id, subtask)
            return "交付模块未初始化"
        
        self.scheduler.register_handler(TaskType.DELIVERY, delivery_handler)
    
    def set_modules(
        self,
        environment=None,
        code_generator=None,
        test_runner=None,
        git_manager=None,
        delivery=None
    ):
        """设置功能模块"""
        self._environment = environment
        self._code_generator = code_generator
        self._test_runner = test_runner
        self._git_manager = git_manager
        self._delivery = delivery
        self.logger.info("功能模块已设置")
    
    def execute(self, request: str) -> Dict:
        """
        执行用户请求
        
        Args:
            request: 用户请求文本
        
        Returns:
            Dict: 执行结果
        """
        from .task_parser import TaskParser
        
        self.logger.info(f"接收用户请求：{request[:100]}...")
        
        # 解析任务
        parser = TaskParser()
        plan = parser.parse(request)
        
        # 执行计划
        success = self.scheduler.execute_plan(plan)
        
        # 生成报告
        report = self.tracker.get_progress_report(plan.id)
        report["success"] = success
        
        return report
    
    def get_progress(self, plan_id: str) -> Dict:
        """获取任务进度"""
        return self.tracker.get_progress_report(plan_id)
    
    def get_briefing(self, plan_id: str) -> str:
        """获取任务简报"""
        return self.tracker.generate_briefing(plan_id)
