"""
任务解析器
解析用户需求，拆分为可执行的子任务
"""

import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from ..utils import TaskParseException, get_logger
except ImportError:
    from utils import TaskParseException, get_logger


class TaskType(Enum):
    """任务类型"""
    CODE_GENERATION = "code_generation"       # 代码生成
    ENVIRONMENT_SETUP = "environment_setup"   # 环境搭建
    TESTING = "testing"                       # 测试
    GIT_OPERATION = "git_operation"           # Git 操作
    DELIVERY = "delivery"                     # 交付
    DOCUMENTATION = "documentation"           # 文档编写
    CODE_REVIEW = "code_review"               # 代码审查
    OPTIMIZATION = "optimization"             # 代码优化
    UNKNOWN = "unknown"                       # 未知类型


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SubTask:
    """子任务"""
    id: str
    name: str
    description: str
    task_type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed, skipped
    result: Optional[str] = None
    error: Optional[str] = None
    progress: float = 0.0  # 0-100
    estimated_duration: Optional[int] = None  # 预估耗时（秒）
    actual_duration: Optional[float] = None  # 实际耗时（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "metadata": self.metadata
        }


@dataclass
class TaskPlan:
    """任务计划"""
    id: str
    title: str
    description: str
    original_request: str
    subtasks: List[SubTask] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "original_request": self.original_request,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata
        }
    
    def get_progress(self) -> float:
        """获取整体进度"""
        if not self.subtasks:
            return 0.0
        
        total_progress = sum(t.progress for t in self.subtasks)
        return total_progress / len(self.subtasks)
    
    def get_completed_count(self) -> int:
        """获取已完成子任务数"""
        return sum(1 for t in self.subtasks if t.status == "completed")
    
    def get_failed_count(self) -> int:
        """获取失败子任务数"""
        return sum(1 for t in self.subtasks if t.status == "failed")


class TaskParser:
    """任务解析器"""
    
    # 任务类型关键词映射
    TASK_TYPE_KEYWORDS = {
        TaskType.CODE_GENERATION: ["写代码", "编写代码", "开发", "实现", "创建", "生成", "code", "develop", "implement", "create"],
        TaskType.ENVIRONMENT_SETUP: ["环境", "安装", "配置", "依赖", "setup", "environment", "install", "configure", "dependency"],
        TaskType.TESTING: ["测试", "单元测试", "集成测试", "test", "unit test", "integration test"],
        TaskType.GIT_OPERATION: ["git", "提交", "commit", "push", "分支", "branch", "merge", "pull"],
        TaskType.DELIVERY: ["交付", "打包", "发布", "deploy", "delivery", "package", "release"],
        TaskType.DOCUMENTATION: ["文档", "说明", "readme", "documentation", "doc", "manual"],
        TaskType.CODE_REVIEW: ["审查", "review", "代码审查", "code review", "审计", "audit"],
        TaskType.OPTIMIZATION: ["优化", "重构", "optimize", "refactor", "性能", "performance"],
    }
    
    def __init__(self):
        self.logger = get_logger()
    
    def parse(self, request: str) -> TaskPlan:
        """
        解析用户请求，生成任务计划
        
        Args:
            request: 用户请求文本
        
        Returns:
            TaskPlan: 任务计划
        """
        import uuid
        from datetime import datetime
        
        self.logger.info(f"解析任务请求：{request[:100]}...")
        
        # 生成任务 ID
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()
        
        # 提取任务标题和描述
        title, description = self._extract_title_description(request)
        
        # 识别任务类型
        task_types = self._identify_task_types(request)
        
        # 生成子任务
        subtasks = self._generate_subtasks(request, task_types)
        
        # 创建任务计划
        plan = TaskPlan(
            id=task_id,
            title=title,
            description=description,
            original_request=request,
            subtasks=subtasks,
            status="pending",
            created_at=timestamp,
            updated_at=timestamp
        )
        
        self.logger.info(f"任务解析完成：{task_id}, 包含 {len(subtasks)} 个子任务")
        
        return plan
    
    def _extract_title_description(self, request: str) -> tuple:
        """提取标题和描述"""
        # 简单实现，可根据需求优化
        lines = request.strip().split('\n')
        title = lines[0][:50] if lines else "未命名任务"
        description = request.strip()
        
        return title, description
    
    def _identify_task_types(self, request: str) -> List[TaskType]:
        """识别任务类型"""
        request_lower = request.lower()
        identified_types = []
        
        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in request_lower:
                    if task_type not in identified_types:
                        identified_types.append(task_type)
                    break
        
        if not identified_types:
            identified_types.append(TaskType.UNKNOWN)
        
        return identified_types
    
    def _generate_subtasks(self, request: str, task_types: List[TaskType]) -> List[SubTask]:
        """生成子任务列表"""
        subtasks = []
        
        # 根据任务类型生成标准子任务流程
        if TaskType.ENVIRONMENT_SETUP in task_types or TaskType.CODE_GENERATION in task_types:
            # 环境检查任务
            subtasks.append(SubTask(
                id="task_env_check",
                name="环境检查",
                description="扫描当前运行环境，检查依赖和工具状态",
                task_type=TaskType.ENVIRONMENT_SETUP,
                priority=TaskPriority.HIGH,
                estimated_duration=30
            ))
        
        if TaskType.CODE_GENERATION in task_types:
            # 代码开发任务
            subtasks.append(SubTask(
                id="task_code_dev",
                name="代码开发",
                description="使用工具自动编写代码",
                task_type=TaskType.CODE_GENERATION,
                priority=TaskPriority.HIGH,
                dependencies=["task_env_check"] if any(t.id == "task_env_check" for t in subtasks) else [],
                estimated_duration=300
            ))
        
        if TaskType.TESTING in task_types or TaskType.CODE_GENERATION in task_types:
            # 测试任务（如果包含代码生成，默认添加测试）
            subtasks.append(SubTask(
                id="task_test",
                name="自动化测试",
                description="编写并执行测试用例",
                task_type=TaskType.TESTING,
                priority=TaskPriority.HIGH,
                dependencies=["task_code_dev"] if any(t.id == "task_code_dev" for t in subtasks) else [],
                estimated_duration=120
            ))
        
        if TaskType.GIT_OPERATION in task_types or TaskType.DELIVERY in task_types:
            # Git 提交任务
            subtasks.append(SubTask(
                id="task_git",
                name="Git 提交",
                description="执行 Git 提交和推送",
                task_type=TaskType.GIT_OPERATION,
                priority=TaskPriority.MEDIUM,
                dependencies=["task_test"] if any(t.id == "task_test" for t in subtasks) else [],
                estimated_duration=30
            ))
        
        if TaskType.DELIVERY in task_types:
            # 交付打包任务
            subtasks.append(SubTask(
                id="task_delivery",
                name="交付打包",
                description="生成交付产物和文档",
                task_type=TaskType.DELIVERY,
                priority=TaskPriority.MEDIUM,
                dependencies=["task_git"] if any(t.id == "task_git" for t in subtasks) else [],
                estimated_duration=60
            ))
        
        # 如果没有生成任何子任务，添加一个通用任务
        if not subtasks:
            subtasks.append(SubTask(
                id="task_general",
                name="通用任务",
                description=request[:100],
                task_type=TaskType.UNKNOWN,
                priority=TaskPriority.MEDIUM,
                estimated_duration=60
            ))
        
        return subtasks
    
    def refine_task(self, plan: TaskPlan, feedback: str) -> TaskPlan:
        """
        根据反馈优化任务计划
        
        Args:
            plan: 原任务计划
            feedback: 用户反馈
        
        Returns:
            TaskPlan: 优化后的任务计划
        """
        self.logger.info(f"根据反馈优化任务计划：{feedback[:50]}...")
        
        # 简单实现：将反馈添加到描述中
        plan.description = f"{plan.description}\n\n用户反馈：{feedback}"
        
        from datetime import datetime
        plan.updated_at = datetime.now().isoformat()
        
        return plan
