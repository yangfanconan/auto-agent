"""
FastAPI Web 应用 - 简化版
只提供 API 和静态文件服务
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import asyncio

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import get_logger, load_config, AgentConfig
from core import AutoAgent, TaskParser
from modules import EnvironmentManager, CodeGenerator, TestRunner, GitManager, DeliveryManager
from core.project_manager import get_project_manager

logger = get_logger()

# ============ 数据模型 ============

class TaskRequest(BaseModel):
    description: str
    workspace: Optional[str] = "."
    auto_test: bool = True
    auto_commit: bool = False
    tool: str = "opencode"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str
    created_at: str
    tool: str = "opencode"

# ============ 创建应用 ============

app = FastAPI(title="Auto-Agent Web UI")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件 - 必须先于路由注册
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

# ============ 全局状态 ============

tasks: Dict[str, Dict] = {}
current_agent: Optional[AutoAgent] = None

# ============ 路由 ============

@app.get("/")
async def root():
    """首页 - 重定向到静态页面"""
    from fastapi.responses import FileResponse
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.exists():
        return FileResponse(str(static_file))
    return {"error": "请将 index.html 放到 webui/static/ 目录"}

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}

@app.get("/api/tasks")
async def list_tasks():
    return {"tasks": list(tasks.values())}

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    return tasks[task_id]

@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest):
    global current_agent
    
    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    workspace = request.workspace or "."
    config = load_config()
    
    agent = AutoAgent(workspace=workspace, config=config.__dict__)
    agent.set_modules(
        environment=EnvironmentManager(workspace),
        code_generator=CodeGenerator(workspace),
        test_runner=TestRunner(workspace),
        git_manager=GitManager(workspace),
        delivery=DeliveryManager(workspace)
    )
    
    if request.tool == "qwen":
        from adapters import get_tool as get_adapter_tool
        agent._code_generator.qwen = get_adapter_tool("qwen")
    
    current_agent = agent
    
    task = {
        "task_id": task_id,
        "description": request.description,
        "status": "pending",
        "progress": 0,
        "workspace": workspace,
        "tool": request.tool,
        "auto_test": request.auto_test,
        "auto_commit": request.auto_commit,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "subtasks": [],
        "result": None,
    }
    
    tasks[task_id] = task
    asyncio.create_task(execute_task(task_id, request))
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        message="任务已创建",
        created_at=task["created_at"],
        tool=request.tool
    )

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    del tasks[task_id]
    return {"message": "任务已删除"}

@app.get("/api/workspaces")
async def get_workspaces():
    from pathlib import Path
    
    common_workspaces = [
        {"name": "当前目录", "path": str(Path.cwd())},
        {"name": "用户目录", "path": str(Path.home())},
        {"name": "桌面", "path": str(Path.home() / "Desktop")},
        {"name": "文档", "path": str(Path.home() / "Documents")},
        {"name": "代码目录", "path": str(Path.home() / "Codes")},
    ]
    
    codes_dir = Path.home() / "Codes"
    if codes_dir.exists():
        for item in codes_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                is_project = (
                    (item / ".git").exists() or
                    (item / "requirements.txt").exists() or
                    (item / "package.json").exists()
                )
                if is_project:
                    common_workspaces.append({"name": f"📁 {item.name}", "path": str(item)})
    
    return {"workspaces": common_workspaces}

@app.get("/api/filesystem/ls")
async def list_directory(path: str = "~"):
    try:
        from pathlib import Path
        target_path = Path(path).expanduser()
        if not target_path.exists():
            return {"error": "目录不存在"}
        
        items = []
        for item in sorted(target_path.iterdir()):
            if item.name.startswith('.') and item.is_dir():
                continue
            
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

@app.get("/api/projects")
async def list_projects():
    pm = get_project_manager()
    projects = pm.list_projects()
    return {"projects": [p.to_dict() for p in projects], "stats": pm.get_stats()}

@app.post("/api/projects")
async def add_project(path: str, name: Optional[str] = None, description: str = "", tags: Optional[str] = None):
    pm = get_project_manager()
    tag_list = []
    if tags:
        try:
            tag_list = [t.strip() for t in tags.split(',')]
        except:
            pass
    project = pm.add_project(path, name, description, tag_list)
    return {"project": project.to_dict(), "message": "项目已添加"}

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    pm = get_project_manager()
    if not pm.remove_project(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"message": "项目已删除"}

# ============ 任务执行 ============

async def execute_task(task_id: str, request: TaskRequest):
    global current_agent, tasks
    
    try:
        tasks[task_id]["status"] = "running"
        tasks[task_id]["updated_at"] = datetime.now().isoformat()
        
        result = current_agent.execute(request.description)
        plan = current_agent.scheduler._current_plan
        
        if plan:
            report = current_agent.tracker.get_progress_report(plan.id)
            
            subtask_results = []
            for subtask in plan.subtasks:
                subtask_info = subtask.to_dict()
                tracked_subtask = current_agent.tracker._get_subtask(plan, subtask.id)
                if tracked_subtask:
                    subtask_info["status"] = tracked_subtask.status
                    subtask_info["result"] = str(tracked_subtask.result)[:2000] if tracked_subtask.result else None
                    subtask_info["error"] = str(tracked_subtask.error)[:1000] if tracked_subtask.error else None
                    subtask_info["progress"] = tracked_subtask.progress
                subtask_results.append(subtask_info)
            
            tasks[task_id]["status"] = "completed" if result.get("success", False) else "failed"
            tasks[task_id]["progress"] = report.get("overall_progress", 100)
            tasks[task_id]["result"] = {
                "success": result.get("success", False),
                "report": report,
                "subtasks": subtask_results,
                "briefing": current_agent.get_briefing(plan.id) if plan.id else "",
            }
            tasks[task_id]["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"任务完成：{task_id}")
        else:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["result"] = {"error": "任务计划未创建"}
            
    except Exception as e:
        logger.error(f"任务执行失败：{e}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["result"] = {"error": str(e)}
    
    tasks[task_id]["updated_at"] = datetime.now().isoformat()
