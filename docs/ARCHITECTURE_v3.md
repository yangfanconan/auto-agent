# Auto-Agent v3.0 架构设计

> 参考 Qwen Code 架构，实现 ReAct + MCP + 对话管理的完整 Agent 系统

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Auto-Agent v3.0                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  ReActAgent  │◄──►│    Memory    │◄──►│  MCP Tools   │      │
│  │              │    │   System     │    │   Registry   │      │
│  │ • Observe    │    │              │    │              │      │
│  │ • Think      │    │ • Short-term │    │ • read_file  │      │
│  │ • Act        │    │ • Long-term  │    │ • write_file │      │
│  │ • Reflect    │    │ • Working    │    │ • execute    │      │
│  └──────┬───────┘    └──────────────┘    └──────────────┘      │
│         │                                                       │
│  ┌──────▼────────────────────────────────────────────────┐     │
│  │              Observation-Action Loop                   │     │
│  │                                                        │     │
│  │   User Input ──► Observe ──► Think ──► Act ──► Output │     │
│  │                      ▲                    │            │     │
│  │                      └────────────────────┘            │     │
│  │                           (Feedback)                   │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │              Conversation Manager                      │     │
│  │                                                        │     │
│  │  • Multi-turn Dialogue    • Context Compression       │     │
│  │  • Intent Recognition     • Session Persistence       │     │
│  │  • State Management       • History Summary           │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. ReAct Agent (`core/agent_v3.py`)

基于 **ReAct (Reasoning + Acting)** 模式的智能体核心。

#### 核心流程

```python
# ReAct 循环
for iteration in range(max_iterations):
    # 1. 观察
    observation = observe(environment)

    # 2. 思考
    thought = think(observation, memory)

    # 3. 行动
    action = decide_action(thought)
    result = execute(action)

    # 4. 反思
    memory.add_step(observation, thought, action, result)

    # 5. 检查完成
    if action.type == FINISH:
        break
```

#### 关键类

| 类名 | 说明 |
|------|------|
| `ReActAgent` | 主智能体类 |
| `Observation` | 观察结果 |
| `Thought` | 思考过程 |
| `Action` | 行动定义 |
| `Step` | 执行步骤 |

### 2. MCP 工具系统 (`core/mcp_tools.py`)

参考 **Model Context Protocol (MCP)** 设计的工具调用系统。

#### 特性

- **标准化接口**: 统一的工具注册和执行机制
- **模式定义**: 自动从函数签名推断参数模式
- **异步支持**: 支持同步和异步工具
- **中间件**: 支持工具调用前后处理

#### 预置工具

| 工具名 | 功能 |
|--------|------|
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件 |
| `list_directory` | 列出目录 |
| `execute_command` | 执行系统命令 |
| `search_code` | 搜索代码 |
| `calculate` | 计算表达式 |
| `get_current_time` | 获取当前时间 |

#### 使用示例

```python
from core.mcp_tools import registry, ToolCall

# 执行工具
call = ToolCall(
    id="call_1",
    name="read_file",
    arguments={"path": "./main.py"}
)
result = await registry.execute(call)
```

### 3. 对话管理系统 (`core/conversation.py`)

支持多轮对话和上下文管理的完整系统。

#### 特性

- **会话管理**: 创建、切换、删除会话
- **消息历史**: 完整的对话记录
- **上下文压缩**: 智能压缩长对话
- **意图识别**: 自动识别用户意图
- **状态管理**: 对话状态跟踪

#### 关键类

| 类名 | 说明 |
|------|------|
| `ConversationManager` | 对话管理器 |
| `ConversationContext` | 对话上下文 |
| `Message` | 消息对象 |
| `IntentRecognizer` | 意图识别器 |

#### 使用示例

```python
from core.conversation import ConversationManager, MessageRole

# 创建管理器
manager = ConversationManager("./conversations.json")

# 创建会话
ctx = manager.create_session()

# 添加消息
ctx.add_message(MessageRole.USER, "帮我写代码")
ctx.add_message(MessageRole.ASSISTANT, "好的，请告诉我具体需求")

# 获取历史
history = ctx.get_history()
```

## 使用方式

### 方式 1: 直接使用 ReAct Agent

```python
import asyncio
from core.agent_v3 import ReActAgent

async def main():
    agent = ReActAgent()

    result = await agent.run("创建一个 Python 文件，输出 Hello World")

    print(f"成功: {result['success']}")
    print(f"结果: {result['result']}")
    print(f"步骤: {result['steps']}")

asyncio.run(main())
```

### 方式 2: 使用 MCP 工具

```python
from core.mcp_tools import registry, ToolCall

# 列出工具
for tool in registry.list_tools():
    print(f"{tool['function']['name']}")

# 执行工具
call = ToolCall(
    id="1",
    name="calculate",
    arguments={"expression": "2 ** 10"}
)
result = await registry.execute(call)
print(result.content)
```

### 方式 3: 完整对话流程

```python
from core import ReActAgent, ConversationManager, MessageRole, IntentRecognizer

# 初始化
agent = ReActAgent()
manager = ConversationManager()
recognizer = IntentRecognizer()

# 创建会话
ctx = manager.create_session()

# 处理用户输入
user_input = "帮我写一个快速排序"

# 识别意图
intent, confidence = recognizer.get_primary_intent(user_input)
print(f"意图: {intent} ({confidence:.2f})")

# 执行
result = await agent.run(user_input)

# 记录对话
ctx.add_message(MessageRole.USER, user_input)
ctx.add_message(MessageRole.ASSISTANT, result['result'])

# 保存
manager.save()
```

## 架构对比

### v2.0 vs v3.0

| 特性 | v2.0 | v3.0 |
|------|------|------|
| 架构模式 | 线性流水线 | ReAct 循环 |
| 工具调用 | 硬编码 | MCP 协议 |
| 对话管理 | 无 | 完整支持 |
| 记忆系统 | 简单日志 | 短期+长期记忆 |
| 意图识别 | 无 | 内置支持 |
| 上下文压缩 | 无 | 智能压缩 |
| 可扩展性 | 中 | 高 |

## 扩展开发

### 自定义工具

```python
from core.mcp_tools import registry

@registry.tool("my_tool", "我的自定义工具")
def my_tool(param1: str, param2: int = 10) -> str:
    """工具描述"""
    return f"结果: {param1}, {param2}"
```

### 自定义 Agent

```python
from core.agent_v3 import ReActAgent, Thought, Observation

class MyAgent(ReActAgent):
    async def _think(self, observation: Observation) -> Thought:
        # 自定义思考逻辑
        # 可以接入 LLM API
        return Thought(
            reasoning="...",
            plan=["step1", "step2"],
            next_action=ActionType.CODE
        )
```

## 运行演示

```bash
# 运行完整演示
python examples/agent_v3_demo.py
```

演示内容包括：
1. ReAct Agent 执行流程
2. MCP 工具调用
3. 对话管理
4. 完整集成示例

## 未来规划

- [ ] 接入 LLM API (OpenAI, Qwen, etc.)
- [ ] 向量数据库存储长期记忆
- [ ] 多 Agent 协作机制
- [ ] 可视化调试界面
- [ ] 插件系统

---

**参考**: [Qwen Code Architecture](https://qwenlm.github.io/qwen-code-docs/zh/developers/architecture/)
