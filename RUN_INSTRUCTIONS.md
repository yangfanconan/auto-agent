# Auto-Agent v2.0 核心架构升级 - 运行说明

## 🚀 快速启动

### 1. 安装依赖

```bash
cd /Users/yangfan/Codes/auto-agent
pip install -r requirements.txt
```

### 2. 启动增强模式

```bash
# 默认启动（自动启用 WebSocket 和控制台 IO 接管）
python main.py

# 自定义 WebSocket 端口
python main.py --websocket-port 9000

# 禁用控制台 IO 接管
python main.py --no-console-redirect

# 仅启用控制台 IO 接管
python main.py --enable-console-redirect
```

## 📡 WebSocket 连接示例

### JavaScript 前端连接

```javascript
// 连接 WebSocket
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    console.log('已连接到 Auto-Agent');
    ws.send(JSON.stringify({
        type: 'command',
        command: '用 Python 写一个快速排序'
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'io':
            // 控制台 IO
            console.log(`[${data.event}] ${data.data.content}`);
            break;
        case 'task':
            // 任务事件
            console.log(`任务 ${data.event}: ${JSON.stringify(data.data)}`);
            break;
        case 'tool':
            // 工具状态
            console.log(`工具状态变更：${data.data.old_status} → ${data.data.new_status}`);
            break;
    }
};
```

### Python 客户端

```python
import asyncio
import websockets

async def connect():
    async with websockets.connect("ws://localhost:8765") as ws:
        # 发送命令
        await ws.send('{"type": "command", "command": "分析项目结构"}')
        
        # 接收消息
        async for message in ws:
            data = json.loads(message)
            print(f"收到：{data}")

asyncio.run(connect())
```

## 🔧 工具调度示例

### 直接使用工具

```python
import asyncio
from adapters.base_tool import get_tool_registry

async def main():
    registry = get_tool_registry()
    
    # 运行 Qwen
    result = await registry.run_tool("qwen", "用 Python 写一个计算器类")
    print(f"Qwen 结果：{result.output}")
    
    # 运行 OpenCode
    result = await registry.run_tool("opencode", "生成快速排序代码")
    print(f"OpenCode 结果：{result.output}")

asyncio.run(main())
```

### 监听工具状态

```python
from adapters.base_tool import ToolStatus, QwenTool

def on_status_change(status: ToolStatus):
    print(f"工具状态变更：{status.value}")
    
    if status == ToolStatus.WAITING:
        print("需要用户操作！")
    elif status == ToolStatus.ERROR:
        print("工具出错，自动重试中...")

tool = QwenTool()
tool.set_status_change_callback(on_status_change)
```

## 📊 控制台 IO 接管示例

```python
from core.console_io import start_console_capture, IOMessage

def on_io_message(message: IOMessage):
    print(f"[{message.type.value}] {message.source.value}: {message.content}")

start_console_capture(on_io_message)

# 现在所有控制台输出都会被捕获并推送
print("这条消息会被捕获")
input("输入也会被捕获")
```

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

# 工具调度配置
scheduler:
  auto_retry: true
  max_retries: 3
  retry_delay: 1.0
  state_decision:
    on_error: "retry"       # retry/notify_user/stop
    on_waiting: "notify_user"  # notify_user/auto_continue
```

## 🧪 测试

```bash
# 运行单元测试
pytest tests/test_console_io.py -v
pytest tests/test_tool_scheduler.py -v

# 测试 WebSocket 连接
python tests/test_websocket.py
```

## 📈 架构优势

1. **模块化设计** - 各模块独立，易于扩展和维护
2. **异步执行** - 不阻塞主线程，支持高并发
3. **状态感知** - 实时感知工具状态，智能决策
4. **可扩展性** - 新增工具只需实现 BaseTool 接口
5. **兼容性** - 完全兼容现有 Auto-Agent v2.0 架构

## 🐛 故障排除

### WebSocket 无法连接

```bash
# 检查端口是否被占用
lsof -i:8765

# 检查防火墙
sudo lsof -iTCP -sTCP:LISTEN
```

### 控制台 IO 未捕获

```bash
# 检查是否启用
python main.py --enable-console-redirect

# 查看详细日志
python main.py -v
```

### 工具状态不更新

```python
# 检查事件订阅
from core.events import get_event_bus
bus = get_event_bus()
print(bus.get_stats())
```

## 📝 更新日志

### v2.0.0 (2026-03-15)
- ✨ 新增控制台 IO 接管模块
- ✨ 新增 WebSocket 实时交互服务
- ✨ 新增工具抽象层和调度框架
- ✨ 支持工具状态感知和智能决策
- ✨ 支持异步执行和并发控制
- 🐛 修复多个已知问题
