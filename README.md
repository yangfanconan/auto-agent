# Auto-Agent v2.0

**全自动工程化编程智能体** - 支持 qwencode/opencode 工具，实现编程全流程自动化

## 🎉 v2.0 新特性

- 🎨 **Rich 可视化界面** - 美化终端输出、进度条、表格展示
- 🧠 **智能任务解析** - 任务模板系统、项目类型识别、语义理解
- 📚 **知识库系统** - 项目索引、代码搜索、问答查询
- 🔧 **虚拟环境管理** - 自动创建 venv、依赖安装
- 📦 **项目脚手架** - 6 种项目模板一键初始化
- 🤖 **智能 Git 提交** - 自动生成提交信息、分支策略管理
- ✅ **增强测试** - 改进覆盖率解析、测试失败智能修复
- 💬 **友好错误** - 错误引导、建议提示

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

### 示例 1：项目初始化

```
📝 任务指令：创建一个 Python 包项目
```

Auto-Agent 会自动：
1. 创建标准 Python 包结构
2. 生成 README、setup.py、requirements.txt
3. 初始化 Git 仓库
4. 创建基础测试框架

### 示例 2：代码生成

```
📝 任务指令：用 Python 写一个带单元测试的计算器类
```

### 示例 3：Web API 开发

```
📝 任务指令：用 FastAPI 创建一个用户管理 API
```

### 示例 4：完整流程

```
📝 任务指令：创建一个待办事项管理应用，包含 CRUD 操作和测试
```

## 项目结构

```
auto-agent/
├── core/                    # 核心框架
│   ├── task_parser.py      # 任务解析器（增强版）
│   ├── task_tracker.py     # 任务跟踪器
│   ├── scheduler.py        # 任务调度器
│   └── knowledge_base.py   # [新增] 知识库
├── modules/                 # 功能模块
│   ├── environment.py      # 环境自动化（增强版）
│   ├── code_generator.py   # 代码生成（增强版）
│   ├── test_runner.py      # 自动化测试（增强版）
│   ├── git_manager.py      # Git 管理（增强版）
│   └── delivery.py         # 交付打包
├── adapters/                # 工具适配器
│   ├── opencode_adapter.py # Opencode 适配器
│   ├── qwencode_adapter.py # Qwencode 适配器
│   └── tool_registry.py    # 工具注册中心
├── ui/                      # [新增] UI 模块
│   ├── console.py          # 控制台 UI
│   ├── components.py       # UI 组件
│   └── themes.py           # 主题配置
├── utils/                   # 工具函数
│   ├── logger.py           # 日志系统
│   ├── config.py           # 配置管理
│   └── exceptions.py       # 异常定义（增强版）
├── config/                  # 配置文件
│   └── settings.yaml
├── tests/                   # 单元测试
│   ├── test_task_parser.py
│   ├── test_ui_components.py
│   └── test_knowledge_base.py
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
  smart_commit: true  # 智能生成提交信息

# 测试配置
test:
  auto_test: true
  coverage_threshold: 90.0
  auto_fix: true  # 自动修复失败测试

# 环境配置
environment:
  venv:
    auto_create: true  # 自动创建虚拟环境
    path: ".venv"

# UI 配置
ui:
  theme: default  # default, dark, light, monokai
  rich_output: true
```

## 交互模式命令

| 命令 | 别名 | 说明 |
|------|------|------|
| `quit` | exit, q | 退出程序 |
| `help` | h, ? | 显示帮助信息 |
| `status` | s | 查看当前任务状态 |
| `history` | hist | 查看任务历史 |
| `clear` | cls | 清屏 |
| `theme` | - | 切换主题 |
| `briefing` | b | 显示任务简报 |
| `tools` | - | 查看工具状态 |
| `config` | - | 查看配置 |
| `export` | - | 导出报告 (json\|md) |
| `retry` | - | 重试失败任务 |
| `cancel` | - | 取消当前任务 |

**提示**：支持 Tab 键自动补全命令

## 项目模板

Auto-Agent 支持多种项目模板：

| 模板 | 说明 | 包含内容 |
|------|------|----------|
| `python_package` | Python 包 | src/, tests/, setup.py, README.md |
| `web_api` | Web API | app/, routes/, models/, requirements.txt |
| `cli_tool` | 命令行工具 | src/cli.py, commands/, setup.py |
| `data_science` | 数据科学 | notebooks/, data/, src/ |
| `frontend_vue` | Vue 前端 | Vue 3 + Vite 项目结构 |
| `frontend_react` | React 前端 | React + Vite 项目结构 |

使用示例：
```
📝 任务指令：创建一个 Python 包项目
📝 任务指令：用 FastAPI 创建 Web API 服务
```

## API 使用

```python
from auto_agent import AutoAgent, EnvironmentManager, CodeGenerator

# 初始化智能体
agent = AutoAgent(workspace="/path/to/project")

# 设置模块
agent.set_modules(
    environment=EnvironmentManager(),
    code_generator=CodeGenerator(),
    test_runner=TestRunner(),
    git_manager=GitManager(),
    delivery=DeliveryManager()
)

# 执行任务
result = agent.execute("用 Python 写一个冒泡排序")

# 查看进度
print(agent.get_briefing(result['plan_id']))

# 代码审查
review = code_generator.review_code(code, "python")
print(f"代码评分：{review['score']}")

# 知识库
from core.knowledge_base import KnowledgeBase
kb = KnowledgeBase("/path/to/project")
kb.index_project()
answer = kb.query("有哪些类？")
```

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

### 虚拟环境创建失败

```bash
# 确保 venv 模块可用
python -m venv --help

# 手动创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_task_parser.py -v

# 查看覆盖率
pytest --cov=auto_agent --cov-report=html
```

## 许可证

MIT License

## 版本

v2.0.0

### 更新日志

#### v2.0.0 (2026-03-14)
- ✨ 新增 Rich 可视化界面
- ✨ 新增知识库模块
- ✨ 新增项目模板系统
- ✨ 增强任务解析器
- ✨ 增强 Git 智能提交
- ✨ 增强测试覆盖率解析
- ✨ 新增虚拟环境管理
- ✨ 新增友好错误提示
- 🐛 修复多个已知问题
