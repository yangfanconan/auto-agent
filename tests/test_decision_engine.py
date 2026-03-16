"""
决策引擎单元测试
测试预设规则引擎和 Qwen 智能决策引擎
"""

from core.decision_engine import (
    DecisionEngine, RuleEngine, QwenDecisionEngine,
    DecisionContext, DecisionResult, DecisionType, RiskLevel,
    ToolStatus
)
import pytest
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestRuleEngine:
    """测试规则引擎"""

    def setup_method(self):
        """每个测试前的设置"""
        self.rule_engine = RuleEngine()

    def test_timeout_retry_rule(self):
        """测试超时重试规则"""
        context = DecisionContext(
            tool_name="opencode",
            tool_status=ToolStatus.ERROR,
            error_message="Execution timeout expired",
            retry_count=0,
            max_retries=3
        )

        result = self.rule_engine.evaluate(context)

        assert result is not None
        assert result.decision_type == DecisionType.AUTO_RETRY
        assert result.risk_level == RiskLevel.LOW

    def test_connection_retry_rule(self):
        """测试连接错误重试规则"""
        context = DecisionContext(
            tool_name="qwen",
            tool_status=ToolStatus.ERROR,
            error_message="Connection refused",
            retry_count=1,
            max_retries=3
        )

        result = self.rule_engine.evaluate(context)

        assert result is not None
        assert result.decision_type == DecisionType.AUTO_RETRY

    def test_max_retries_exceeded_rule(self):
        """测试超过最大重试次数规则"""
        context = DecisionContext(
            tool_name="opencode",
            tool_status=ToolStatus.ERROR,
            error_message="Some error",
            retry_count=3,
            max_retries=3
        )

        result = self.rule_engine.evaluate(context)

        assert result is not None
        assert result.decision_type == DecisionType.CALL_QWEN

    def test_waiting_user_rule(self):
        """测试等待用户规则"""
        context = DecisionContext(
            tool_name="qwen",
            tool_status=ToolStatus.WAITING,
            retry_count=0,
            max_retries=3
        )

        result = self.rule_engine.evaluate(context)

        assert result is not None
        assert result.decision_type == DecisionType.WAIT_USER
        assert result.risk_level == RiskLevel.HIGH

    def test_error_state_rule(self):
        """测试错误状态规则"""
        context = DecisionContext(
            tool_name="opencode",
            tool_status=ToolStatus.ERROR,
            error_message="Unknown error",
            retry_count=0,
            max_retries=3
        )

        result = self.rule_engine.evaluate(context)

        assert result is not None
        assert result.decision_type == DecisionType.CALL_QWEN

    def test_idle_continue_rule(self):
        """测试空闲继续规则"""
        context = DecisionContext(
            tool_name="qwen",
            tool_status=ToolStatus.IDLE,
            retry_count=0,
            max_retries=3
        )

        result = self.rule_engine.evaluate(context)

        assert result is not None
        assert result.decision_type == DecisionType.CONTINUE

    def test_add_custom_rule(self):
        """测试添加自定义规则"""
        def custom_condition(ctx):
            return ctx.tool_name == "custom_tool"

        self.rule_engine.add_rule(
            name="custom_rule",
            condition=custom_condition,
            action=DecisionType.SWITCH_TOOL,
            reason="自定义规则测试",
            risk_level=RiskLevel.MEDIUM
        )

        context = DecisionContext(
            tool_name="custom_tool",
            tool_status=ToolStatus.IDLE
        )

        result = self.rule_engine.evaluate(context)

        assert result is not None
        # 自定义规则应该优先于默认规则
        assert result.decision_type == DecisionType.SWITCH_TOOL
        assert result.reason == "自定义规则测试"


class TestDecisionContext:
    """测试决策上下文"""

    def test_context_to_dict(self):
        """测试上下文转字典"""
        context = DecisionContext(
            tool_name="opencode",
            tool_status=ToolStatus.RUNNING,
            error_message="Test error",
            retry_count=1,
            max_retries=3,
            task_id="task_123",
            task_description="Test task",
            meta={"key": "value"}
        )

        data = context.to_dict()

        assert data["tool_name"] == "opencode"
        assert data["tool_status"] == "RUNNING"
        assert data["error_message"] == "Test error"
        assert data["retry_count"] == 1
        assert data["max_retries"] == 3
        assert data["task_id"] == "task_123"
        assert data["meta"]["key"] == "value"


class TestDecisionResult:
    """测试决策结果"""

    def test_result_to_dict(self):
        """测试结果转字典"""
        result = DecisionResult(
            decision_type=DecisionType.AUTO_RETRY,
            reason="超时错误，自动重试",
            action="retry_now",
            risk_level=RiskLevel.LOW,
            qwen_suggestion="建议重试",
            meta={"retry_delay": 1.0}
        )

        data = result.to_dict()

        assert data["decision_type"] == "auto_retry"
        assert data["reason"] == "超时错误，自动重试"
        assert data["action"] == "retry_now"
        assert data["risk_level"] == "low"
        assert data["qwen_suggestion"] == "建议重试"


class TestDecisionEngine:
    """测试决策引擎"""

    def setup_method(self):
        """每个测试前的设置"""
        self.decision_engine = DecisionEngine()

    @pytest.mark.asyncio
    async def test_rule_based_decision(self):
        """测试基于规则的决策"""
        context = DecisionContext(
            tool_name="opencode",
            tool_status=ToolStatus.ERROR,
            error_message="Connection timeout",
            retry_count=0,
            max_retries=3
        )

        result = await self.decision_engine.make_decision(context)

        # 应该匹配超时重试规则
        assert result.decision_type == DecisionType.AUTO_RETRY

    @pytest.mark.asyncio
    async def test_decision_history_recording(self):
        """测试决策历史记录"""
        context = DecisionContext(
            tool_name="qwen",
            tool_status=ToolStatus.IDLE
        )

        await self.decision_engine.make_decision(context)

        history = self.decision_engine.get_decision_history()
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_high_risk_decision(self):
        """测试高风险决策"""
        context = DecisionContext(
            tool_name="opencode",
            tool_status=ToolStatus.WAITING,
            retry_count=0,
            max_retries=3
        )

        result = await self.decision_engine.make_decision(context)

        # 等待用户确认应该是高风险
        assert result.risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]


class TestRiskLevel:
    """测试风险等级"""

    def test_risk_level_values(self):
        """测试风险等级值"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"


class TestDecisionType:
    """测试决策类型"""

    def test_decision_type_values(self):
        """测试决策类型值"""
        assert DecisionType.AUTO_RETRY.value == "auto_retry"
        assert DecisionType.WAIT_USER.value == "wait_user"
        assert DecisionType.CALL_QWEN.value == "call_qwen"
        assert DecisionType.STOP.value == "stop"
        assert DecisionType.CONTINUE.value == "continue"
        assert DecisionType.SWITCH_TOOL.value == "switch_tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
