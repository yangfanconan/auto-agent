#!/usr/bin/env python3
"""
Auto-Agent v2.0 全自动工程化编程智能体
入口文件

支持 qwencode/opencode 等工具，实现从任务解析→环境搭建→代码开发→测试→交付→Git 提交的全流程自动化

v2.0 新增功能:
- 控制台 IO 全接管
- WebSocket 实时可视化
- 双工具智能调度 (OpenCode + Qwen)
- 智能决策引擎 (预设规则 + Qwen 智能决策)
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
    from core.decision_engine import get_decision_engine
    from core.tool_scheduler import get_scheduler
except ImportError:
    from utils import get_logger, load_config, AgentConfig
    from core import AutoAgent, TaskParser
    from modules import EnvironmentManager, CodeGenerator, TestRunner, GitManager, DeliveryManager
    from adapters import get_registry, list_tools
    from core.decision_engine import get_decision_engine
    from core.tool_scheduler import get_scheduler


def print_banner():
    """打印欢迎横幅"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   Auto-Agent v2.0 全自动工程化编程智能体                  ║
║                                                           ║
║   支持 OpenCode/Qwen 双工具                               ║
║   全流程自动化：环境→开发→测试→交付→Git                   ║
║   ✨ 新增：控制台 IO 接管 | WebSocket 可视化 | 智能决策   ║
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


def print_v2_features_status(config):
    """打印 v2.0 增强功能状态"""
    print("\n🚀 Auto-Agent v2.0 增强功能:")
    
    # WebSocket 状态
    ws_enabled = getattr(config, 'websocket', None) and getattr(config.websocket, 'enabled', True)
    ws_port = getattr(config.websocket, 'port', 8765) if getattr(config, 'websocket', None) else 8765
    ws_status = f"✅ 已启用 (端口：{ws_port})" if ws_enabled else "❌ 已禁用"
    print(f"  📡 WebSocket 服务：{ws_status}")
    
    # 控制台 IO 接管状态
    io_enabled = getattr(config, 'console_io', None) and getattr(config.console_io, 'enabled', True)
    io_status = "✅ 已启用" if io_enabled else "❌ 已禁用"
    print(f"  📝 控制台 IO 接管：{io_status}")
    
    # 决策引擎状态
    try:
        decision_engine = get_decision_engine()
        print(f"  🧠 智能决策引擎：✅ 已初始化")
    except Exception as e:
        print(f"  🧠 智能决策引擎：⚠️ 初始化失败 ({e})")
    
    # 工具调度器状态
    try:
        scheduler = get_scheduler()
        print(f"  ⚡ 工具调度器：✅ 已初始化")
    except Exception as e:
        print(f"  ⚡ 工具调度器：⚠️ 初始化失败 ({e})")


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
    print(f"Qwen: {'✅ 可用' if report.qwen_available else '⚠️ 可选'}")
    
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

    parser.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket 端口（默认：8765）"
    )

    parser.add_argument(
        "--enable-console-redirect",
        action="store_true",
        help="启用控制台 IO 接管"
    )

    parser.add_argument(
        "--no-console-redirect",
        action="store_true",
        help="禁用控制台 IO 接管"
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
    
    # 打印 v2.0 增强功能状态
    print_v2_features_status(config)

    # 检测是否是后台运行（无 TTY）
    is_background = not sys.stdin.isatty()

    # 启动 WebSocket 服务（始终启用，除非明确禁用）
    enable_websocket = getattr(config, 'websocket', None) and getattr(config.websocket, 'enabled', True)
    
    # 控制台 IO 接管（后台运行时禁用）
    try:
        enable_console_redirect = getattr(config, 'console_io', None) and getattr(config.console_io, 'enabled', True) and not args.no_console_redirect
    except:
        enable_console_redirect = False

    # 后台运行时禁用控制台交互
    if is_background:
        enable_console_redirect = False
        logger.info("检测到后台运行，已禁用控制台 IO 接管")

    if args.enable_console_redirect:
        enable_console_redirect = True
    
    if args.no_console_redirect:
        enable_console_redirect = False

    websocket_port = 8765
    try:
        if hasattr(config, 'websocket') and hasattr(config.websocket, 'port'):
            websocket_port = config.websocket.port
    except:
        pass

    if args.websocket_port:
        websocket_port = args.websocket_port

    # 启动增强功能
    if enable_websocket or enable_console_redirect:
        logger.info("启动增强功能...")
        start_enhanced_features(
            enable_websocket=enable_websocket,
            enable_console_redirect=enable_console_redirect,
            websocket_port=websocket_port,
        )

    # 环境检查模式
    if args.check:
        check_environment(args.workspace)
        return 0

    # Web UI 模式
    if args.webui:
        return run_webui(args.host, args.port, websocket_port)

    # 命令模式
    if args.command:
        return run_command_mode(args.command, args.workspace, config)

    # 后台运行时跳过交互模式
    if is_background:
        logger.info("后台运行模式，已跳过交互模式")
        print("\n🔌 服务已启动，运行在后台模式")
        print(f"   WebSocket: ws://0.0.0.0:{websocket_port}")
        print(f"   使用命令模式：python main.py -c '任务描述'\n")
        # 保持运行
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return 0

    # 交互模式（默认）
    run_interactive_mode(args.workspace, config)

    return 0


def start_enhanced_features(
    enable_websocket: bool = True,
    enable_console_redirect: bool = True,
    websocket_port: int = 8765,
):
    """启动增强功能（WebSocket + 控制台 IO 接管）"""
    import asyncio
    import queue

    # 全局 WebSocket 管理器引用
    global _ws_manager

    # 启动 WebSocket 服务
    if enable_websocket:
        from ui.websocket_server import WebSocketManager

        # 创建 WebSocket 管理器
        _ws_manager = WebSocketManager(port=websocket_port)

        # 启动 WebSocket 服务器（后台线程）
        import threading
        ws_thread = threading.Thread(
            target=lambda: asyncio.run(_ws_manager.start_server()),
            daemon=True
        )
        ws_thread.start()

        print(f"\n🔌 WebSocket 服务已启动：ws://0.0.0.0:{websocket_port}")
        print(f"   连接 WebSocket 以接收实时日志\n")

    # 创建 WebSocket IO 桥接器（始终创建，用于事件转发）
    if enable_websocket:
        from ui.websocket_server import WebSocketIOBridge
        io_bridge = WebSocketIOBridge(_ws_manager)
        # 设置 WebSocket 消息处理（必须在创建 io_bridge 后立即设置）
        _ws_manager.on_message = io_bridge.handle_websocket_message
        print(f"📡 WebSocket IO 桥接器已启用")

    # 启动控制台 IO 接管
    if enable_console_redirect:
        from core.console_io import start_console_capture, IOMessage

        # 消息队列（线程安全）
        _message_queue = queue.Queue()

        # 启动控制台捕获
        def on_io_message(message: IOMessage):
            """IO 消息回调（线程安全）"""
            # 将消息放入队列，由 WebSocket 线程处理
            _message_queue.put({
                "type": "io",
                "event": message.type.value,
                "data": message.to_dict(),
            })

        start_console_capture(on_io_message)

        # 启动消息转发线程
        def message_forwarder():
            """消息转发线程：将队列中的消息发送到 WebSocket"""
            import time
            while True:
                try:
                    msg = _message_queue.get(timeout=0.1)
                    # 使用线程安全的方式调度异步任务
                    if hasattr(_ws_manager, '_broadcast_queue'):
                        try:
                            # 尝试直接放入广播队列
                            loop = None
                            try:
                                loop = asyncio.get_running_loop()
                            except RuntimeError:
                                pass

                            if loop and loop.is_running():
                                loop.call_soon_threadsafe(
                                    lambda m=msg: _ws_manager._broadcast_queue.put_nowait(m)
                                )
                        except Exception:
                            pass
                except queue.Empty:
                    continue
                except Exception as e:
                    time.sleep(0.1)

        forwarder_thread = threading.Thread(target=message_forwarder, daemon=True)
        forwarder_thread.start()

        print(f"📡 控制台 IO 接管已启用")


# 全局 WebSocket 管理器引用
_ws_manager = None


def run_webui(host: str, port: int, websocket_port: int = 8765):
    """运行 Web UI"""
    try:
        from fastapi import FastAPI
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse, HTMLResponse
        import uvicorn
        from pathlib import Path
        
        # 创建 FastAPI 应用
        app = FastAPI(title="Auto-Agent v2.0")
        
        # 静态文件目录
        static_dir = Path(__file__).parent / "ui" / "static"
        
        # 挂载静态文件
        if static_dir.exists():
            app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        else:
            static_dir.mkdir(parents=True, exist_ok=True)
            # 创建默认的 index.html
            index_html = static_dir / "index.html"
            if not index_html.exists():
                index_html.write_text("""
                <!DOCTYPE html>
                <html>
                <head><title>Auto-Agent v2.0</title></head>
                <body>
                    <h1>🤖 Auto-Agent v2.0</h1>
                    <p>Web UI 已启动，但前端页面文件不存在。</p>
                    <p>请检查 ui/static/index.html 是否存在。</p>
                </body>
                </html>
                """)
        
        # API 路由
        @app.get("/")
        async def root():
            """根路径"""
            index_path = static_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
            return HTMLResponse(content="<h1>Auto-Agent v2.0</h1><p>请访问 /static/index.html</p>")
        
        @app.get("/api/health")
        async def health():
            """健康检查"""
            return {"status": "ok", "version": "2.0"}
        
        @app.get("/api/tools/status")
        async def tools_status():
            """获取工具状态"""
            try:
                from adapters.base_tool import get_tool_registry
                registry = get_tool_registry()
                tools = {}
                for name in ["qwen", "opencode"]:
                    tool = registry.get(name)
                    if tool:
                        tools[name] = tool.status.value
                    else:
                        tools[name] = "not_found"
                return tools
            except Exception as e:
                return {"error": str(e)}
        
        @app.get("/api/tasks")
        async def list_tasks():
            """获取任务列表"""
            try:
                from core.tool_scheduler import get_scheduler
                scheduler = get_scheduler()
                return scheduler.list_tasks()
            except Exception as e:
                return {"error": str(e)}
        
        @app.post("/api/tasks")
        async def create_task(task_data: dict):
            """创建任务"""
            try:
                import asyncio
                from core.tool_scheduler import get_scheduler, TaskPriority
                from core.events import publish_event
                scheduler = get_scheduler()
                
                description = task_data.get("description", "")
                tool = task_data.get("tool", "auto")
                
                if tool == "auto":
                    tool = "opencode"
                
                # 直接使用 await（不要用 asyncio.run，会干扰现有事件循环）
                task_id = await scheduler.submit_task(
                    name=description[:50],
                    description=description,
                    tool_name=tool,
                    input_text=description
                )

                # 手动发布事件（确保事件被发布）
                publish_event(
                    "task.submitted",
                    {"task_id": task_id, "description": description, "tool": tool},
                    "api"
                )

                # 启动任务执行（后台）
                asyncio.create_task(_execute_task_background(task_id, scheduler))
                return {"task_id": task_id, "status": "submitted"}
            except Exception as e:
                import traceback
                traceback.print_exc()
                return {"error": str(e)}

        async def _execute_task_background(task_id: str, scheduler):
            """后台执行任务"""
            try:
                await scheduler.execute_next()
            except Exception as e:
                print(f"任务执行异常：{e}")

        print(f"\n🌐 Web UI 已启动!")
        print(f"   访问地址：http://{host}:{port}")
        print(f"   WebSocket: ws://{host}:{websocket_port}")
        print(f"   按 Ctrl+C 停止\n")

        uvicorn.run(app, host=host, port=port, log_level="info")
        return 0
    except ImportError as e:
        print(f"\n❌ 错误：缺少 Web UI 依赖 - {e}")
        print("   请运行：pip install fastapi uvicorn websockets")
        return 1
    except Exception as e:
        print(f"\n❌ Web UI 启动失败：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
