#!/usr/bin/env python3
"""
Auto-Agent 全自动工程化编程智能体
入口文件

支持 qwencode/opencode 等工具，实现从任务解析→环境搭建→代码开发→测试→交付→Git 提交的全流程自动化
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

try:
    from utils import get_logger, load_config, AgentConfig
    from core import AutoAgent, TaskParser
    from modules import EnvironmentManager, CodeGenerator, TestRunner, GitManager, DeliveryManager
    from adapters import get_registry, list_tools
except ImportError:
    from utils import get_logger, load_config, AgentConfig
    from core import AutoAgent, TaskParser
    from modules import EnvironmentManager, CodeGenerator, TestRunner, GitManager, DeliveryManager
    from adapters import get_registry, list_tools


def print_banner():
    """打印欢迎横幅"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   Auto-Agent 全自动工程化编程智能体 v1.0.0                ║
║                                                           ║
║   支持 qwencode/opencode 工具                             ║
║   全流程自动化：环境→开发→测试→交付→Git                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)


def print_tools_status():
    """打印工具状态"""
    print("\n📦 工具状态:")
    tools = list_tools()
    for name, info in tools.items():
        status = "✅" if info.get("available", False) else "❌"
        version = info.get("version", "N/A")
        print(f"  {status} {name}: {version}")


def run_interactive_mode(workspace: str, config: AgentConfig):
    """运行交互模式"""
    logger = get_logger()
    
    # 初始化智能体
    agent = AutoAgent(workspace=workspace, config=config.__dict__)
    
    # 初始化并设置模块
    env_manager = EnvironmentManager(workspace)
    code_generator = CodeGenerator(workspace)
    test_runner = TestRunner(workspace)
    git_manager = GitManager(workspace)
    delivery = DeliveryManager(workspace)
    
    agent.set_modules(
        environment=env_manager,
        code_generator=code_generator,
        test_runner=test_runner,
        git_manager=git_manager,
        delivery=delivery
    )
    
    print("\n✅ 智能体已就绪，请输入任务指令（输入 'quit' 退出）")
    print("-" * 50)
    
    while True:
        try:
            # 获取用户输入
            user_input = input("\n📝 任务指令：").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break
            
            if user_input.lower() == 'status':
                report = agent.tracker.get_progress_report(agent.scheduler._current_plan.id) if agent.scheduler._current_plan else None
                if report:
                    print("\n📊 当前任务状态:")
                    print(json.dumps(report, indent=2, ensure_ascii=False))
                else:
                    print("\n暂无正在执行的任务")
                continue
            
            if user_input.lower() == 'help':
                print("""
可用命令:
  <任务描述>  - 执行任务，例如："用 Python 写一个计算器"
  status     - 查看当前任务状态
  help       - 显示帮助信息
  quit       - 退出程序
                """)
                continue
            
            # 执行任务
            print("\n🔄 正在处理任务...")
            print("-" * 50)
            
            result = agent.execute(user_input)
            
            # 输出结果
            print("\n" + "=" * 50)
            print("📋 任务执行结果:")
            print("=" * 50)
            
            print(f"\n✅ 完成状态：{'成功' if result.get('success', False) else '部分完成'}")
            print(f"📊 整体进度：{result.get('overall_progress', 0):.1f}%")
            
            # 子任务状态
            subtasks = result.get('subtasks', [])
            if subtasks:
                print("\n子任务:")
                for task in subtasks:
                    status_icon = {"completed": "✅", "failed": "❌", "in_progress": "🔄", "pending": "⏳"}.get(task.get('status', 'pending'), '⏳')
                    print(f"  {status_icon} {task.get('name', 'Unknown')}: {task.get('status', 'pending')}")
            
            # 简报
            if agent.scheduler._current_plan:
                briefing = agent.get_briefing(agent.scheduler._current_plan.id)
                print(f"\n{briefing}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  任务中断")
        except Exception as e:
            print(f"\n❌ 执行错误：{e}")
            logger.error(f"交互模式异常：{e}")


def run_command_mode(command: str, workspace: str, config: AgentConfig):
    """运行命令模式"""
    logger = get_logger()
    
    # 初始化智能体
    agent = AutoAgent(workspace=workspace, config=config.__dict__)
    
    # 初始化并设置模块
    env_manager = EnvironmentManager(workspace)
    code_generator = CodeGenerator(workspace)
    test_runner = TestRunner(workspace)
    git_manager = GitManager(workspace)
    delivery = DeliveryManager(workspace)
    
    agent.set_modules(
        environment=env_manager,
        code_generator=code_generator,
        test_runner=test_runner,
        git_manager=git_manager,
        delivery=delivery
    )
    
    print(f"\n🔄 执行任务：{command}")
    print("-" * 50)
    
    # 执行任务
    result = agent.execute(command)
    
    # 输出 JSON 结果
    print("\n" + "=" * 50)
    print("📋 任务执行结果:")
    print("=" * 50)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    return 0 if result.get('success', False) else 1


def check_environment(workspace: str):
    """检查环境"""
    print("\n🔍 环境检查:")
    print("-" * 50)
    
    env_manager = EnvironmentManager(workspace)
    report = env_manager.scan()
    
    print(f"\n操作系统：{report.os_info}")
    print(f"Python: {report.python_version}")
    print(f"Node.js: {report.node_version or '未安装'}")
    print(f"Git: {report.git_version or '未安装'}")
    print(f"Opencode: {'✅ 可用' if report.opencode_available else '❌ 不可用'}")
    print(f"Qwencode: {'✅ 可用' if report.qwencode_available else '⚠️ 可选'}")
    
    if report.issues:
        print(f"\n⚠️  发现问题:")
        for issue in report.issues:
            print(f"  - {issue}")
    
    if report.recommendations:
        print(f"\n💡 建议:")
        for rec in report.recommendations:
            print(f"  - {rec}")
    
    return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Auto-Agent 全自动工程化编程智能体",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互模式
  python main.py

  # 执行单个任务
  python main.py --command "用 Python 写一个快速排序"

  # 检查环境
  python main.py --check

  # 启动 Web UI
  python main.py --webui

  # 指定工作空间
  python main.py --workspace /path/to/project
        """
    )

    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default=".",
        help="工作空间路径（默认：当前目录）"
    )

    parser.add_argument(
        "--command", "-c",
        type=str,
        help="执行单个任务命令"
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="检查环境并退出"
    )

    parser.add_argument(
        "--webui",
        action="store_true",
        help="启动 Web UI 界面"
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Web UI 监听地址（默认：0.0.0.0）"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Web UI 端口（默认：8000）"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    # 打印横幅
    print_banner()
    
    # 加载配置
    config_path = args.config if args.config else str(Path(__file__).parent / "config" / "settings.yaml")
    config = load_config(config_path)
    
    if args.verbose:
        config.log.level = "DEBUG"
    
    # 初始化日志
    logger = get_logger(log_dir=str(Path(args.workspace) / "logs"))
    logger.info(f"Auto-Agent 启动，工作空间：{args.workspace}")
    
    # 打印工具状态
    print_tools_status()

    # 环境检查模式
    if args.check:
        check_environment(args.workspace)
        return 0

    # Web UI 模式
    if args.webui:
        return run_webui(args.host, args.port)

    # 命令模式
    if args.command:
        return run_command_mode(args.command, args.workspace, config)

    # 交互模式（默认）
    run_interactive_mode(args.workspace, config)

    return 0


def run_webui(host: str, port: int):
    """运行 Web UI"""
    try:
        import uvicorn
        from webui import app
        
        print(f"\n🌐 Web UI 已启动!")
        print(f"   访问地址：http://{host}:{port}")
        print(f"   按 Ctrl+C 停止\n")
        
        uvicorn.run(app, host=host, port=port, log_level="info")
        return 0
    except ImportError:
        print("\n❌ 错误：缺少 Web UI 依赖")
        print("   请运行：pip install fastapi uvicorn")
        return 1
    except Exception as e:
        print(f"\n❌ Web UI 启动失败：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
