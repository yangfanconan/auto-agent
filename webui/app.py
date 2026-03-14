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


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: str
    created_at: str


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
            created_at=task["created_at"]
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
        
        try:
            while True:
                if task_id in tasks:
                    task = tasks[task_id]
                    await websocket.send_json({
                        "task_id": task_id,
                        "status": task["status"],
                        "progress": task["progress"],
                        "subtasks": task["subtasks"],
                        "updated_at": task["updated_at"],
                    })
                else:
                    await websocket.send_json({"error": "任务不存在"})
                
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            logger.info(f"WebSocket 断开：{task_id}")
        except Exception as e:
            logger.error(f"WebSocket 错误：{e}")


async def execute_task(task_id: str, request: TaskRequest):
    """执行任务"""
    global current_agent, tasks
    
    try:
        # 更新状态为运行中
        tasks[task_id]["status"] = "running"
        tasks[task_id]["updated_at"] = datetime.now().isoformat()
        
        # 解析任务
        parser = TaskParser()
        plan = parser.parse(request.description)
        
        # 更新子任务
        tasks[task_id]["subtasks"] = [t.to_dict() for t in plan.subtasks]
        
        # 执行计划
        if current_agent:
            result = current_agent.scheduler.execute_plan(plan)
            
            # 获取报告
            report = current_agent.tracker.get_progress_report(plan.id)
            
            # 更新任务
            tasks[task_id]["status"] = "completed" if result else "failed"
            tasks[task_id]["progress"] = plan.get_progress()
            tasks[task_id]["result"] = report
            tasks[task_id]["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"任务完成：{task_id}, 结果：{result}")
        else:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["result"] = {"error": "智能体未初始化"}
            
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
                <label>工作空间</label>
                <input type="text" id="workspace" value="." placeholder="项目路径">
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
        
        // 创建任务
        async function createTask() {
            const description = document.getElementById('taskDescription').value;
            const workspace = document.getElementById('workspace').value;
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
                    body: JSON.stringify({ description, workspace, auto_test: autoTest, auto_commit: autoCommit })
                });
                
                const data = await response.json();
                addLog(`任务已创建：${data.task_id}`, 'info');
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
                
                return `
                <div class="task-item">
                    <div class="task-info">
                        <div><strong>${escapeHtml(task.description)}</strong></div>
                        <div style="color: #888; font-size: 13px; margin-top: 4px;">
                            ${dateStr}
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${task.progress || 0}%"></div>
                        </div>
                    </div>
                    <span class="task-status status-${task.status}">${task.status}</span>
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
        
        // 轮询更新
        setInterval(loadTasks, 3000);
        
        // 初始加载
        loadTasks();
        addLog('Web UI 已就绪', 'success');
    </script>
</body>
</html>
"""


# ============ 主入口 ============

app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
