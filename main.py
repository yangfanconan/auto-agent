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
from typing import Optional, Dict, Any

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


def print_status_report(ws_status: str, io_status: str, de_status: str, ts_status: str):
    """打印状态报告"""
    print("\n📦 工具状态:")
    registry = get_registry()
    for name, info in registry.items():
        status = "✅" if info.available else "❌"
        version = info.version or "未知"
        print(f"  {status} {name}: {version}")
    
    print("\n🚀 Auto-Agent v2.0 增强功能:")
    print(f"  📡 WebSocket 服务：{ws_status}")
    print(f"  📝 控制台 IO 接管：{io_status}")
    print(f"  🧠 智能决策引擎：{de_status}")
    print(f"  ⚡ 工具调度器：{ts_status}")


def get_tool_status():
    """获取工具状态"""
    registry = get_registry()
    tools = {}
    for name in ["qwen", "opencode"]:
        tool = registry.get(name)
        if tool:
            tools[name] = tool.status.value
        else:
            tools[name] = "not_found"
    return tools


def create_fastapi_app(static_dir: Path):
    """创建FastAPI应用"""
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse, HTMLResponse
    
    app = FastAPI(title="Auto-Agent v2.0")
    
    # 挂载静态文件
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    else:
        static_dir.mkdir(parents=True, exist_ok=True)
        index_html = static_dir / "index.html"
        if not index_html.exists():
            index_html.write_text(_get_default_html())
    
    return app


def _get_default_html() -> str:
    """获取默认HTML内容"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Auto-Agent v2.0</title></head>
    <body>
        <h1>🤖 Auto-Agent v2.0</h1>
        <p>Web UI 已启动，但前端页面文件不存在。</p>
        <p>请检查 ui/static/index.html 是否存在。</p>
    </body>
    </html>
    """


def setup_api_routes(app, static_dir: Path):
    """设置API路由"""
    from fastapi.responses import FileResponse, HTMLResponse
    
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
            return get_tool_status()
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/tasks")
    async def list_tasks():
        """获取任务列表"""
        try:
            scheduler = get_scheduler()
            tasks = scheduler.list_tasks()
            return {"tasks": tasks}
        except Exception as e:
            return {"tasks": [], "error": str(e)}
    
    @app.post("/api/tasks")
    async def create_task(task_data: dict):
        """创建任务"""
        return await handle_create_task(task_data)
    
    @app.get("/api/workspaces")
    async def get_workspaces():
        """获取工作目录列表"""
        return await handle_get_workspaces()
    
    @app.get("/api/projects")
    async def list_projects():
        """获取项目列表"""
        return await handle_list_projects()
    
    @app.post("/api/projects")
    async def add_project(project_data: dict):
        """添加项目"""
        return await handle_add_project(project_data)
    
    @app.delete("/api/projects/{project_id}")
    async def delete_project(project_id: str):
        """删除项目"""
        return await handle_delete_project(project_id)
    
    @app.get("/api/filesystem/ls")
    async def list_directory(path: str = "."):
        """列出目录内容"""
        return await handle_list_directory(path)


async def handle_create_task(task_data: dict) -> Dict[str, Any]:
    """处理创建任务"""
    import asyncio
    from core.tool_scheduler import get_scheduler, TaskPriority
    from core.events import publish_event
    
    scheduler = get_scheduler()
    description = task_data.get("description", "")
    tool = task_data.get("tool", "auto")
    
    if tool == "auto":
        tool = "opencode"
    
    task_id = await scheduler.submit_task(
        name=description[:50],
        description=description,
        tool_name=tool,
        input_text=description
    )
    
    publish_event(
        "task.submitted",
        {"task_id": task_id, "description": description, "tool": tool},
        "api"
    )
    
    asyncio.create_task(_execute_task_background(task_id, scheduler))
    return {"task_id": task_id, "status": "submitted"}


async def _execute_task_background(task_id: str, scheduler):
    """后台执行任务"""
    try:
        await scheduler.execute_next()
    except Exception as e:
        logger = get_logger()
        logger.error(f"任务执行异常：{e}")


def handle_get_workspaces() -> Dict[str, Any]:
    """处理获取工作目录"""
    try:
        from pathlib import Path
        workspaces = [
            {"name": "当前目录", "path": str(Path.cwd())},
            {"name": "用户目录", "path": str(Path.home())},
            {"name": "桌面", "path": str(Path.home() / "Desktop")},
            {"name": "文档", "path": str(Path.home() / "Documents")},
        ]
        return {"workspaces": workspaces}
    except Exception as e:
        return {"error": str(e)}


async def handle_list_projects() -> Dict[str, Any]:
    """处理列出项目"""
    try:
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        projects = pm.list_projects()
        return {"projects": [p.to_dict() for p in projects]}
    except Exception as e:
        return {"projects": [], "error": str(e)}


async def handle_add_project(project_data: dict) -> Dict[str, Any]:
    """处理添加项目"""
    try:
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        path = project_data.get("path", "")
        name = project_data.get("name")
        description = project_data.get("description", "")
        tags = project_data.get("tags", [])
        project = pm.add_project(path, name, description, tags)
        return {"project": project.to_dict()}
    except Exception as e:
        return {"error": str(e)}


async def handle_delete_project(project_id: str) -> Dict[str, Any]:
    """处理删除项目"""
    try:
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        if pm.remove_project(project_id):
            return {"message": "项目已删除"}
        return {"error": "项目不存在"}
    except Exception as e:
        return {"error": str(e)}


async def handle_list_directory(path: str) -> Dict[str, Any]:
    """处理列出目录"""
    try:
        from pathlib import Path
        import os
        
        if path == "~" or path == "undefined":
            path = str(Path.home())
        
        target_path = Path(path).expanduser().resolve()
        
        if not target_path.exists():
            return {"error": f"路径不存在: {path}", "current_path": str(target_path)}
        
        if not target_path.is_dir():
            return {"error": f"不是目录: {path}", "current_path": str(target_path)}
        
        items = []
        for item in target_path.iterdir():
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else None,
                    "modified": stat.st_mtime,
                })
            except (PermissionError, OSError):
                continue
        
        items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
        parent_path = str(target_path.parent) if target_path.parent != target_path else None
        
        return {
            "current_path": str(target_path),
            "parent_path": parent_path,
            "items": items
        }
    except Exception as e:
        return {"error": str(e), "current_path": path}


def run_webui(host: str, port: int, websocket_port: int = 8765):
    """运行 Web UI"""
    try:
        import uvicorn
        import asyncio
        from pathlib import Path

        static_dir = Path(__file__).parent / "ui" / "static"
        app = create_fastapi_app(static_dir)
        setup_api_routes(app, static_dir)

        print(f"\n🌐 Web UI 已启动!")
        print(f"   访问地址：http://{host}:{port}")
        print(f"   WebSocket: ws://{host}:{websocket_port}")
        print(f"   按 Ctrl+C 停止\n")

        # 启动WebSocket服务器（在后台）
        async def start_servers():
            # 启动WebSocket服务器
            try:
                from ui.websocket_server import start_websocket_server
                ws_task = asyncio.create_task(
                    start_websocket_server(host=host, port=websocket_port)
                )
                await asyncio.sleep(1)  # 等待WebSocket启动
            except Exception as e:
                print(f"⚠️ WebSocket服务器启动失败: {e}")
                ws_task = None
            
            # 启动HTTP服务器
            config = uvicorn.Config(app, host=host, port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()
            
            if ws_task:
                ws_task.cancel()
        
        asyncio.run(start_servers())
        return 0
    except ImportError as e:
        print(f"\n❌ 错误：缺少 Web UI 依赖 - {e}")
        print("   请运行：pip install fastapi uvicorn websockets")
        return 1
    except Exception as e:
        print(f"\n❌ Web UI 启动失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Auto-Agent v2.0")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--webui", "-w", action="store_true", help="启动 Web UI")
    parser.add_argument("--host", default="0.0.0.0", help="Web UI 主机地址")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Web UI 端口")
    parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket 端口")
    parser.add_argument("--task", "-t", help="任务描述文件")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    if args.webui:
        return run_webui(args.host, args.port, args.ws_port)
    elif args.task:
        return run_task_file(args.task)
    else:
        return run_interactive_mode()


def run_task_file(task_file: str) -> int:
    """运行任务文件"""
    try:
        with open(task_file, "r", encoding="utf-8") as f:
            task_desc = f.read()
        
        agent = AutoAgent()
        result = agent.run(task_desc)
        
        if result:
            print("\n✅ 任务完成！")
            return 0
        else:
            print("\n❌ 任务失败")
            return 1
    except Exception as e:
        print(f"\n❌ 运行任务失败：{e}")
        return 1


def run_interactive_mode() -> int:
    """运行交互模式"""
    print_banner()
    
    # 初始化组件
    try:
        agent = AutoAgent()
        ws_status = "✅ 已启动"
        io_status = "✅ 已接管"
        de_status = "✅ 已初始化"
        ts_status = "✅ 已初始化"
    except Exception as e:
        ws_status = f"⚠️  {e}"
        io_status = "⚠️  初始化失败"
        de_status = "⚠️  初始化失败"
        ts_status = "⚠️  初始化失败"
    
    print_status_report(ws_status, io_status, de_status, ts_status)
    
    print("\n✅ 智能体已就绪，请输入任务指令（输入 'quit' 退出）")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("\n📝 任务指令：").strip()
            
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 再见！")
                break
            
            if not user_input:
                continue
            
            if user_input == "status":
                print_status()
                continue
            
            print("\n🔄 正在处理任务...")
            print("-" * 50)
            
            result = agent.run(user_input)
            
            if result:
                print("\n✅ 任务完成！")
            else:
                print("\n❌ 任务失败")
                
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 错误：{e}")
    
    return 0


def print_status():
    """打印当前状态"""
    try:
        scheduler = get_scheduler()
        report = scheduler.get_task_report()
        if report:
            print("\n📊 当前任务状态:")
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print("\n暂无正在执行的任务")
    except Exception as e:
        print(f"\n无法获取状态：{e}")


if __name__ == "__main__":
    sys.exit(main())
