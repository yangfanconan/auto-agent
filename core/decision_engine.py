"""
智能决策引擎模块
实现预设规则 + Qwen 智能决策的双层决策系统

支持：
- 预设规则处置（自动重试、等待确认、空闲监听）
- Qwen 智能决策（需求解析、异常诊断、状态决策）
- 决策日志记录和追溯
- 高危操作用户确认机制
"""

import asyncio
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    from ..utils import get_logger, load_config
    from ..adapters.base_tool import ToolStatus, ToolResult, get_tool_registry
    from ..core.events import publish_event, EventType
    from ..core.console_io import get_console_redirector
except ImportError:
    from utils import get_logger, load_config
    from adapters.base_tool import ToolStatus, ToolResult, get_tool_registry
    from core.events import publish_event, EventType
    from core.console_io import get_console_redirector


class DecisionType(str, Enum):
    """决策类型"""
    AUTO_RETRY = "auto_retry"           # 自动重试
    WAIT_USER = "wait_user"             # 等待用户确认
    CALL_QWEN = "call_qwen"             # 调用 Qwen 决策
    STOP = "stop"                       # 停止执行
    CONTINUE = "continue"               # 继续执行
    SWITCH_TOOL = "switch_tool"         # 切换工具


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"                     # 低风险 - 自动执行
    MEDIUM = "medium"               # 中风险 - 记录日志
    HIGH = "high"                   # 高风险 - 需要用户确认
    CRITICAL = "critical"           # 严重风险 - 禁止自动执行


@dataclass
class DecisionContext:
    """决策上下文"""
    tool_name: str
    tool_status: ToolStatus
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    task_id: Optional[str] = None
    task_description: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "tool_name": self.tool_name,
            "tool_status": self.tool_status.value,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "meta": self.meta,
        }


@dataclass
class DecisionResult:
    """决策结果"""
    decision_type: DecisionType
    reason: str
    action: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    qwen_suggestion: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "decision_type": self.decision_type.value,
            "reason": self.reason,
            "action": self.action,
            "risk_level": self.risk_level.value,
            "qwen_suggestion": self.qwen_suggestion,
            "meta": self.meta,
        }


class RuleEngine:
    """预设规则引擎"""

    def __init__(self, config: Optional[Dict] = None):
        self.logger = get_logger()
        self.config = config or {}
        self._default_rules: List[Dict] = []
        self._custom_rules: List[Dict] = []
        self._load_default_rules()

    def _load_default_rules(self):
        """加载默认规则"""
        self._default_rules = [
            # 错误处理规则
            {
                "name": "timeout_retry",
                "condition": lambda ctx: ctx.error_message and "timeout" in ctx.error_message.lower(),
                "action": DecisionType.AUTO_RETRY,
                "reason": "超时错误，自动重试",
                "risk_level": RiskLevel.LOW,
            },
            {
                "name": "connection_retry",
                "condition": lambda ctx: ctx.error_message and "connection" in ctx.error_message.lower(),
                "action": DecisionType.AUTO_RETRY,
                "reason": "连接错误，自动重试",
                "risk_level": RiskLevel.LOW,
            },
            {
                "name": "max_retries_exceeded",
                "condition": lambda ctx: ctx.retry_count >= ctx.max_retries,
                "action": DecisionType.CALL_QWEN,
                "reason": "超过最大重试次数，请求 Qwen 决策",
                "risk_level": RiskLevel.MEDIUM,
            },
            # 状态处理规则
            {
                "name": "waiting_user",
                "condition": lambda ctx: ctx.tool_status == ToolStatus.WAITING,
                "action": DecisionType.WAIT_USER,
                "reason": "等待用户确认",
                "risk_level": RiskLevel.HIGH,
            },
            {
                "name": "error_state",
                "condition": lambda ctx: ctx.tool_status == ToolStatus.ERROR and ctx.retry_count < ctx.max_retries,
                "action": DecisionType.AUTO_RETRY,
                "reason": "工具异常，自动重试",
                "risk_level": RiskLevel.LOW,
            },
            {
                "name": "error_state_max_retries",
                "condition": lambda ctx: ctx.tool_status == ToolStatus.ERROR and ctx.retry_count >= ctx.max_retries,
                "action": DecisionType.SWITCH_TOOL,
                "reason": "工具异常且超过重试次数，切换工具",
                "risk_level": RiskLevel.MEDIUM,
            },
            {
                "name": "idle_continue",
                "condition": lambda ctx: ctx.tool_status == ToolStatus.IDLE and not ctx.error_message,
                "action": DecisionType.CONTINUE,
                "reason": "工具空闲，继续执行",
                "risk_level": RiskLevel.LOW,
            },
        ]

    def evaluate(self, context: DecisionContext) -> Optional[DecisionResult]:
        """评估规则（自定义规则优先）"""
        # 先检查自定义规则
        for rule in self._custom_rules:
            try:
                if rule["condition"](context):
                    return DecisionResult(
                        decision_type=rule["action"],
                        reason=rule["reason"],
                        risk_level=rule.get("risk_level", RiskLevel.LOW),
                    )
            except Exception as e:
                self.logger.error(
                    f"自定义规则评估失败 [{rule.get('name', 'unknown')}]: {e}")

        # 再检查默认规则
        for rule in self._default_rules:
            try:
                if rule["condition"](context):
                    return DecisionResult(
                        decision_type=rule["action"],
                        reason=rule["reason"],
                        risk_level=rule.get("risk_level", RiskLevel.LOW),
                    )
            except Exception as e:
                self.logger.error(
                    f"默认规则评估失败 [{rule.get('name', 'unknown')}]: {e}")

        # 无匹配规则
        return None

    def add_rule(self, name: str, condition: Callable, action: DecisionType,
                 reason: str, risk_level: RiskLevel = RiskLevel.LOW):
        """添加自定义规则（优先级高于默认规则）"""
        self._custom_rules.append({
            "name": name,
            "condition": condition,
            "action": action,
            "reason": reason,
            "risk_level": risk_level,
        })
        self.logger.info(f"自定义规则已添加：{name}")


class QwenDecisionEngine:
    """Qwen 智能决策引擎"""

    def __init__(self, config: Optional[Dict] = None):
        self.logger = get_logger()
        self.config = config or {}
        self.console_io = get_console_redirector()
        self._qwen_tool = None
        self._lock = threading.Lock()

    def _get_qwen_tool(self):
        """获取 Qwen 工具实例"""
        if self._qwen_tool is None:
            try:
                registry = get_tool_registry()
                self._qwen_tool = registry.get("qwen")
            except BaseException:
                pass
        return self._qwen_tool

    async def make_decision(self, context: DecisionContext) -> DecisionResult:
        """
        Qwen 智能决策

        流程：
        1. 构建决策上下文
        2. 调用 Qwen 获取决策建议
        3. 解析 Qwen 返回的决策
        4. 返回决策结果
        """
        self.logger.info("启动 Qwen 智能决策")

        # 构建决策提示
        prompt = self._build_decision_prompt(context)

        # 发送状态通知
        self.console_io.send_status(
            "🧠 Qwen 正在分析决策...",
            {"context": "decision_making", "tool": context.tool_name}
        )

        try:
            # 异步调用 Qwen（独立线程，不阻塞主程序）
            result = await self._call_qwen_async(prompt)

            # 解析 Qwen 返回的决策
            decision = self._parse_qwen_result(result, context)

            self.logger.info(f"Qwen 决策完成：{decision.decision_type.value}")
            return decision

        except Exception as e:
            self.logger.error(f"Qwen 决策失败：{e}")
            # 降级为自动重试（不等待用户）
            if context.retry_count < context.max_retries:
                return DecisionResult(
                    decision_type=DecisionType.AUTO_RETRY,
                    reason=f"Qwen 决策失败：{e}，自动重试",
                    risk_level=RiskLevel.LOW,
                )
            else:
                # 超过重试次数，切换工具
                return DecisionResult(
                    decision_type=DecisionType.SWITCH_TOOL,
                    reason=f"Qwen 决策失败且超过重试次数，切换工具",
                    risk_level=RiskLevel.MEDIUM,
                )

    def _build_decision_prompt(self, context: DecisionContext) -> str:
        """构建决策提示词"""
        prompt = f"""你是一个智能决策助手。请分析以下工具执行状态，并给出决策建议。

## 工具状态
- 工具名称：{context.tool_name}
- 当前状态：{context.tool_status.value}
- 错误信息：{context.error_message or '无'}
- 重试次数：{context.retry_count}/{context.max_retries}
- 任务 ID: {context.task_id or '无'}
- 任务描述：{context.task_description or '无'}

## 可用决策选项
1. AUTO_RETRY - 自动重试（适用于临时错误）
2. WAIT_USER - 等待用户确认（适用于高风险操作）
3. CONTINUE - 继续执行（适用于非致命错误）
4. SWITCH_TOOL - 切换工具（适用于工具故障）
5. STOP - 停止执行（适用于严重错误）

## 返回格式
请严格按以下 JSON 格式返回：
{{
    "decision": "决策选项",
    "reason": "决策理由",
    "action": "具体操作建议",
    "risk_level": "low|medium|high|critical"
}}

## 决策要求
1. 优先尝试自动恢复（重试、切换工具）
2. 高风险操作必须用户确认
3. 给出明确的修复建议
"""
        return prompt

    async def _call_qwen_async(self, prompt: str) -> str:
        """异步调用 Qwen"""
        qwen_tool = self._get_qwen_tool()

        if not qwen_tool:
            raise RuntimeError("Qwen 工具不可用")

        # 在线程池中运行（避免阻塞异步事件循环）
        loop = asyncio.get_event_loop()

        def run_qwen():
            # 使用同步方式调用（Qwen 工具内部处理异步）
            import subprocess
            try:
                result = subprocess.run(
                    ["qwen", "--yolo", prompt],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                return result.stdout
            except Exception as e:
                return f"Qwen 调用失败：{e}"

        return await loop.run_in_executor(None, run_qwen)

    def _parse_qwen_result(self, result: str,
                           context: DecisionContext) -> DecisionResult:
        """解析 Qwen 返回的结果"""
        try:
            # 尝试提取 JSON
            json_start = result.find('{')
            json_end = result.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = result[json_start:json_end]
                data = json.loads(json_str)

                decision_type = DecisionType(data.get("decision", "WAIT_USER"))
                risk_level = RiskLevel(data.get("risk_level", "medium"))

                return DecisionResult(
                    decision_type=decision_type,
                    reason=data.get("reason", "Qwen 建议"),
                    action=data.get("action"),
                    risk_level=risk_level,
                    qwen_suggestion=result,
                )

        except Exception as e:
            self.logger.warning(f"解析 Qwen 结果失败：{e}，使用默认决策")

        # 解析失败，使用默认决策
        return DecisionResult(
            decision_type=DecisionType.WAIT_USER,
            reason="无法解析 Qwen 返回，等待用户确认",
            risk_level=RiskLevel.HIGH,
            qwen_suggestion=result,
        )

    async def analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """
        Qwen 需求解析

        将用户需求拆解为可执行的子任务
        """
        prompt = f"""你是一个资深全栈工程师。请分析以下需求，并拆解为可执行的子任务。

## 用户需求
{requirement}

## 返回格式
请严格按以下 JSON 格式返回：
{{
    "summary": "需求简述",
    "complexity": "low|medium|high",
    "estimated_steps": 5,
    "subtasks": [
        {{
            "name": "子任务名称",
            "description": "子任务描述",
            "tool": "opencode|qwen",
            "priority": 1
        }}
    ],
    "risks": ["潜在风险 1", "潜在风险 2"],
    "suggestions": ["建议 1", "建议 2"]
}}
"""
        result = await self._call_qwen_async(prompt)

        try:
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(result[json_start:json_end])
        except BaseException:
            pass

        # 解析失败，返回默认结构
        return {
            "summary": requirement,
            "complexity": "medium",
            "estimated_steps": 3,
            "subtasks": [
                {"name": "需求分析", "description": requirement,
                    "tool": "qwen", "priority": 1},
                {"name": "代码实现", "description": "根据需求编写代码",
                    "tool": "opencode", "priority": 2},
                {"name": "测试验证", "description": "测试功能是否正常",
                    "tool": "opencode", "priority": 3},
            ],
            "risks": [],
            "suggestions": ["建议先进行需求分析", "注意代码质量"],
        }

    async def diagnose_error(
            self, error: str, context: str = "") -> Dict[str, Any]:
        """
        Qwen 异常诊断

        分析错误原因并给出修复方案
        """
        prompt = f"""你是一个故障诊断专家。请分析以下错误，并给出修复方案。

## 错误信息
{error}

## 上下文
{context or '无额外上下文'}

## 返回格式
请严格按以下 JSON 格式返回：
{{
    "root_cause": "根本原因",
    "severity": "low|medium|high|critical",
    "solution": "修复方案",
    "prevention": "预防措施",
    "auto_fixable": true|false,
    "auto_fix_command": "自动修复命令（如果有）"
}}
"""
        result = await self._call_qwen_async(prompt)

        try:
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(result[json_start:json_end])
        except BaseException:
            pass

        return {
            "root_cause": "未知原因",
            "severity": "medium",
            "solution": "请检查日志并联系开发者",
            "prevention": "无",
            "auto_fixable": False,
        }


class DecisionEngine:
    """决策引擎（组合预设规则 + Qwen 智能）"""

    def __init__(self, config: Optional[Dict] = None):
        self.logger = get_logger()
        self.config = config or {}
        self.console_io = get_console_redirector()

        # 规则引擎
        self.rule_engine = RuleEngine(config)

        # Qwen 决策引擎
        self.qwen_engine = QwenDecisionEngine(config)

        # 决策历史
        self._decision_history: List[Dict] = []

        # 高危操作确认回调
        self._on_confirm_action: Optional[Callable] = None

        self.logger.info("决策引擎已初始化")

    def set_confirm_callback(self, callback: Callable):
        """设置高危操作确认回调"""
        self._on_confirm_action = callback

    async def make_decision(self, context: DecisionContext) -> DecisionResult:
        """
        双层决策流程

        1. 首先尝试预设规则
        2. 规则不匹配时调用 Qwen
        3. 记录决策历史
        """
        self.logger.info(
            f"开始决策：tool={
                context.tool_name}, status={
                context.tool_status.value}")

        # 第一层：预设规则
        rule_result = self.rule_engine.evaluate(context)

        if rule_result:
            self.logger.info(f"预设规则匹配：{rule_result.decision_type.value}")

            # 检查是否需要升级到 Qwen
            if rule_result.decision_type == DecisionType.CALL_QWEN:
                self.logger.info("规则建议调用 Qwen，启动智能决策")
                result = await self.qwen_engine.make_decision(context)
            else:
                result = rule_result
        else:
            # 第二层：Qwen 智能决策
            self.logger.info("无匹配规则，启动 Qwen 智能决策")
            result = await self.qwen_engine.make_decision(context)

        # 记录决策历史
        self._record_decision(context, result)

        # 检查风险等级
        if result.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            self.logger.warning(f"高风险决策：{result.reason}")

            # 如果需要用户确认
            if result.decision_type == DecisionType.WAIT_USER and self._on_confirm_action:
                self.logger.info("等待用户确认...")
                # 这里可以通过 WebSocket 推送确认请求到前端

        # 发布事件
        publish_event(
            event_type="decision.made",
            payload={
                "context": context.to_dict(),
                "result": result.to_dict(),
            },
            source="decision_engine"
        )

        return result

    def _record_decision(self, context: DecisionContext,
                         result: DecisionResult):
        """记录决策历史"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "context": context.to_dict(),
            "result": result.to_dict(),
        }
        self._decision_history.append(record)

        # 限制历史记录数量
        if len(self._decision_history) > 100:
            self._decision_history = self._decision_history[-100:]

    def get_decision_history(self, limit: int = 20) -> List[Dict]:
        """获取决策历史"""
        return self._decision_history[-limit:]

    async def analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """需求解析（委托给 Qwen）"""
        return await self.qwen_engine.analyze_requirement(requirement)

    async def diagnose_error(
            self, error: str, context: str = "") -> Dict[str, Any]:
        """异常诊断（委托给 Qwen）"""
        return await self.qwen_engine.diagnose_error(error, context)


# 全局实例
_global_decision_engine: Optional[DecisionEngine] = None


def get_decision_engine(config: Optional[Dict] = None) -> DecisionEngine:
    """获取全局决策引擎"""
    global _global_decision_engine
    if _global_decision_engine is None:
        _global_decision_engine = DecisionEngine(config)
    return _global_decision_engine
