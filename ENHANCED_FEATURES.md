# Auto-Agent v2.0 增强版运行说明

## 📋 目录

1. [快速开始](#快速开始)
2. [v2.0 新增功能](#v20-新增功能)
3. [核心模块说明](#核心模块说明)
4. [配置说明](#配置说明)
5. [使用示例](#使用示例)
6. [Web 可视化界面](#web-可视化界面)
7. [API 接口](#api-接口)
8. [故障排查](#故障排查)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /Users/yangfan/Codes/auto-agent
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 默认启动（自动启用 WebSocket 和控制台 IO 接管）
python main.py

# 启动 Web UI 可视化界面
python main.py --webui --host 0.0.0.0 --port 8000

# 仅启用 WebSocket（后台模式）
python main.py --websocket-port 8765
```

### 3. 访问 Web 界面

浏览器访问：`http://localhost:8000`

---

## ✨ v2.0 新增功能

### 1. 控制台 IO 全接管模块

- ✅ 劫持 Python 程序的 stdin/stdout/stderr
- ✅ 捕获所有控制台输入、输出、报错信息
- ✅ 结构化封装 IO 消息（时间戳、来源、类型）
- ✅ 支持开关控制，兼容调试模式

**代码位置**: `core/console_io.py`

### 2. WebSocket 实时可视化模块

- ✅ 异步 WebSocket 服务端
- ✅ 实时推送终端输出、工具状态、任务进度
- ✅ 接收前端用户指令、确认操作
- ✅ 心跳检测、断线重连、消息缓存

**代码位置**: `ui/websocket_server.py`

### 3. 双工具调度与状态管理（OpenCode + Qwen）

| 工具 | 分工 |
|------|------|
| **OpenCode** | 核心代码编写、脚手架生成、代码格式化、测试用例开发、Git 自动化 |
| **Qwen** | 需求语义解析、任务拆解、异常诊断、状态决策、代码优化建议 |

**工具状态**: `IDLE` → `RUNNING` → `WAITING` → `ERROR` → `FINISHED`

**代码位置**: 
- `adapters/base_tool.py` - 工具抽象基类
- `adapters/opencode_adapter.py` - OpenCode 适配器
- `adapters/qwen_adapter.py` - Qwen 适配器
- `core/tool_scheduler.py` - 工具调度器

### 4. 智能状态决策引擎

- ✅ **预设规则处置**: 自动重试（上限 3 次）、等待 Web 确认、空闲监听
- ✅ **Qwen 智能决策**: 规则失效时调用 Qwen 获取处置方案
- ✅ **全程记录**: 状态流转、决策日志、工具调用记录

**代码位置**: `core/decision_engine.py`

### 5. 全流程自动化闭环

```
需求解析 → 拆分子任务 → 调度 OpenCode/Qwen → 环境搭建 → 
代码开发 → 测试 → Git 提交 → 交付打包 → 进度可视化
```

---

## 📦 核心模块说明

### 模块架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      Auto-Agent v2.0                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  ConsoleIO  │  │  WebSocket  │  │  Decision   │         │
│  │   控制台    │  │   可视化    │  │   决策引擎  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│  ┌──────┴────────────────┴────────────────┴──────┐         │
│  │           Tool Scheduler (工具调度器)          │         │
│  └──────┬─────────────────────────────────┬──────┘         │
│         │                                 │                 │
│  ┌──────┴──────┐                   ┌──────┴──────┐         │
│  │  OpenCode   │                   │    Qwen     │         │
│  │  代码开发   │                   │  智能决策   │         │
│  └─────────────┘                   └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 核心类说明

#### 1. ConsoleIORedirector (`core/console_io.py`)

```python
from core.console_io import get_console_redirector, IOMessage

# 获取全局实例
redirector = get_console_redirector()

# 启动捕获
redirector.start()

# 发送工具输出
redirector.send_tool_output("代码生成完成", "opencode")

# 发送状态
redirector.send_status("任务执行中", {"task_id": "123"})
```

#### 2. WebSocketManager (`ui/websocket_server.py`)

```python
from ui.websocket_server import WebSocketManager

# 创建管理器
ws_manager = WebSocketManager(port=8765)

# 启动服务
await ws_manager.start_server()

# 广播消息
await ws_manager.send_message({
    "type": "task",
    "event": "completed",
    "data": {"task_id": "123"}
})
```

#### 3. ToolScheduler (`core/tool_scheduler.py`)

```python
from core.tool_scheduler import get_scheduler, TaskPriority

# 获取全局调度器
scheduler = get_scheduler()

# 提交任务
task_id = await scheduler.submit_task(
    name="代码生成",
    description="用 Python 写一个快速排序",
    tool_name="opencode",
    input_text="用 Python 写一个快速排序",
    priority=TaskPriority.HIGH
)

# 提交任务计划（批量）
plan_id = await scheduler.submit_plan(
    name="项目开发",
    description="完整的项目开发流程",
    subtasks=[
        {"name": "需求分析", "tool": "qwen", "input": "分析需求..."},
        {"name": "代码实现", "tool": "opencode", "input": "编写代码..."},
        {"name": "测试验证", "tool": "opencode", "input": "运行测试..."},
    ]
)
```

#### 4. DecisionEngine (`core/decision_engine.py`)

```python
from core.decision_engine import get_decision_engine, DecisionContext, ToolStatus

# 获取决策引擎
engine = get_decision_engine()

# 构建决策上下文
context = DecisionContext(
    tool_name="opencode",
    tool_status=ToolStatus.ERROR,
    error_message="执行超时",
    retry_count=2,
    max_retries=3
)

# 请求决策
decision = await engine.make_decision(context)
print(decision.decision_type)  # AUTO_RETRY / WAIT_USER / CALL_QWEN
```

---

## ⚙️ 配置说明

编辑 `config/settings.yaml`:

```yaml
# WebSocket 配置
websocket:
  enabled: true
  host: "0.0.0.0"
  port: 8765
  heartbeat_interval: 30.0  # 心跳间隔（秒）

# 控制台 IO 配置
console_io:
  enabled: true
  capture_input: true      # 捕获输入
  capture_output: true     # 捕获输出
  capture_error: true      # 捕获错误
  keep_original: true      # 保留原始控制台输出

# 工具调度配置（通过决策引擎）
decision_engine:
  auto_retry: true
  max_retries: 3
  retry_delay: 1.0
  risk_levels:
    low: "auto_execute"
    medium: "log_only"
    high: "require_confirm"
    critical: "forbidden"
```

---

## 💡 使用示例

### 1. 命令行交互模式

```bash
python main.py

# 输入任务
📝 任务指令：用 Python 写一个计算器类
```

### 2. Web 可视化界面

```bash
python main.py --webui --port 8000
```

访问 `http://localhost:8000`，可以：
- 📊 实时查看工具状态
- 📝 查看控制台输出
- 🚀 创建新任务
- 📋 查看任务进度

### 3. WebSocket 前端连接

```javascript
// 连接 WebSocket
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    console.log('已连接');
    
    // 发送任务
    ws.send(JSON.stringify({
        type: 'command',
        command: '用 Python 写一个快速排序'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'io':
            // 控制台输出
            console.log(`[${data.event}] ${data.data.content}`);
            break;
        case 'task':
            // 任务事件
            console.log(`任务 ${data.event}`);
            break;
        case 'tool':
            // 工具状态
            console.log(`工具状态：${data.data.status}`);
            break;
    }
};
```

### 4. Python 客户端

```python
import asyncio
import websockets
import json

async def main():
    async with websockets.connect("ws://localhost:8765") as ws:
        # 发送任务
        await ws.send(json.dumps({
            "type": "command",
            "command": "分析项目结构"
        }))
        
        # 接收消息
        async for message in ws:
            data = json.loads(message)
            print(f"收到：{data}")

asyncio.run(main())
```

---

## 🔌 API 接口

### Web UI API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | Web 前端页面 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/tools/status` | 获取工具状态 |
| GET | `/api/tasks` | 获取任务列表 |
| POST | `/api/tasks` | 创建任务 |

### 示例

```bash
# 获取工具状态
curl http://localhost:8000/api/tools/status

# 创建任务
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "用 Python 写一个 hello world", "tool": "opencode"}'

# 获取任务列表
curl http://localhost:8000/api/tasks
```

---

## 🧪 测试

```bash
# 运行单元测试
pytest tests/test_decision_engine.py -v
pytest tests/test_tool_scheduler.py -v

# 测试 WebSocket 连接
python tests/test_websocket.py

# 测试控制台 IO
python tests/test_console_io.py
```

---

## 🐛 故障排查

### WebSocket 无法连接

```bash
# 检查端口是否被占用
lsof -i :8765

# 检查防火墙
sudo lsof -iTCP -sTCP:LISTEN
```

### 控制台 IO 未捕获

```bash
# 检查配置
python main.py --verbose

# 确认是否启用
cat config/settings.yaml | grep console_io
```

### 工具状态不更新

```python
# 检查事件总线
from core.events import get_event_bus
bus = get_event_bus()
print(bus.get_stats())
```

### Web UI 无法访问

```bash
# 检查服务是否运行
lsof -i :8000

# 检查静态文件
ls -la ui/static/

# 重启服务
pkill -f "python main.py"
python main.py --webui
```

---

## 📈 更新日志

### v2.0.0 (2026-03-15)

**新增功能**
- ✨ 控制台 IO 接管模块
- ✨ WebSocket 实时交互服务
- ✨ 工具抽象层和调度框架
- ✨ 智能决策引擎（预设规则 + Qwen）
- ✨ Web 可视化界面

**改进**
- 🚀 支持双工具智能切换
- 🚀 支持异步执行和并发
- 🚀 支持状态感知和自动决策

**修复**
- 🐛 修复多个已知问题

---

## 📞 支持

如有问题，请查看日志文件：

```bash
tail -f logs/auto-agent_*.log
```

或运行诊断命令：

```bash
python main.py --check
```
