"""
核心功能包
"""

from .task_parser import TaskParser, TaskPlan, SubTask, TaskType, TaskPriority
from .task_tracker import TaskTracker, TaskEvent, TaskProgress
from .scheduler import TaskScheduler, AutoAgent

# v3.0 新组件
from .agent_v3 import ReActAgent, run_agent, Observation, Thought, Action, Step
from .mcp_tools import MCPTool, MCPToolRegistry, ToolCall, ToolResult, registry
from .conversation import (
    ConversationManager, ConversationContext, Message, MessageRole,
    IntentRecognizer, ConversationState
)

__all__ = [
    # Task Parser
    'TaskParser',
    'TaskPlan',
    'SubTask',
    'TaskType',
    'TaskPriority',
    # Task Tracker
    'TaskTracker',
    'TaskEvent',
    'TaskProgress',
    # Scheduler
    'TaskScheduler',
    'AutoAgent',
    # v3.0 Agent
    'ReActAgent',
    'run_agent',
    'Observation',
    'Thought',
    'Action',
    'Step',
    # MCP Tools
    'MCPTool',
    'MCPToolRegistry',
    'ToolCall',
    'ToolResult',
    'registry',
    # Conversation
    'ConversationManager',
    'ConversationContext',
    'Message',
    'MessageRole',
    'IntentRecognizer',
    'ConversationState',
]
