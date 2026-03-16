"""
Auto-Agent v3.0 - 基于 ReAct 架构的智能体核心

参考 Qwen Code 架构设计：
- ReAct (Reasoning + Acting) 模式
- 观察-思考-行动循环
- 工具调用系统 (MCP 协议)
- 记忆系统 (短期+长期)
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import hashlib

from utils import get_logger


class ActionType(Enum):
    """行动类型"""
    THINK = "think"           # 思考
    CODE = "code"             # 生成代码
    EXECUTE = "execute"       # 执行命令
    FILE_READ = "file_read"   # 读取文件
    FILE_WRITE = "file_write" # 写入文件
    SEARCH = "search"         # 搜索
    ASK = "ask"               # 询问用户
    FINISH = "finish"         # 完成任务


@dataclass
class Observation:
    """观察结果"""
    source: str                          # 来源：user, tool, system
    content: str                         # 内容
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Thought:
    """思考过程"""
    reasoning: str                       # 推理过程
    plan: List[str]                      # 执行计划
    next_action: ActionType              # 下一步行动
    confidence: float = 1.0              # 置信度


@dataclass
class Action:
    """行动"""
    type: ActionType
    params: Dict[str, Any]
    id: str = field(default_factory=lambda: hashlib.md5(
        str(datetime.now()).encode()).hexdigest()[:8])


@dataclass
class Step:
    """执行步骤"""
    observation: Observation
    thought: Thought
    action: Action
    result: Optional[str] = None
    success: bool = True


class MemorySystem:
    """记忆系统 - 短期记忆 + 长期记忆"""

    def __init__(self, max_short_term: int = 10):
        self.logger = get_logger()
        self.short_term: List[Step] = []  # 短期记忆（对话历史）
        self.long_term: Dict[str, Any] = {}  # 长期记忆（知识库）
        self.max_short_term = max_short_term
        self.working_memory: Dict[str, Any] = {}  # 工作记忆

    def add_step(self, step: Step):
        """添加步骤到短期记忆"""
        self.short_term.append(step)
        # 保持短期记忆在限制范围内
        if len(self.short_term) > self.max_short_term:
            self._archive_oldest()

    def _archive_oldest(self):
        """归档最旧的记忆到长期记忆"""
        oldest = self.short_term.pop(0)
        key = f"step_{oldest.action.id}_{datetime.now().isoformat()}"
        self.long_term[key] = {
            "observation": oldest.observation.content,
            "thought": oldest.thought.reasoning,
            "action": oldest.action.type.value,
            "result": oldest.result,
            "success": oldest.success
        }

    def get_context(self, n: int = 5) -> str:
        """获取最近 n 步的上下文"""
        recent = self.short_term[-n:] if self.short_term else []
        context = []
        for step in recent:
            context.append(f"[观察] {step.observation.content[:200]}")
            context.append(f"[思考] {step.thought.reasoning[:200]}")
            context.append(f"[行动] {step.action.type.value}: {step.action.params}")
            if step.result:
                context.append(f"[结果] {step.result[:200]}")
        return "\n".join(context)

    def remember(self, key: str, value: Any):
        """存储到工作记忆"""
        self.working_memory[key] = value

    def recall(self, key: str) -> Optional[Any]:
        """从工作记忆读取"""
        return self.working_memory.get(key)

    def clear_working_memory(self):
        """清空工作记忆"""
        self.working_memory.clear()


class ToolRegistry:
    """工具注册表 - MCP (Model Context Protocol) 风格"""

    def __init__(self):
        self.logger = get_logger()
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict] = {}

    def register(self, name: str, func: Callable, schema: Optional[Dict] = None):
        """注册工具"""
        self._tools[name] = func
        self._schemas[name] = schema or self._infer_schema(func)
        self.logger.debug(f"注册工具: {name}")

    def _infer_schema(self, func: Callable) -> Dict:
        """推断工具参数模式"""
        import inspect
        sig = inspect.signature(func)
        params = {}
        for name, param in sig.parameters.items():
            params[name] = {
                "type": "string" if param.annotation == str else "any",
                "required": param.default == inspect.Parameter.empty
            }
        return {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": params
        }

    async def execute(self, name: str, params: Dict[str, Any]) -> str:
        """执行工具"""
        if name not in self._tools:
            return f"错误: 工具 '{name}' 未找到"

        tool = self._tools[name]
        try:
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**params)
            else:
                result = tool(**params)
            return str(result) if result is not None else "完成"
        except Exception as e:
            self.logger.error(f"工具执行失败 {name}: {e}")
            return f"错误: {str(e)}"

    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        return [
            {"name": name, "schema": schema}
            for name, schema in self._schemas.items()
        ]


class ReActAgent:
    """
    ReAct Agent - 推理+行动循环

    核心流程:
    1. 观察 (Observe) - 接收用户输入或环境反馈
    2. 思考 (Think) - 分析情况，制定计划
    3. 行动 (Act) - 执行工具或生成代码
    4. 循环 - 直到任务完成
    """

    def __init__(self, max_iterations: int = 20):
        self.logger = get_logger()
        self.memory = MemorySystem()
        self.tools = ToolRegistry()
        self.max_iterations = max_iterations
        self._register_default_tools()

    def _register_default_tools(self):
        """注册默认工具"""
        # 文件操作
        self.tools.register("read_file", self._tool_read_file)
        self.tools.register("write_file", self._tool_write_file)
        self.tools.register("list_dir", self._tool_list_dir)

        # 代码执行
        self.tools.register("execute_python", self._tool_execute_python)
        self.tools.register("execute_shell", self._tool_execute_shell)

        # 搜索
        self.tools.register("search_code", self._tool_search_code)

    async def run(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        运行任务

        Args:
            task: 任务描述
            context: 额外上下文

        Returns:
            执行结果
        """
        self.logger.info(f"开始执行任务: {task[:100]}...")
        self.memory.clear_working_memory()

        # 初始观察
        observation = Observation(
            source="user",
            content=task,
            metadata=context or {}
        )

        # ReAct 循环
        for i in range(self.max_iterations):
            self.logger.debug(f"第 {i+1} 轮迭代")

            # 1. 思考
            thought = await self._think(observation)

            # 2. 决定行动
            action = Action(
                type=thought.next_action,
                params=self._prepare_action_params(thought, observation)
            )

            # 3. 执行
            result = await self._act(action)

            # 4. 记录步骤
            step = Step(
                observation=observation,
                thought=thought,
                action=action,
                result=result,
                success=not result.startswith("错误:")
            )
            self.memory.add_step(step)

            # 5. 检查是否完成
            if action.type == ActionType.FINISH:
                return {
                    "success": True,
                    "result": result,
                    "steps": len(self.memory.short_term),
                    "history": self._format_history()
                }

            # 6. 准备下一轮观察
            observation = Observation(
                source="tool" if action.type != ActionType.THINK else "system",
                content=result,
                metadata={"action": action.type.value, "iteration": i+1}
            )

        # 达到最大迭代次数
        return {
            "success": False,
            "result": "达到最大迭代次数，任务未完成",
            "steps": len(self.memory.short_term),
            "history": self._format_history()
        }

    async def _think(self, observation: Observation) -> Thought:
        """
        思考过程 - 分析观察并决定下一步

        这里可以接入 LLM 进行智能推理
        简化版本使用规则引擎
        """
        content = observation.content.lower()
        context = self.memory.get_context(3)

        # 简单规则引擎（实际应使用 LLM）
        if "创建" in content or "生成" in content or "write" in content:
            return Thought(
                reasoning="用户需要创建文件或代码，先生成代码然后写入文件",
                plan=["生成代码", "写入文件", "验证结果"],
                next_action=ActionType.CODE,
                confidence=0.9
            )
        elif "读取" in content or "查看" in content or "read" in content:
            return Thought(
                reasoning="用户需要查看文件内容",
                plan=["读取文件", "分析内容", "返回结果"],
                next_action=ActionType.FILE_READ,
                confidence=0.9
            )
        elif "执行" in content or "运行" in content or "execute" in content:
            return Thought(
                reasoning="用户需要执行代码或命令",
                plan=["执行命令", "捕获输出", "分析结果"],
                next_action=ActionType.EXECUTE,
                confidence=0.9
            )
        elif "完成" in content or "结束" in content or "finish" in content:
            return Thought(
                reasoning="任务已完成",
                plan=[],
                next_action=ActionType.FINISH,
                confidence=1.0
            )
        else:
            return Thought(
                reasoning="需要更多信息或进行思考",
                plan=["分析需求", "制定计划"],
                next_action=ActionType.THINK,
                confidence=0.7
            )

    def _prepare_action_params(self, thought: Thought, observation: Observation) -> Dict[str, Any]:
        """准备行动参数"""
        content = observation.content

        if thought.next_action == ActionType.FILE_READ:
            # 从内容中提取文件路径
            return {"path": self._extract_path(content)}
        elif thought.next_action == ActionType.FILE_WRITE:
            return {
                "path": self._extract_path(content),
                "content": content  # 简化处理
            }
        elif thought.next_action == ActionType.EXECUTE:
            return {"command": content}
        elif thought.next_action == ActionType.CODE:
            return {"description": content}
        else:
            return {"input": content}

    def _extract_path(self, content: str) -> str:
        """从内容中提取路径"""
        # 简化实现：返回第一个看起来像路径的部分
        import re
        paths = re.findall(r'[\w\-/\\.]+\.[\w]+', content)
        return paths[0] if paths else "./output.txt"

    async def _act(self, action: Action) -> str:
        """执行行动"""
        self.logger.info(f"执行行动: {action.type.value}")

        if action.type == ActionType.THINK:
            return f"思考: {action.params.get('input', '')}"

        elif action.type == ActionType.CODE:
            # 生成代码（简化版）
            description = action.params.get("description", "")
            code = self._generate_code(description)
            self.memory.remember("last_code", code)
            return f"生成代码:\n```python\n{code[:500]}...\n```"

        elif action.type == ActionType.FILE_WRITE:
            return await self.tools.execute("write_file", action.params)

        elif action.type == ActionType.FILE_READ:
            return await self.tools.execute("read_file", action.params)

        elif action.type == ActionType.EXECUTE:
            return await self.tools.execute("execute_shell", action.params)

        elif action.type == ActionType.FINISH:
            return action.params.get("result", "任务完成")

        else:
            return f"未实现的行动类型: {action.type}"

    def _generate_code(self, description: str) -> str:
        """生成代码（简化版，实际应调用 LLM）"""
        return f"# {description}\n# 生成的代码\nprint('Hello, World!')"

    def _format_history(self) -> str:
        """格式化执行历史"""
        lines = []
        for i, step in enumerate(self.memory.short_term, 1):
            lines.append(f"\n=== 步骤 {i} ===")
            lines.append(f"观察: {step.observation.content[:100]}...")
            lines.append(f"思考: {step.thought.reasoning}")
            lines.append(f"行动: {step.action.type.value}")
            lines.append(f"结果: {step.result[:100] if step.result else '无'}...")
        return "\n".join(lines)

    # ========== 工具实现 ==========

    def _tool_read_file(self, path: str) -> str:
        """读取文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"错误: 无法读取文件 {path}: {e}"

    def _tool_write_file(self, path: str, content: str) -> str:
        """写入文件"""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"文件已写入: {path}"
        except Exception as e:
            return f"错误: 无法写入文件 {path}: {e}"

    def _tool_list_dir(self, path: str = ".") -> str:
        """列出目录"""
        try:
            p = Path(path)
            items = list(p.iterdir())
            return "\n".join([f"{'[D]' if item.is_dir() else '[F]'} {item.name}"
                            for item in items[:20]])
        except Exception as e:
            return f"错误: {e}"

    def _tool_execute_python(self, code: str) -> str:
        """执行 Python 代码"""
        try:
            # 注意：实际使用时应限制执行环境
            import io
            import sys
            stdout = io.StringIO()
            sys.stdout = stdout
            exec(code, {"__builtins__": __builtins__})
            sys.stdout = sys.__stdout__
            return stdout.getvalue() or "执行完成"
        except Exception as e:
            return f"执行错误: {e}"

    def _tool_execute_shell(self, command: str) -> str:
        """执行 Shell 命令"""
        import subprocess
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True,
                text=True, timeout=30
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"
            return output or "命令执行完成"
        except Exception as e:
            return f"命令执行错误: {e}"

    def _tool_search_code(self, query: str, path: str = ".") -> str:
        """搜索代码"""
        try:
            import subprocess
            result = subprocess.run(
                ["grep", "-r", query, path, "--include=*.py"],
                capture_output=True, text=True
            )
            return result.stdout[:1000] or "未找到匹配"
        except Exception as e:
            return f"搜索错误: {e}"


# 便捷函数
async def run_agent(task: str, **kwargs) -> Dict[str, Any]:
    """运行 Agent 的便捷函数"""
    agent = ReActAgent()
    return await agent.run(task, kwargs)


if __name__ == "__main__":
    # 测试
    async def test():
        agent = ReActAgent()

        # 测试任务
        result = await agent.run("创建一个 Python 文件，输出 Hello World")
        print("=" * 50)
        print(f"成功: {result['success']}")
        print(f"结果: {result['result']}")
        print(f"步骤数: {result['steps']}")
        print("=" * 50)
        print(result['history'])

    asyncio.run(test())
