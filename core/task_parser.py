"""
任务解析器
解析用户需求，拆分为可执行的子任务

增强版：支持语义理解、任务模板、多轮对话澄清
"""

import re
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

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
    PROJECT_INIT = "project_init"             # 项目初始化
    UNKNOWN = "unknown"                       # 未知类型


class TaskPriority(Enum):
    """任务优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# 项目结构模板
PROJECT_TEMPLATES = {
    "python_package": {
        "name": "Python 包",
        "structure": [
            "src/__init__.py",
            "src/main.py",
            "src/utils/",
            "tests/__init__.py",
            "tests/test_main.py",
            "docs/",
            "requirements.txt",
            "setup.py",
            "README.md",
            ".gitignore",
        ],
        "description": "标准 Python 包结构，支持 pip 安装",
    },
    "web_api": {
        "name": "Web API 项目",
        "structure": [
            "app/__init__.py",
            "app/main.py",
            "app/routes/",
            "app/models/",
            "app/schemas/",
            "app/services/",
            "tests/",
            "requirements.txt",
            "README.md",
        ],
        "description": "FastAPI/Flask Web API 项目结构",
    },
    "cli_tool": {
        "name": "命令行工具",
        "structure": [
            "src/__init__.py",
            "src/cli.py",
            "src/commands/",
            "tests/",
            "requirements.txt",
            "setup.py",
            "README.md",
        ],
        "description": "命令行工具项目结构",
    },
    "data_science": {
        "name": "数据科学项目",
        "structure": [
            "notebooks/",
            "src/__init__.py",
            "src/data/",
            "src/features/",
            "src/models/",
            "data/raw/",
            "data/processed/",
            "requirements.txt",
            "README.md",
        ],
        "description": "数据科学/机器学习项目结构",
    },
    "frontend_vue": {
        "name": "Vue 前端项目",
        "structure": [
            "src/main.js",
            "src/App.vue",
            "src/components/",
            "src/views/",
            "src/router/",
            "src/store/",
            "public/index.html",
            "package.json",
            "vite.config.js",
        ],
        "description": "Vue 3 + Vite 前端项目结构",
    },
    "frontend_react": {
        "name": "React 前端项目",
        "structure": [
            "src/main.jsx",
            "src/App.jsx",
            "src/components/",
            "src/pages/",
            "src/hooks/",
            "src/store/",
            "index.html",
            "package.json",
            "vite.config.js",
        ],
        "description": "React + Vite 前端项目结构",
    },
}


# 任务模板
TASK_TEMPLATES = {
    "web_app": {
        "name": "Web 应用开发",
        "subtasks": [
            {"name": "项目初始化", "type": TaskType.PROJECT_INIT, "priority": TaskPriority.HIGH},
            {"name": "环境配置", "type": TaskType.ENVIRONMENT_SETUP, "priority": TaskPriority.HIGH},
            {"name": "后端 API 开发", "type": TaskType.CODE_GENERATION, "priority": TaskPriority.HIGH},
            {"name": "前端页面开发", "type": TaskType.CODE_GENERATION, "priority": TaskPriority.HIGH},
            {"name": "集成测试", "type": TaskType.TESTING, "priority": TaskPriority.HIGH},
            {"name": "文档编写", "type": TaskType.DOCUMENTATION, "priority": TaskPriority.MEDIUM},
        ],
    },
    "cli_tool": {
        "name": "命令行工具",
        "subtasks": [
            {"name": "项目初始化", "type": TaskType.PROJECT_INIT, "priority": TaskPriority.HIGH},
            {"name": "命令行参数解析", "type": TaskType.CODE_GENERATION, "priority": TaskPriority.HIGH},
            {"name": "核心功能实现", "type": TaskType.CODE_GENERATION, "priority": TaskPriority.HIGH},
            {"name": "单元测试", "type": TaskType.TESTING, "priority": TaskPriority.HIGH},
            {"name": "使用文档", "type": TaskType.DOCUMENTATION, "priority": TaskPriority.MEDIUM},
        ],
    },
    "python_lib": {
        "name": "Python 库开发",
        "subtasks": [
            {"name": "项目初始化", "type": TaskType.PROJECT_INIT, "priority": TaskPriority.HIGH},
            {"name": "核心模块开发", "type": TaskType.CODE_GENERATION, "priority": TaskPriority.HIGH},
            {"name": "单元测试", "type": TaskType.TESTING, "priority": TaskPriority.HIGH},
            {"name": "API 文档", "type": TaskType.DOCUMENTATION, "priority": TaskPriority.MEDIUM},
            {"name": "发布配置", "type": TaskType.DELIVERY, "priority": TaskPriority.MEDIUM},
        ],
    },
    "code_refactor": {
        "name": "代码重构",
        "subtasks": [
            {"name": "代码分析", "type": TaskType.CODE_REVIEW, "priority": TaskPriority.HIGH},
            {"name": "重构优化", "type": TaskType.OPTIMIZATION, "priority": TaskPriority.HIGH},
            {"name": "测试验证", "type": TaskType.TESTING, "priority": TaskPriority.HIGH},
        ],
    },
}


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
    template_name: Optional[str] = None  # 使用的模板名称

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
            "metadata": self.metadata,
            "template_name": self.template_name
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
    """任务解析器（增强版）"""

    # 任务类型关键词映射（增强版）
    TASK_TYPE_KEYWORDS = {
        TaskType.CODE_GENERATION: ["写代码", "编写代码", "开发", "实现", "创建", "生成", "code", "develop", "implement", "create", "编写一个", "创建一个"],
        TaskType.ENVIRONMENT_SETUP: ["环境", "安装", "配置", "依赖", "setup", "environment", "install", "configure", "dependency", "搭建"],
        TaskType.TESTING: ["测试", "单元测试", "集成测试", "test", "unit test", "integration test"],
        TaskType.GIT_OPERATION: ["git", "提交", "commit", "push", "分支", "branch", "merge", "pull"],
        TaskType.DELIVERY: ["交付", "打包", "发布", "deploy", "delivery", "package", "release"],
        TaskType.DOCUMENTATION: ["文档", "说明", "readme", "documentation", "doc", "manual"],
        TaskType.CODE_REVIEW: ["审查", "review", "代码审查", "code review", "审计", "audit"],
        TaskType.OPTIMIZATION: ["优化", "重构", "optimize", "refactor", "性能", "performance"],
        TaskType.PROJECT_INIT: ["项目", "初始化", "init", "create project", "新建项目"],
    }

    # 项目类型关键词
    PROJECT_TYPE_KEYWORDS = {
        "python_package": ["python 包", "python package", "pip 包", "library", "库"],
        "web_api": ["web api", "api", "web 服务", "flask", "fastapi", "后端"],
        "cli_tool": ["命令行", "cli", "终端工具", "command line"],
        "data_science": ["数据科学", "data science", "机器学习", "ml", "数据分析"],
        "frontend_vue": ["vue", "前端", "frontend", "vue3"],
        "frontend_react": ["react", "前端", "frontend", "jsx"],
    }

    def __init__(self, use_llm: bool = False):
        self.logger = get_logger()
        self.use_llm = use_llm  # 是否使用 LLM 语义理解

    def parse(self, request: str) -> TaskPlan:
        """
        解析用户请求，生成任务计划

        Args:
            request: 用户请求文本

        Returns:
            TaskPlan: 任务计划
        """
        self.logger.info(f"解析任务请求：{request[:100]}...")

        # 生成任务 ID
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.now().isoformat()

        # 提取任务标题和描述
        title, description = self._extract_title_description(request)

        # 识别任务类型和项目类型
        task_types = self._identify_task_types(request)
        project_type = self._identify_project_type(request)

        # 检查是否匹配任务模板
        template = self._match_task_template(request, task_types)

        if template and not self._has_explicit_template(request):
            # 使用模板生成子任务
            subtasks = self._generate_subtasks_from_template(template, request)
            template_name = template["name"]
        else:
            # 标准方式生成子任务
            subtasks = self._generate_subtasks(request, task_types, project_type)
            template_name = None

        # 创建任务计划
        plan = TaskPlan(
            id=task_id,
            title=title,
            description=description,
            original_request=request,
            subtasks=subtasks,
            status="pending",
            created_at=timestamp,
            updated_at=timestamp,
            template_name=template_name,
            metadata={"project_type": project_type} if project_type else {}
        )

        self.logger.info(f"任务解析完成：{task_id}, 包含 {len(subtasks)} 个子任务")

        return plan

    def _extract_title_description(self, request: str) -> tuple:
        """提取标题和描述（增强版）"""
        lines = request.strip().split('\n')
        
        # 尝试从第一行提取标题
        first_line = lines[0].strip() if lines else "未命名任务"
        title = first_line[:80] if len(first_line) > 80 else first_line
        
        # 完整描述
        description = request.strip()

        return title, description

    def _identify_task_types(self, request: str) -> List[TaskType]:
        """识别任务类型（增强版）"""
        request_lower = request.lower()
        identified_types = []

        # 首先检查是否是文档/总结类任务
        if any(word in request_lower for word in ["总结", "分析", "报告", "文档", "说明", "describe", "summary", "analyze"]):
            identified_types.append(TaskType.DOCUMENTATION)

        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in request_lower:
                    if task_type not in identified_types:
                        identified_types.append(task_type)
                    break

        # 如果没有识别到类型，根据常见模式推断
        if not identified_types:
            # 检查是否是项目初始化
            if any(word in request_lower for word in ["创建", "新建", "init", "new"]):
                identified_types.append(TaskType.PROJECT_INIT)
            else:
                identified_types.append(TaskType.CODE_GENERATION)

        return identified_types

    def _identify_project_type(self, request: str) -> Optional[str]:
        """识别项目类型"""
        request_lower = request.lower()
        
        for project_type, keywords in self.PROJECT_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in request_lower:
                    return project_type
        
        return None

    def _match_task_template(self, request: str, task_types: List[TaskType]) -> Optional[Dict]:
        """匹配任务模板"""
        request_lower = request.lower()
        
        # 检查是否明确指定模板
        for template_key, template in TASK_TEMPLATES.items():
            if template_key in request_lower or template["name"] in request:
                return template
        
        # 根据任务类型推断模板
        if TaskType.PROJECT_INIT in task_types:
            if any(word in request_lower for word in ["web", "网站", "应用"]):
                return TASK_TEMPLATES.get("web_app")
            elif any(word in request_lower for word in ["命令行", "cli", "工具"]):
                return TASK_TEMPLATES.get("cli_tool")
            elif any(word in request_lower for word in ["python", "包", "library", "库"]):
                return TASK_TEMPLATES.get("python_lib")
        
        if TaskType.CODE_REVIEW in task_types or TaskType.OPTIMIZATION in task_types:
            return TASK_TEMPLATES.get("code_refactor")
        
        return None

    def _has_explicit_template(self, request: str) -> bool:
        """检查用户是否明确要求不使用模板"""
        return any(word in request.lower() for word in ["简单", "快速", "只要", "仅"])

    def _generate_subtasks_from_template(self, template: Dict, request: str) -> List[SubTask]:
        """从模板生成子任务"""
        subtasks = []
        
        for i, task_info in enumerate(template["subtasks"]):
            subtask = SubTask(
                id=f"task_{i+1:03d}",
                name=task_info["name"],
                description=f"执行{task_info['name']}",
                task_type=task_info["type"],
                priority=task_info.get("priority", TaskPriority.MEDIUM),
                dependencies=[],  # 模板中可定义依赖
                estimated_duration=self._estimate_duration(task_info["type"])
            )
            
            # 设置依赖关系
            if i > 0:
                subtask.dependencies = [f"task_{j+1:03d}" for j in range(i)]
            
            subtasks.append(subtask)
        
        return subtasks

    def _estimate_duration(self, task_type: TaskType) -> int:
        """预估任务耗时（秒）"""
        durations = {
            TaskType.PROJECT_INIT: 60,
            TaskType.ENVIRONMENT_SETUP: 120,
            TaskType.CODE_GENERATION: 300,
            TaskType.TESTING: 180,
            TaskType.GIT_OPERATION: 30,
            TaskType.DELIVERY: 60,
            TaskType.DOCUMENTATION: 120,
            TaskType.CODE_REVIEW: 180,
            TaskType.OPTIMIZATION: 240,
        }
        return durations.get(task_type, 120)

    def _generate_subtasks(self, request: str, task_types: List[TaskType], project_type: Optional[str] = None) -> List[SubTask]:
        """生成子任务列表（增强版）"""
        subtasks = []

        # 检查是否是开放式问题（让 Qwen 自主决策）
        is_open_question = any(word in request.lower() for word in [
            "如何", "怎么", "what", "how", "why", "分析", "总结", "描述", "介绍",
            "配置", "情况", "状态", "check", "describe"
        ])
        
        # 如果是开放式问题，创建一个通用任务让 Qwen 自主决策
        if is_open_question and len(task_types) == 1 and task_types[0] in [TaskType.DOCUMENTATION, TaskType.ENVIRONMENT_SETUP]:
            subtasks.append(SubTask(
                id="task_qwen_agent",
                name="Qwen 智能执行",
                description=f"请分析用户需求并自主决策执行必要的步骤：{request[:200]}",
                task_type=TaskType.CODE_GENERATION,  # 使用代码生成类型，会调用 Qwen
                priority=TaskPriority.HIGH,
                estimated_duration=600,
                metadata={"auto_agent": True, "request": request}
            ))
            return subtasks

        # 项目初始化任务
        if TaskType.PROJECT_INIT in task_types or project_type:
            subtasks.append(SubTask(
                id="task_project_init",
                name="项目初始化",
                description=f"初始化{project_type or '项目'}结构",
                task_type=TaskType.PROJECT_INIT,
                priority=TaskPriority.HIGH,
                estimated_duration=60,
                metadata={"project_type": project_type}
            ))

        # 环境检查任务
        if TaskType.ENVIRONMENT_SETUP in task_types or TaskType.CODE_GENERATION in task_types:
            subtasks.append(SubTask(
                id="task_env_check",
                name="环境检查",
                description="扫描当前运行环境，检查依赖和工具状态",
                task_type=TaskType.ENVIRONMENT_SETUP,
                priority=TaskPriority.HIGH,
                estimated_duration=30
            ))

        # 代码开发任务
        if TaskType.CODE_GENERATION in task_types:
            subtasks.append(SubTask(
                id="task_code_dev",
                name="代码开发",
                description="使用工具自动编写代码",
                task_type=TaskType.CODE_GENERATION,
                priority=TaskPriority.HIGH,
                dependencies=self._get_dependencies(subtasks, ["task_env_check", "task_project_init"]),
                estimated_duration=300
            ))

        # 测试任务
        if TaskType.TESTING in task_types or (TaskType.CODE_GENERATION in task_types and "测试" not in request):
            subtasks.append(SubTask(
                id="task_test",
                name="自动化测试",
                description="编写并执行测试用例",
                task_type=TaskType.TESTING,
                priority=TaskPriority.HIGH,
                dependencies=self._get_dependencies(subtasks, ["task_code_dev"]),
                estimated_duration=120
            ))

        # Git 提交任务
        if TaskType.GIT_OPERATION in task_types or TaskType.DELIVERY in task_types:
            subtasks.append(SubTask(
                id="task_git",
                name="Git 提交",
                description="执行 Git 提交和推送",
                task_type=TaskType.GIT_OPERATION,
                priority=TaskPriority.MEDIUM,
                dependencies=self._get_dependencies(subtasks, ["task_test"]),
                estimated_duration=30
            ))

        # 交付打包任务
        if TaskType.DELIVERY in task_types:
            subtasks.append(SubTask(
                id="task_delivery",
                name="交付打包",
                description="生成交付产物和文档",
                task_type=TaskType.DELIVERY,
                priority=TaskPriority.MEDIUM,
                dependencies=self._get_dependencies(subtasks, ["task_git"]),
                estimated_duration=60
            ))

        # 如果没有生成任何子任务，添加一个通用任务
        if not subtasks:
            subtasks.append(SubTask(
                id="task_general",
                name="通用任务",
                description=request[:200],
                task_type=TaskType.UNKNOWN,
                priority=TaskPriority.MEDIUM,
                estimated_duration=60
            ))

        return subtasks

    def _get_dependencies(self, subtasks: List[SubTask], potential_deps: List[str]) -> List[str]:
        """获取依赖列表（只包含已存在的任务 ID）"""
        existing_ids = {task.id for task in subtasks}
        return [dep for dep in potential_deps if dep in existing_ids]

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
        plan.updated_at = datetime.now().isoformat()

        return plan

    def get_available_templates(self) -> Dict[str, Dict]:
        """获取可用任务模板"""
        return {
            key: {"name": t["name"], "description": t.get("description", "")}
            for key, t in TASK_TEMPLATES.items()
        }

    def get_project_templates(self) -> Dict[str, Dict]:
        """获取可用项目结构模板"""
        return {
            key: {"name": t["name"], "description": t["description"]}
            for key, t in PROJECT_TEMPLATES.items()
        }
