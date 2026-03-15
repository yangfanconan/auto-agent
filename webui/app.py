"""
FastAPI Web 应用
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_logger, load_config, AgentConfig
from core import AutoAgent, TaskParser
from modules import EnvironmentManager, CodeGenerator, TestRunner, GitManager, DeliveryManager


logger = get_logger()


# ============ 数据模型 ============

class TaskRequest(BaseModel):
    """任务请求"""
    description: str
    workspace: Optional[str] = "."
    auto_test: bool = True
    auto_commit: bool = False
    tool: str = "opencode"  # opencode 或 qwen


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str
    created_at: str
    tool: str = "opencode"  # 添加 tool 字段


class TaskStatus(BaseModel):
    """任务状态"""
    task_id: str
    status: str  # pending, running, completed, failed
    progress: float
    subtasks: List[Dict]
    result: Optional[Dict] = None


class CommandRequest(BaseModel):
    """命令请求"""
    command: str
    args: Optional[Dict] = None


# ============ 创建应用 ============

def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Auto-Agent Web UI",
        description="全自动工程化编程智能体 Web 界面",
        version="2.0.0",
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 挂载静态文件
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # 注册路由
    register_routes(app)
    
    return app


# ============ 全局状态 ============

# 任务存储
tasks: Dict[str, Dict] = {}
# 当前智能体实例
current_agent: Optional[AutoAgent] = None


# ============ 路由 ============

def register_routes(app: FastAPI):
    """注册路由"""
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """首页"""
        return get_html_content()
    
    @app.get("/api/health")
    async def health_check():
        """健康检查"""
        return {"status": "ok", "version": "2.0.0"}
    
    @app.get("/api/tasks")
    async def list_tasks():
        """获取任务列表"""
        return {"tasks": list(tasks.values())}
    
    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str):
        """获取任务详情"""
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        return tasks[task_id]
    
    @app.post("/api/tasks", response_model=TaskResponse)
    async def create_task(request: TaskRequest):
        """创建新任务"""
        global current_agent
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 初始化智能体
        workspace = request.workspace or "."
        config = load_config()
        
        agent = AutoAgent(workspace=workspace, config=config.__dict__)
        
        # 设置模块
        agent.set_modules(
            environment=EnvironmentManager(workspace),
            code_generator=CodeGenerator(workspace),
            test_runner=TestRunner(workspace),
            git_manager=GitManager(workspace),
            delivery=DeliveryManager(workspace)
        )
        
        current_agent = agent
        
        # 创建任务记录
        task = {
            "task_id": task_id,
            "description": request.description,
            "status": "pending",
            "progress": 0,
            "workspace": workspace,
            "tool": request.tool,  # 记录使用的工具
            "auto_test": request.auto_test,
            "auto_commit": request.auto_commit,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "subtasks": [],
            "result": None,
        }
        
        tasks[task_id] = task

        # 异步执行任务
        asyncio.create_task(execute_task(task_id, request))

        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="任务已创建",
            created_at=task["created_at"],
            tool=request.tool  # 返回工具选择
        )
    
    @app.delete("/api/tasks/{task_id}")
    async def delete_task(task_id: str):
        """删除任务"""
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        del tasks[task_id]
        return {"message": "任务已删除"}
    
    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str):
        """取消任务"""
        if task_id not in tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        task = tasks[task_id]
        if task["status"] == "running":
            task["status"] = "cancelled"
            task["updated_at"] = datetime.now().isoformat()
            return {"message": "任务已取消"}
        
        raise HTTPException(status_code=400, detail="任务未运行")
    
    @app.get("/api/environment")
    async def get_environment():
        """获取环境信息"""
        env_manager = EnvironmentManager(".")
        report = env_manager.scan()
        return report.to_dict()
    
    @app.get("/api/config")
    async def get_config():
        """获取配置"""
        config = load_config()
        return {
            "name": config.name,
            "version": config.version,
            "workspace": config.workspace,
            "opencode_enabled": config.opencode.enabled,
            "qwencode_enabled": config.qwencode.enabled,
            "git_auto_commit": config.git.auto_commit,
            "test_auto_test": config.test.auto_test,
        }
    
    @app.get("/api/workspaces")
    async def get_workspaces():
        """获取可用工作目录列表"""
        import os
        from pathlib import Path
        
        # 预定义常用工作目录
        common_workspaces = [
            {"name": "当前目录", "path": str(Path.cwd())},
            {"name": "用户目录", "path": str(Path.home())},
            {"name": "桌面", "path": str(Path.home() / "Desktop")},
            {"name": "文档", "path": str(Path.home() / "Documents")},
            {"name": "代码目录", "path": str(Path.home() / "Codes")},
        ]
        
        # 扫描用户目录下的代码项目
        codes_dir = Path.home() / "Codes"
        if codes_dir.exists():
            for item in codes_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # 检查是否是项目目录
                    is_project = (
                        (item / ".git").exists() or
                        (item / "requirements.txt").exists() or
                        (item / "package.json").exists() or
                        (item / "setup.py").exists()
                    )
                    if is_project:
                        common_workspaces.append({
                            "name": f"📁 {item.name}",
                            "path": str(item),
                        })
        
        # 检查 Documents 下的项目
        docs_dir = Path.home() / "Documents"
        if docs_dir.exists():
            for item in docs_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    is_project = (item / ".git").exists()
                    if is_project:
                        common_workspaces.append({
                            "name": f"📁 {item.name}",
                            "path": str(item),
                        })
        
        return {"workspaces": common_workspaces}
    
    @app.get("/api/filesystem/ls")
    async def list_directory(path: str = "~"):
        """列出目录内容"""
        try:
            target_path = Path(path).expanduser()
            if not target_path.exists():
                return {"error": "目录不存在"}
            
            items = []
            for item in sorted(target_path.iterdir()):
                if item.name.startswith('.') and item.is_dir():
                    continue  # 跳过隐藏目录
                
                item_type = "directory" if item.is_dir() else "file"
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": item_type,
                    "is_project": item.is_dir() and (
                        (item / ".git").exists() or
                        (item / "requirements.txt").exists() or
                        (item / "package.json").exists()
                    ),
                })
            
            return {
                "current_path": str(target_path),
                "parent_path": str(target_path.parent) if target_path != target_path.parent else None,
                "items": items,
            }
        except Exception as e:
            return {"error": str(e)}
    @app.get("/api/tools")
    async def get_tools():
        """获取可用工具"""
        from adapters import list_tools
        tools = list_tools()
        return {
            "tools": [
                {
                    "id": name,
                    "name": name,
                    "available": info.get("available", False),
                    "version": info.get("version", "N/A"),
                    "description": info.get("description", ""),
                }
                for name, info in tools.items()
            ]
        }
    
    @app.post("/api/commands")
    async def execute_command(request: CommandRequest):
        """执行命令"""
        # 这里可以扩展更多命令
        return {"message": f"命令已执行：{request.command}"}
    
    # WebSocket 实时更新
    @app.websocket("/ws/tasks/{task_id}")
    async def task_websocket(websocket: WebSocket, task_id: str):
        """任务实时更新 WebSocket"""
        await websocket.accept()
        
        # 订阅事件
        from core.events import EventBus, EventType, get_event_bus
        
        event_bus = get_event_bus()
        
        async def on_task_event(event):
            """任务事件处理器"""
            if event.payload.get("task_id") == task_id:
                try:
                    await websocket.send_json({
                        "type": event.type,
                        "payload": event.payload,
                        "timestamp": event.timestamp,
                    })
                except:
                    pass
        
        async def on_progress(event):
            """进度事件处理器"""
            if event.payload.get("task_id") == task_id:
                if task_id in tasks:
                    task = tasks[task_id]
                    try:
                        await websocket.send_json({
                            "task_id": task_id,
                            "status": task["status"],
                            "progress": task["progress"],
                            "subtasks": task["subtasks"],
                            "updated_at": task["updated_at"],
                        })
                    except:
                        pass
        
        # 订阅相关事件
        event_bus.subscribe_async(EventType.TASK_PROGRESS, on_progress)
        event_bus.subscribe_async(EventType.TASK_SUBTASK_COMPLETED, on_task_event)
        event_bus.subscribe_async(EventType.TASK_COMPLETED, on_task_event)
        event_bus.subscribe_async(EventType.TASK_FAILED, on_task_event)
        
        # 订阅日志事件
        async def on_log_event(event):
            """日志事件处理器"""
            try:
                await websocket.send_json({
                    "type": "log",
                    "payload": event.payload,
                })
            except:
                pass
        
        event_bus.subscribe_async("system.log", on_log_event)
        
        try:
            # 发送初始状态
            if task_id in tasks:
                task = tasks[task_id]
                await websocket.send_json({
                    "task_id": task_id,
                    "status": task["status"],
                    "progress": task["progress"],
                    "subtasks": task["subtasks"],
                    "updated_at": task["updated_at"],
                })
            
            # 保持连接
            while True:
                await asyncio.sleep(1)
                
                # 定期发送心跳
                try:
                    await websocket.send_json({"type": "heartbeat", "timestamp": datetime.now().isoformat()})
                except:
                    break
        except WebSocketDisconnect:
            logger.info(f"WebSocket 断开：{task_id}")
        except Exception as e:
            logger.error(f"WebSocket 错误：{e}")
        finally:
            # 取消订阅
            event_bus.unsubscribe(EventType.TASK_PROGRESS, on_progress)
            event_bus.unsubscribe(EventType.TASK_SUBTASK_COMPLETED, on_task_event)
            event_bus.unsubscribe(EventType.TASK_COMPLETED, on_task_event)
            event_bus.unsubscribe(EventType.TASK_FAILED, on_task_event)
    
    @app.get("/api/events")
    async def get_events(limit: int = 100):
        """获取事件历史"""
        from core.events import get_event_bus
        event_bus = get_event_bus()
        events = event_bus.get_history(limit=limit)
        return {
            "events": [e.to_dict() for e in events],
            "stats": event_bus.get_stats(),
        }
    
    @app.get("/api/logs")
    async def get_logs(limit: int = 100):
        """获取最近日志"""
        from utils.logger import get_logger
        logger = get_logger()
        logs = logger.get_recent_logs(limit)
        return {"logs": logs}
    
    # ============ 项目管理 API ============
    
    @app.get("/api/projects")
    async def list_projects(favorite: bool = False, tag: Optional[str] = None):
        """获取项目列表"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        projects = pm.list_projects(favorite_only=favorite, tag=tag)
        return {
            "projects": [p.to_dict() for p in projects],
            "stats": pm.get_stats(),
        }
    
    @app.post("/api/projects")
    async def add_project(path: str, name: Optional[str] = None, description: str = "", tags: Optional[List[str]] = None):
        """添加项目"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        project = pm.add_project(path, name, description, tags)
        return {"project": project.to_dict(), "message": "项目已添加"}
    
    @app.get("/api/projects/{project_id}")
    async def get_project(project_id: str):
        """获取项目详情"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        project = pm.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        pm.access_project(project_id)  # 记录访问
        return {"project": project.to_dict()}
    
    @app.put("/api/projects/{project_id}")
    async def update_project(
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_favorite: Optional[bool] = None,
        notes: Optional[str] = None
    ):
        """更新项目"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        project = pm.update_project(
            project_id,
            name=name,
            description=description,
            tags=tags,
            is_favorite=is_favorite,
            notes=notes
        )
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        return {"project": project.to_dict(), "message": "项目已更新"}
    
    @app.delete("/api/projects/{project_id}")
    async def delete_project(project_id: str):
        """删除项目"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        if not pm.remove_project(project_id):
            raise HTTPException(status_code=404, detail="项目不存在")
        
        return {"message": "项目已删除"}
    
    @app.post("/api/projects/{project_id}/favorite")
    async def toggle_favorite(project_id: str):
        """切换收藏状态"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        project = pm.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        pm.update_project(project_id, is_favorite=not project.is_favorite)
        return {"message": f"已{'收藏' if not project.is_favorite else '取消收藏'}"}
    
    @app.get("/api/projects/search/{query}")
    async def search_projects(query: str):
        """搜索项目"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        projects = pm.search_projects(query)
        return {"projects": [p.to_dict() for p in projects]}
    
    @app.get("/api/projects/tags")
    async def get_tags():
        """获取所有标签"""
        from core.project_manager import get_project_manager
        pm = get_project_manager()
        return {"tags": pm.get_all_tags()}


async def execute_task(task_id: str, request: TaskRequest):
    """执行任务"""
    global current_agent, tasks

    try:
        # 更新状态为运行中
        tasks[task_id]["status"] = "running"
        tasks[task_id]["updated_at"] = datetime.now().isoformat()
        
        # 发布事件
        from core.events import publish_event, EventType
        publish_event(EventType.TASK_STARTED, {
            "task_id": task_id,
            "description": request.description,
            "tool": request.tool,
        })

        # 初始化智能体（每次任务都重新初始化，确保状态干净）
        workspace = request.workspace or "."
        from utils import load_config, AgentConfig
        from modules import EnvironmentManager, CodeGenerator, TestRunner, GitManager, DeliveryManager
        
        config = load_config()
        agent = AutoAgent(workspace=workspace, config=config.__dict__)
        
        # 设置模块
        agent.set_modules(
            environment=EnvironmentManager(workspace),
            code_generator=CodeGenerator(workspace),
            test_runner=TestRunner(workspace),
            git_manager=GitManager(workspace),
            delivery=DeliveryManager(workspace)
        )
        
        # 设置工具偏好
        if request.tool == "qwen":
            from adapters import get_tool as get_adapter_tool
            agent._code_generator.qwencode = get_adapter_tool("qwencode")
        
        current_agent = agent

        # 执行用户请求 - 这会创建新的任务计划并执行
        result = current_agent.execute(request.description)
        
        # 获取当前计划 ID（execute 方法会创建新计划）
        plan = current_agent.scheduler._current_plan
        if not plan:
            raise Exception("任务计划未创建")
        
        plan_id = plan.id

        # 更新子任务
        tasks[task_id]["subtasks"] = [t.to_dict() for t in plan.subtasks]
        tasks[task_id]["plan_id"] = plan_id
        tasks[task_id]["progress"] = 0

        # 获取详细报告
        report = current_agent.tracker.get_progress_report(plan_id)
        
        # 获取子任务详细结果
        subtask_results = []
        for subtask in plan.subtasks:
            subtask_info = subtask.to_dict()
            # 从 tracker 获取实际执行结果
            tracked_subtask = current_agent.tracker._get_subtask(plan, subtask.id)
            if tracked_subtask:
                subtask_info["status"] = tracked_subtask.status
                # 保存完整的执行结果
                if tracked_subtask.result:
                    result_str = str(tracked_subtask.result)
                    subtask_info["result"] = result_str[:2000]  # 增加长度限制到 2000 字符
                    # 提取生成的文件信息
                    if "生成的文件" in result_str:
                        subtask_info["generated_files"] = result_str.split("生成的文件:")[1].strip() if "生成的文件:" in result_str else ""
                else:
                    subtask_info["result"] = None
                subtask_info["error"] = str(tracked_subtask.error)[:1000] if tracked_subtask.error else None
                subtask_info["progress"] = tracked_subtask.progress
                subtask_info["duration"] = tracked_subtask.actual_duration
            subtask_results.append(subtask_info)

        # 更新任务
        tasks[task_id]["status"] = "completed" if result.get("success", False) else "failed"
        tasks[task_id]["progress"] = report.get("overall_progress", 100)
        tasks[task_id]["result"] = {
            "success": result.get("success", False),
            "report": report,
            "subtasks": subtask_results,
            "briefing": current_agent.get_briefing(plan_id),
            "generated_code": None,  # 后续可以提取生成的代码
        }
        tasks[task_id]["tool"] = request.tool  # 保存使用的工具
        tasks[task_id]["updated_at"] = datetime.now().isoformat()

        # 发布完成事件
        publish_event(EventType.TASK_COMPLETED, {
            "task_id": task_id,
            "success": result.get("success", False),
            "report": report,
            "tool": request.tool,
        })

        logger.info(f"任务完成：{task_id}, 结果：{result}")

    except Exception as e:
        logger.error(f"任务执行失败：{e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["result"] = {"error": str(e)}

    tasks[task_id]["updated_at"] = datetime.now().isoformat()


# ============ HTML 页面 ============

def get_html_content() -> str:
    """获取 HTML 内容"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Auto-Agent v2.0 - Web UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header {
            text-align: center;
            padding: 40px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        header h1 {
            font-size: 2.5em;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        header p { color: #888; }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 24px;
            margin: 20px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h2 { margin-bottom: 16px; color: #00d9ff; }
        .form-group { margin-bottom: 16px; }
        label { display: block; margin-bottom: 8px; color: #aaa; }
        textarea, input, select {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 14px;
        }
        textarea { min-height: 120px; resize: vertical; }
        button {
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            color: #1a1a2e;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: scale(1.05); }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .task-list { margin-top: 20px; }
        .task-item {
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            padding: 16px;
            margin: 12px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .task-info { flex: 1; }
        .task-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        .status-pending { background: #666; }
        .status-running { background: #00d9ff; color: #000; }
        .status-completed { background: #00ff88; color: #000; }
        .status-failed { background: #ff4757; color: #fff; }
        .progress-bar {
            height: 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #00ff88);
            transition: width 0.3s;
        }
        .checkbox-group {
            display: flex;
            gap: 24px;
            margin-top: 12px;
        }
        .checkbox-group label {
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
        }
        .checkbox-group input { width: auto; }
        #logOutput {
            background: #0d1117;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 16px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
            max-height: 400px;
            overflow-y: auto;
        }
        .log-line { margin: 4px 0; }
        .log-info { color: #00d9ff; }
        .log-success { color: #00ff88; }
        .log-error { color: #ff4757; }
        .log-warning { color: #ffa502; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 20px;
            text-align: center;
        }
        .stat-value { font-size: 2em; font-weight: bold; color: #00d9ff; }
        .stat-label { color: #888; margin-top: 8px; }
        .footer {
            text-align: center;
            padding: 40px 0;
            color: #666;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Auto-Agent v2.0</h1>
            <p>全自动工程化编程智能体 - Web 界面</p>
        </header>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="totalTasks">0</div>
                <div class="stat-label">总任务数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="completedTasks">0</div>
                <div class="stat-label">已完成</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="runningTasks">0</div>
                <div class="stat-label">运行中</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="failedTasks">0</div>
                <div class="stat-label">失败</div>
            </div>
        </div>
        
        <div class="card">
            <h2>📝 创建新任务</h2>
            <div class="form-group">
                <label>任务描述</label>
                <textarea id="taskDescription" placeholder="例如：用 Python 写一个快速排序算法，包含单元测试"></textarea>
            </div>
            <div class="form-group">
                <label>📂 工作目录</label>
                <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                    <select id="workspaceSelect" onchange="onWorkspaceSelect()" style="flex: 1;">
                        <option value="">选择常用目录...</option>
                    </select>
                    <button onclick="browseWorkspace()" style="padding: 12px 16px;">📁 浏览</button>
                </div>
                <input type="text" id="workspace" value="." placeholder="或手动输入路径">
                <div id="workspaceInfo" style="margin-top: 8px; font-size: 13px; color: #888;"></div>
            </div>
            <div class="form-group">
                <label>🔧 选择工具</label>
                <select id="toolSelect">
                    <option value="opencode">Opencode (代码生成核心)</option>
                    <option value="qwen">Qwen (通义千问)</option>
                </select>
            </div>
            <div class="checkbox-group">
                <label>
                    <input type="checkbox" id="autoTest" checked>
                    自动测试
                </label>
                <label>
                    <input type="checkbox" id="autoCommit">
                    自动提交 Git
                </label>
            </div>
            <button onclick="createTask()" style="margin-top: 16px;">🚀 开始执行</button>
        </div>
        
        <!-- 目录浏览对话框 -->
        <div id="browseDialog" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center;">
            <div style="background: #1a1a2e; border-radius: 12px; padding: 24px; max-width: 600px; width: 90%; max-height: 80vh; overflow: auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="margin: 0;">📁 选择工作目录</h3>
                    <button onclick="closeBrowseDialog()" style="padding: 4px 12px; background: transparent; border: 1px solid rgba(255,255,255,0.2);">✕</button>
                </div>
                <div id="breadcrumb" style="margin-bottom: 16px; color: #00d9ff; font-size: 13px;"></div>
                <div id="fileList" style="display: flex; flex-direction: column; gap: 8px;">
                    <!-- 动态生成 -->
                </div>
                <div style="margin-top: 16px; display: flex; gap: 8px;">
                    <button onclick="confirmWorkspace()" style="flex: 1;">确认选择</button>
                    <button onclick="closeBrowseDialog()" style="flex: 1; background: transparent; border: 1px solid rgba(255,255,255,0.2);">取消</button>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>📁 项目管理</h2>
            <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                <input type="text" id="projectSearch" placeholder="🔍 搜索项目..." oninput="searchProjects(this.value)" style="flex: 1;">
                <button onclick="showAddProjectDialog()" style="padding: 12px 16px;">➕ 添加项目</button>
            </div>
            <div style="display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;">
                <button onclick="loadProjects()" style="padding: 8px 12px; background: rgba(0,217,255,0.2);">全部</button>
                <button onclick="loadProjects(true)" style="padding: 8px 12px; background: rgba(255,165,2,0.2);">⭐ 收藏</button>
                <div id="tagFilters" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
            </div>
            <div id="projectList" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
                <!-- 动态生成 -->
            </div>
        </div>
        
        <!-- 添加项目对话框 -->
        <div id="addProjectDialog" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 1000; align-items: center; justify-content: center;">
            <div style="background: #1a1a2e; border-radius: 12px; padding: 24px; max-width: 500px; width: 90%;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="margin: 0;">➕ 添加项目</h3>
                    <button onclick="closeAddProjectDialog()" style="padding: 4px 12px; background: transparent; border: 1px solid rgba(255,255,255,0.2);">✕</button>
                </div>
                <div class="form-group">
                    <label>项目路径</label>
                    <div style="display: flex; gap: 8px;">
                        <input type="text" id="newProjectPath" placeholder="/path/to/project">
                        <button onclick="browseForProject()" style="padding: 12px;">📁</button>
                    </div>
                </div>
                <div class="form-group">
                    <label>项目名称</label>
                    <input type="text" id="newProjectName" placeholder="自动识别">
                </div>
                <div class="form-group">
                    <label>描述</label>
                    <textarea id="newProjectDesc" placeholder="项目描述..." style="min-height: 80px;"></textarea>
                </div>
                <div class="form-group">
                    <label>标签（逗号分隔）</label>
                    <input type="text" id="newProjectTags" placeholder="python, web, api">
                </div>
                <div style="display: flex; gap: 8px; margin-top: 16px;">
                    <button onclick="confirmAddProject()" style="flex: 1;">添加</button>
                    <button onclick="closeAddProjectDialog()" style="flex: 1; background: transparent; border: 1px solid rgba(255,255,255,0.2);">取消</button>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>📋 任务列表</h2>
            <div id="taskList" class="task-list">
                <p style="color: #666; text-align: center;">暂无任务</p>
            </div>
        </div>

        <div class="card">
            <h2>📊 执行日志</h2>
            <div id="logOutput">
                <p style="color: #666;">等待任务执行...</p>
            </div>
        </div>
        
        <footer class="footer">
            <p>Auto-Agent v2.0.0 | Powered by FastAPI & Vue.js</p>
        </footer>
    </div>
    
    <script>
        let tasks = {};
        let wsConnections = {};
        let selectedWorkspace = ".";
        let currentBrowsePath = "~";
        
        // 加载工作目录列表
        async function loadWorkspaces() {
            try {
                const response = await fetch('/api/workspaces');
                const data = await response.json();
                const select = document.getElementById('workspaceSelect');
                
                select.innerHTML = '<option value="">选择常用目录...</option>' + 
                    data.workspaces.map(w => `
                        <option value="${w.path}">${w.name}</option>
                    `).join('');
                
                if (data.workspaces.length > 0) {
                    document.getElementById('workspaceInfo').innerHTML = 
                        `发现 ${data.workspaces.length} 个工作目录`;
                }
            } catch (error) {
                console.error('加载工作目录失败:', error);
            }
        }
        
        // 工作目录选择
        function onWorkspaceSelect() {
            const select = document.getElementById('workspaceSelect');
            if (select.value) {
                document.getElementById('workspace').value = select.value;
                selectedWorkspace = select.value;
            }
        }
        
        // 浏览目录
        async function browseWorkspace() {
            document.getElementById('browseDialog').style.display = 'flex';
            currentBrowsePath = document.getElementById('workspace').value || "~";
            await loadDirectory(currentBrowsePath);
        }
        
        // 关闭浏览对话框
        function closeBrowseDialog() {
            document.getElementById('browseDialog').style.display = 'none';
        }
        
        // 加载目录内容
        async function loadDirectory(path) {
            try {
                const response = await fetch(`/api/filesystem/ls?path=${encodeURIComponent(path)}`);
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('fileList').innerHTML = 
                        `<div style="color: #ff4757;">${data.error}</div>`;
                    return;
                }
                
                currentBrowsePath = data.current_path;
                
                // 更新面包屑
                document.getElementById('breadcrumb').textContent = data.current_path;
                
                // 生成文件列表
                const items = data.items;
                const fileList = document.getElementById('fileList');
                
                let html = '';
                
                // 父目录
                if (data.parent_path) {
                    html += `
                        <div onclick="loadDirectory('${data.parent_path}')" 
                             style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                            <span>📁</span>
                            <span>.. (父目录)</span>
                        </div>
                    `;
                }
                
                // 目录
                items.filter(i => i.type === 'directory').forEach(item => {
                    const icon = item.is_project ? '📦' : '📁';
                    html += `
                        <div onclick="loadDirectory('${item.path}')" 
                             style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px;">
                            <span>${icon}</span>
                            <span>${item.name}</span>
                            ${item.is_project ? '<span style="font-size: 11px; color: #00d9ff; margin-left: auto;">项目</span>' : ''}
                        </div>
                    `;
                });
                
                // 文件
                items.filter(i => i.type === 'file').slice(0, 50).forEach(item => {
                    html += `
                        <div style="padding: 12px; background: rgba(255,255,255,0.02); border-radius: 8px; display: flex; align-items: center; gap: 8px; color: #888;">
                            <span>📄</span>
                            <span>${item.name}</span>
                        </div>
                    `;
                });
                
                fileList.innerHTML = html;
                
            } catch (error) {
                console.error('加载目录失败:', error);
            }
        }
        
        // 确认选择
        function confirmWorkspace() {
            document.getElementById('workspace').value = currentBrowsePath;
            selectedWorkspace = currentBrowsePath;
            closeBrowseDialog();
            addLog(`已选择工作目录：${currentBrowsePath}`, 'info');
        }
        
        // 创建 WebSocket 连接
        function connectWebSocket(taskId) {
            if (wsConnections[taskId]) return;
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(`${protocol}//${window.location.host}/ws/tasks/${taskId}`);
            
            ws.onopen = () => {
                addLog(`WebSocket 已连接：${taskId}`, 'info');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                // 处理日志消息
                if (data.type === 'log') {
                    const log = data.payload;
                    const typeMap = {
                        'ERROR': 'error',
                        'WARNING': 'warning',
                        'INFO': 'info',
                        'DEBUG': 'info',
                    };
                    addLog(`[${log.time || new Date(log.timestamp * 1000).toLocaleTimeString()}] ${log.message}`, typeMap[log.level] || 'info');
                    return;
                }
                
                if (data.type === 'heartbeat') return;
                
                // 更新任务状态
                if (data.task_id) {
                    if (tasks[data.task_id]) {
                        tasks[data.task_id].status = data.status;
                        tasks[data.task_id].progress = data.progress;
                        tasks[data.task_id].subtasks = data.subtasks;
                        tasks[data.task_id].updated_at = data.updated_at;
                        renderTasks();
                        updateStats();
                    }
                }
                
                // 显示事件通知
                if (data.type) {
                    const typeMap = {
                        'task.completed': 'success',
                        'task.failed': 'error',
                        'task.progress': 'info',
                        'task.subtask.completed': 'success',
                    };
                    addLog(`${data.type}: ${JSON.stringify(data.payload)}`, typeMap[data.type] || 'info');
                }
            };
            
            ws.onclose = () => {
                addLog(`WebSocket 已断开：${taskId}`, 'warning');
                delete wsConnections[taskId];
            };
            
            ws.onerror = (error) => {
                addLog(`WebSocket 错误：${taskId}`, 'error');
            };
            
            wsConnections[taskId] = ws;
        }
        
        // 加载工具状态
        async function loadTools() {
            try {
                const response = await fetch('/api/tools');
                const data = await response.json();
                const select = document.getElementById('toolSelect');
                
                select.innerHTML = data.tools
                    .filter(t => t.available)
                    .map(t => `
                        <option value="${t.id}">${t.id === 'opencode' ? '⚡' : '🤖'} ${t.name} (${t.version})</option>
                    `).join('');
                
                addLog(`可用工具：${data.tools.map(t => t.name).join(', ')}`, 'info');
            } catch (error) {
                addLog(`加载工具失败：${error.message}`, 'warning');
            }
        }
        
        // 查看任务详情
        function viewTask(taskId) {
            connectWebSocket(taskId);
            addLog(`查看任务：${taskId}`, 'info');
        }
        
        // 加载事件历史
        async function loadEvents() {
            try {
                const response = await fetch('/api/events?limit=20');
                const data = await response.json();

                const output = document.getElementById('logOutput');
                const events = data.events.reverse();

                output.innerHTML = events.map(e => {
                    const time = new Date(e.timestamp * 1000).toLocaleTimeString();
                    const typeMap = {
                        'task.completed': 'log-success',
                        'task.failed': 'log-error',
                        'task.progress': 'log-info',
                        'task.subtask.completed': 'log-success',
                    };
                    const className = typeMap[e.type] || 'log-info';
                    return `<div class="log-line ${className}">[${time}] ${e.type}: ${JSON.stringify(e.payload)}</div>`;
                }).join('');

                output.scrollTop = output.scrollHeight;
            } catch (error) {
                console.error('加载事件失败:', error);
            }
        }

        // 加载日志
        async function loadLogs() {
            try {
                const response = await fetch('/api/logs?limit=50');
                const data = await response.json();
                
                const output = document.getElementById('logOutput');
                const logs = data.logs;
                
                if (logs.length === 0) return;
                
                const logHtml = logs.map(log => {
                    const time = log.time || new Date(log.timestamp * 1000).toLocaleTimeString();
                    const typeMap = {
                        'ERROR': 'log-error',
                        'WARNING': 'log-warning',
                        'INFO': 'log-info',
                        'DEBUG': 'log-info',
                    };
                    const className = typeMap[log.level] || 'log-info';
                    return `<div class="log-line ${className}">[${time}] ${log.message}</div>`;
                }).join('');
                
                // 如果有日志，替换事件显示（事件和日志二选一）
                if (logs.length > 0) {
                    output.innerHTML = logHtml;
                    output.scrollTop = output.scrollHeight;
                }
            } catch (error) {
                console.error('加载日志失败:', error);
            }
        }

        // ========== 项目管理功能 ==========

        // 加载项目列表
        async function loadProjects(favoriteOnly = false) {
            try {
                const response = await fetch(`/api/projects?favorite=${favoriteOnly}`);
                const data = await response.json();

                const projectList = document.getElementById('projectList');
                const projects = data.projects;

                if (projects.length === 0) {
                    projectList.innerHTML = '<p style="color: #666; grid-column: 1/-1; text-align: center;">暂无项目，点击右上角添加</p>';
                    return;
                }

                projectList.innerHTML = projects.map(p => {
                    const typeIcon = p.metadata?.has_python ? '🐍' :
                                    p.metadata?.has_node ? '📦' :
                                    p.metadata?.has_rust ? '🦀' :
                                    p.metadata?.has_go ? '🐹' : '📁';
                    const typeText = p.metadata?.type || 'unknown';

                    return `
                        <div class="project-card" style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px; border: 1px solid ${p.is_favorite ? 'rgba(255,165,2,0.5)' : 'rgba(255,255,255,0.1)'};">
                            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <span style="font-size: 24px;">${typeIcon}</span>
                                    <div>
                                        <div style="font-weight: 600;">${p.name}</div>
                                        <div style="font-size: 12px; color: #888;">${typeText}</div>
                                    </div>
                                </div>
                                <button onclick="toggleFavorite('${p.id}')" style="background: transparent; border: none; font-size: 18px; cursor: pointer;">
                                    ${p.is_favorite ? '⭐' : '☆'}
                                </button>
                            </div>
                            <div style="font-size: 13px; color: #888; margin-bottom: 8px;">${p.path}</div>
                            ${p.description ? `<div style="font-size: 13px; color: #aaa; margin-bottom: 8px;">${p.description}</div>` : ''}
                            <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 12px;">
                                ${(p.tags || []).map(t => `<span style="background: rgba(0,217,255,0.2); color: #00d9ff; padding: 2px 8px; border-radius: 4px; font-size: 11px;">${t}</span>`).join('')}
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button onclick="selectProjectAsWorkspace('${p.path}')" style="flex: 1; padding: 6px; font-size: 12px;">设为工作目录</button>
                                <button onclick="deleteProject('${p.id}')" style="padding: 6px 12px; font-size: 12px; background: rgba(255,71,87,0.2); color: #ff4757;">删除</button>
                            </div>
                        </div>
                    `;
                }).join('');

                // 加载标签
                loadProjectTags();

            } catch (error) {
                console.error('加载项目失败:', error);
            }
        }

        // 加载标签过滤器
        async function loadProjectTags() {
            try {
                const response = await fetch('/api/projects/tags');
                const data = await response.json();
                const tagFilters = document.getElementById('tagFilters');

                tagFilters.innerHTML = data.tags.map(t => `
                    <button onclick="filterByTag('${t}')" style="padding: 4px 8px; font-size: 11px; background: rgba(0,217,255,0.1); border: 1px solid rgba(0,217,255,0.3); border-radius: 4px; color: #00d9ff; cursor: pointer;">#${t}</button>
                `).join('');
            } catch (error) {
                console.error('加载标签失败:', error);
            }
        }

        // 按标签过滤
        function filterByTag(tag) {
            loadProjects(false, tag);
        }

        // 搜索项目
        async function searchProjects(query) {
            if (!query) {
                loadProjects();
                return;
            }

            try {
                const response = await fetch(`/api/projects/search/${encodeURIComponent(query)}`);
                const data = await response.json();

                const projectList = document.getElementById('projectList');
                const projects = data.projects;

                if (projects.length === 0) {
                    projectList.innerHTML = '<p style="color: #666; grid-column: 1/-1; text-align: center;">未找到匹配的项目</p>';
                    return;
                }

                // 复用渲染逻辑
                projectList.innerHTML = projects.map(p => renderProjectCard(p)).join('');
            } catch (error) {
                console.error('搜索失败:', error);
            }
        }

        // 显示添加项目对话框
        function showAddProjectDialog() {
            document.getElementById('addProjectDialog').style.display = 'flex';
        }

        // 关闭添加项目对话框
        function closeAddProjectDialog() {
            document.getElementById('addProjectDialog').style.display = 'none';
        }

        // 浏览选择项目路径
        async function browseForProject() {
            document.getElementById('browseDialog').style.display = 'flex';
            currentBrowsePath = document.getElementById('newProjectPath').value || "~";
            await loadDirectory(currentBrowsePath);

            // 修改确认函数
            window.confirmWorkspace = function() {
                document.getElementById('newProjectPath').value = currentBrowsePath;
                closeBrowseDialog();
            };
        }

        // 确认添加项目
        async function confirmAddProject() {
            const path = document.getElementById('newProjectPath').value;
            const name = document.getElementById('newProjectName').value;
            const description = document.getElementById('newProjectDesc').value;
            const tags = document.getElementById('newProjectTags').value.split(',').map(t => t.trim()).filter(t => t);

            if (!path) {
                alert('请输入项目路径');
                return;
            }

            try {
                const params = new URLSearchParams({ path });
                if (name) params.append('name', name);
                if (description) params.append('description', description);
                if (tags.length) params.append('tags', JSON.stringify(tags));

                const response = await fetch(`/api/projects?${params}`, {
                    method: 'POST',
                });

                const data = await response.json();
                addLog(`项目已添加：${data.project.name}`, 'success');
                closeAddProjectDialog();
                loadProjects();

                // 清空表单
                document.getElementById('newProjectPath').value = '';
                document.getElementById('newProjectName').value = '';
                document.getElementById('newProjectDesc').value = '';
                document.getElementById('newProjectTags').value = '';

            } catch (error) {
                addLog(`添加项目失败：${error.message}`, 'error');
            }
        }

        // 切换收藏
        async function toggleFavorite(projectId) {
            try {
                const response = await fetch(`/api/projects/${projectId}/favorite`, {
                    method: 'POST',
                });
                await response.json();
                loadProjects();
            } catch (error) {
                addLog(`操作失败：${error.message}`, 'error');
            }
        }

        // 删除项目
        async function deleteProject(projectId) {
            if (!confirm('确定要删除这个项目吗？')) return;

            try {
                const response = await fetch(`/api/projects/${projectId}`, {
                    method: 'DELETE',
                });
                await response.json();
                addLog('项目已删除', 'info');
                loadProjects();
            } catch (error) {
                addLog(`删除失败：${error.message}`, 'error');
            }
        }

        // 选择项目为工作目录
        function selectProjectAsWorkspace(path) {
            document.getElementById('workspace').value = path;
            selectedWorkspace = path;
            addLog(`已设置工作目录：${path}`, 'info');
        }

        // 渲染项目卡片（复用）
        function renderProjectCard(p) {
            const typeIcon = p.metadata?.has_python ? '🐍' :
                            p.metadata?.has_node ? '📦' :
                            p.metadata?.has_rust ? '🦀' :
                            p.metadata?.has_go ? '🐹' : '📁';
            // ... 复用上面的渲染逻辑
        }
        
        // 创建任务
        async function createTask() {
            const description = document.getElementById('taskDescription').value;
            const workspace = document.getElementById('workspace').value;
            const tool = document.getElementById('toolSelect').value;
            const autoTest = document.getElementById('autoTest').checked;
            const autoCommit = document.getElementById('autoCommit').checked;
            
            if (!description.trim()) {
                alert('请输入任务描述');
                return;
            }
            
            try {
                const response = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        description,
                        workspace,
                        tool,
                        auto_test: autoTest,
                        auto_commit: autoCommit
                    })
                });
                
                const data = await response.json();
                addLog(`任务已创建：${data.task_id} (使用 ${data.tool || 'opencode'})`, 'info');
                
                // 连接 WebSocket
                connectWebSocket(data.task_id);
                
                loadTasks();
            } catch (error) {
                addLog(`创建任务失败：${error.message}`, 'error');
            }
        }
        
        // 加载任务列表
        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                tasks = data.tasks.reduce((acc, task) => {
                    acc[task.task_id] = task;
                    return acc;
                }, {});
                renderTasks();
                updateStats();
            } catch (error) {
                console.error('加载任务失败:', error);
            }
        }
        
        // 渲染任务列表
        function renderTasks() {
            const container = document.getElementById('taskList');
            const taskArray = Object.values(tasks);
            
            if (taskArray.length === 0) {
                container.innerHTML = '<p style="color: #666; text-align: center;">暂无任务</p>';
                return;
            }
            
            container.innerHTML = taskArray.map(task => {
                let dateStr = '未知时间';
                try {
                    const date = new Date(task.created_at);
                    dateStr = date.toLocaleString('zh-CN');
                } catch (e) {
                    dateStr = task.created_at || '未知时间';
                }

                const toolBadge = task.tool ? `
                    <span style="background: rgba(0,217,255,0.2); color: #00d9ff; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px;">
                        ${task.tool === 'qwen' || task.tool === 'qwencode' ? '🤖 Qwen' : '⚡ Opencode'}
                    </span>
                ` : '';
                
                // 子任务状态摘要
                const subtasks = task.subtasks || [];
                const completedCount = subtasks.filter(s => s.status === 'completed').length;
                const subtaskSummary = subtasks.length > 0 ? `
                    <div style="font-size: 12px; color: #888; margin-top: 8px;">
                        子任务：${completedCount}/${subtasks.length} 完成
                    </div>
                ` : '';
                
                // 子任务详情
                const subtaskDetails = subtasks.length > 0 ? `
                    <div style="margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px;">
                        <div style="font-size: 12px; color: #aaa; margin-bottom: 8px;">子任务执行详情:</div>
                        ${subtasks.map(s => {
                            const statusIcon = s.status === 'completed' ? '✅' : s.status === 'failed' ? '❌' : s.status === 'in_progress' ? '🔄' : '⏳';
                            const duration = s.duration ? `(${s.duration.toFixed(1)}秒)` : '';
                            return `
                                <div style="background: rgba(255,255,255,0.03); border-radius: 4px; padding: 8px; margin-bottom: 8px;">
                                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                        <span>${statusIcon}</span>
                                        <span style="font-weight: 600; font-size: 13px;">${s.name}</span>
                                        <span style="font-size: 11px; color: #666;">${duration}</span>
                                    </div>
                                    ${s.result ? `
                                        <div style="font-size: 12px; color: #888; margin-top: 4px; white-space: pre-wrap; max-height: 200px; overflow: auto; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 4px;">${s.result}</div>
                                    ` : ''}
                                    ${s.error ? `
                                        <div style="font-size: 12px; color: #ff4757; margin-top: 4px; background: rgba(255,71,87,0.1); padding: 6px; border-radius: 4px;">❌ ${s.error}</div>
                                    ` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                ` : '';
                
                // 结果预览
                const resultPreview = task.result?.briefing ? `
                    <div style="background: rgba(0,255,136,0.1); border-left: 3px solid #00ff88; padding: 8px; margin-top: 8px; font-size: 12px; color: #aaa; max-height: 150px; overflow: auto;">
                        <div style="font-weight: 600; margin-bottom: 4px;">📊 任务简报:</div>
                        ${task.result.briefing}
                    </div>
                ` : (task.result?.error ? `
                    <div style="background: rgba(255,71,87,0.1); border-left: 3px solid #ff4757; padding: 8px; margin-top: 8px; font-size: 12px; color: #ff4757;">
                        ❌ ${task.result.error}
                    </div>
                ` : '');

                return `
                <div class="task-item" style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                    <div class="task-info">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <strong style="font-size: 15px;">${escapeHtml(task.description)}</strong>
                                ${toolBadge}
                            </div>
                            <span class="task-status status-${task.status}" style="padding: 4px 12px; border-radius: 12px; font-size: 12px;">${task.status}</span>
                        </div>
                        <div style="color: #888; font-size: 12px; margin-top: 4px;">
                            ${dateStr} | 工具：${task.tool || 'opencode'}
                        </div>
                        <div class="progress-bar" style="margin-top: 12px;">
                            <div class="progress-fill" style="width: ${task.progress || 0}%"></div>
                        </div>
                        ${subtaskSummary}
                        ${subtaskDetails}
                        ${resultPreview}
                    </div>
                </div>
                `;
            }).join('');
        }
        
        // 更新统计
        function updateStats() {
            const taskArray = Object.values(tasks);
            document.getElementById('totalTasks').textContent = taskArray.length;
            document.getElementById('completedTasks').textContent = taskArray.filter(t => t.status === 'completed').length;
            document.getElementById('runningTasks').textContent = taskArray.filter(t => t.status === 'running').length;
            document.getElementById('failedTasks').textContent = taskArray.filter(t => t.status === 'failed').length;
        }
        
        // 添加日志
        function addLog(message, type = 'info') {
            const output = document.getElementById('logOutput');
            const time = new Date().toLocaleTimeString();
            const className = `log-${type}`;
            output.innerHTML += `<div class="log-line ${className}">[${time}] ${escapeHtml(message)}</div>`;
            output.scrollTop = output.scrollHeight;
        }
        
        // HTML 转义
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // 轮询更新（降低频率，因为现在有 WebSocket）
        setInterval(loadTasks, 10000);  // 10 秒一次
        setInterval(loadEvents, 5000);   // 5 秒刷新事件
        
        // 初始加载
        loadTools();
        loadWorkspaces();  // 加载工作目录
        loadProjects();    // 加载项目
        loadTasks();
        loadLogs();        // 加载日志
        loadEvents();
        addLog('Web UI 已就绪，WebSocket 实时推送已启用', 'success');
    </script>
</body>
</html>
"""


# ============ 主入口 ============

app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
