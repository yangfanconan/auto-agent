# Auto-Agent

**全自动工程化编程智能体** - 支持 qwencode/opencode 工具，实现编程全流程自动化

## 功能特性

- 🤖 **智能任务解析** - 自动分析需求，拆分为可执行子任务
- 🔧 **环境自动化** - 自动检测、修复运行环境
- 💻 **代码生成** - 调用 opencode/qwencode 自动编写代码
- 📊 **任务跟踪** - 实时进度跟踪，生成简报
- ✅ **自动化测试** - 生成测试用例，执行测试，修复 bug
- 📦 **交付打包** - 生成交付产物和文档
- 🔄 **Git 自动化** - 自动提交、推送、分支管理

## 快速开始

### 1. 安装依赖

```bash
cd /Users/yangfan/Codes/auto-agent
pip install -r requirements.txt
```

### 2. 检查环境

```bash
python main.py --check
```

### 3. 运行

**交互模式**（推荐）：
```bash
python main.py
```

**命令模式**：
```bash
python main.py -c "用 Python 写一个快速排序算法"
```

**指定工作空间**：
```bash
python main.py -w /path/to/project -c "分析项目结构并生成文档"
```

## 使用示例

### 示例 1：代码生成

```
📝 任务指令：用 Python 写一个带单元测试的计算器类
```

### 示例 2：环境搭建

```
📝 任务指令：配置 Python Web 开发环境，安装 Flask 和依赖
```

### 示例 3：完整流程

```
📝 任务指令：创建一个待办事项管理应用，包含 CRUD 操作和测试
```

## 项目结构

```
auto-agent/
├── core/                    # 核心框架
│   ├── task_parser.py      # 任务解析器
│   ├── task_tracker.py     # 任务跟踪器
│   └── scheduler.py        # 任务调度器
├── modules/                 # 功能模块
│   ├── environment.py      # 环境自动化
│   ├── code_generator.py   # 代码生成
│   ├── test_runner.py      # 自动化测试
│   ├── git_manager.py      # Git 管理
│   └── delivery.py         # 交付打包
├── adapters/                # 工具适配器
│   ├── opencode_adapter.py # Opencode 适配器
│   ├── qwencode_adapter.py # Qwencode 适配器
│   └── tool_registry.py    # 工具注册中心
├── utils/                   # 工具函数
│   ├── logger.py           # 日志系统
│   ├── config.py           # 配置管理
│   └── exceptions.py       # 异常定义
├── config/                  # 配置文件
│   └── settings.yaml
├── main.py                  # 入口文件
└── requirements.txt         # 依赖清单
```

## 配置说明

编辑 `config/settings.yaml` 自定义配置：

```yaml
# Opencode 配置
opencode:
  enabled: true
  path: ""  # 空表示自动检测 ~/.opencode/bin/opencode
  timeout: 300

# Git 配置
git:
  auto_commit: true
  auto_push: false
  branch_prefix: feature

# 测试配置
test:
  auto_test: true
  coverage_threshold: 90.0
```

## API 使用

```python
from auto_agent import AutoAgent, EnvironmentManager, CodeGenerator

# 初始化智能体
agent = AutoAgent(workspace="/path/to/project")

# 设置模块
agent.set_modules(
    environment=EnvironmentManager(),
    code_generator=CodeGenerator()
)

# 执行任务
result = agent.execute("用 Python 写一个冒泡排序")

# 查看进度
print(agent.get_briefing(result['plan_id']))
```

## 命令参考

| 命令 | 说明 |
|------|------|
| `python main.py` | 启动交互模式 |
| `python main.py -c "命令"` | 执行单个任务 |
| `python main.py --check` | 检查环境 |
| `python main.py -w /path` | 指定工作空间 |
| `status` | 查看任务状态（交互模式） |
| `help` | 显示帮助（交互模式） |
| `quit` | 退出（交互模式） |

## 日志

运行日志保存在 `logs/` 目录：
- `auto-agent_YYYYMMDD_HHMMSS.log` - 文本日志
- `auto-agent_YYYYMMDD_HHMMSS.json` - JSON 格式日志

## 交付产物

交付包保存在 `deliveries/` 目录：
- 源代码文件
- 测试报告和文档
- 元数据文件（delivery.json）

## 注意事项

1. **Opencode** 是核心工具，请确保已安装并可用
2. **Qwencode** 是可选工具，用于批量代码生成和格式化
3. 首次运行会自动检测工具路径，可在配置文件中手动指定
4. Git 操作需要配置用户信息（user.name 和 user.email）

## 故障排除

### Opencode 未找到

```bash
# 检查安装
ls -la ~/.opencode/bin/opencode

# 或手动配置路径
# 编辑 config/settings.yaml
opencode:
  path: /path/to/opencode
```

### 测试覆盖率检查失败

```bash
# 安装 pytest-cov
pip install pytest-cov

# 或禁用覆盖率检查
# 编辑 config/settings.yaml
test:
  auto_test: false
```

## 许可证

MIT License

## 版本

v1.0.0
