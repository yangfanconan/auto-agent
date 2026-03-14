"""
UI 组件模块
定义可复用的 UI 组件：面板、表格、进度条等
"""

from datetime import datetime
from typing import List, Dict, Optional, Any
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.console import Console, RenderableType
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.syntax import Syntax
from rich.markdown import Markdown

from .themes import ThemeManager, ColorScheme, StyleConfig


class TaskPanel:
    """任务面板组件"""
    
    def __init__(self, theme: Optional[ThemeManager] = None):
        self.theme = theme or ThemeManager()
    
    def create(
        self,
        title: str,
        content: str,
        status: str = "info",
        subtitle: Optional[str] = None
    ) -> Panel:
        """创建任务面板"""
        color = self.theme.get_status_color(status)
        icon = self.theme.get_status_icon(status)
        
        # 构建内容
        full_content = f"{icon} {content}" if icon else content
        if subtitle:
            full_content += f"\n\n[dim]{subtitle}[/dim]"
        
        return Panel(
            full_content,
            title=f"[bold {color}]{title}[/bold {color}]",
            border_style=color,
            padding=(1, 2),
        )
    
    def create_task_result(self, result: Dict) -> Panel:
        """创建任务结果面板"""
        success = result.get("success", False)
        status = "success" if success else "failed"
        
        content_lines = [
            f"完成状态：{'成功' if success else '部分完成'}",
            f"整体进度：{result.get('overall_progress', 0):.1f}%",
        ]
        
        # 子任务状态
        subtasks = result.get("subtasks", [])
        if subtasks:
            content_lines.append("\n子任务:")
            for task in subtasks:
                task_status = task.get("status", "pending")
                task_icon = self.theme.get_status_icon(task_status)
                content_lines.append(
                    f"  {task_icon} [bold]{task.get('name', 'Unknown')}[/bold]: {task_status}"
                )
        
        return self.create(
            title="📋 任务执行结果",
            content="\n".join(content_lines),
            status=status,
        )
    
    def create_error(self, error: str, suggestion: Optional[str] = None) -> Panel:
        """创建错误面板"""
        content = f"[bold red]{error}[/bold red]"
        if suggestion:
            content += f"\n\n[yellow]💡 建议：{suggestion}[/yellow]"
        
        return Panel(
            content,
            title="[bold red]❌ 错误[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    
    def create_help(self, commands: Dict[str, str]) -> Panel:
        """创建帮助面板"""
        content_lines = []
        for cmd, desc in commands.items():
            content_lines.append(f"  [cyan]{cmd:<15}[/cyan] {desc}")
        
        return self.create(
            title="📖 帮助",
            content="\n".join(content_lines),
            status="info",
        )


class StatusTable:
    """状态表格组件"""
    
    def __init__(self, theme: Optional[ThemeManager] = None):
        self.theme = theme or ThemeManager()
    
    def create_subtasks_table(self, subtasks: List[Dict]) -> Table:
        """创建子任务状态表格"""
        table = Table(
            title="子任务状态",
            show_header=self.theme.style.table_show_header,
            border_style=self.theme.colors.border_primary,
        )
        
        # 添加列
        table.add_column("状态", style="cyan", width=8)
        table.add_column("任务名", style="white", width=30)
        table.add_column("类型", style="blue", width=15)
        table.add_column("进度", style="yellow", width=10)
        table.add_column("耗时", style="green", width=10)
        
        # 添加行
        for task in subtasks:
            status = task.get("status", "pending")
            icon = self.theme.get_status_icon(status)
            color = self.theme.get_status_color(status)
            
            duration = task.get("actual_duration")
            duration_str = f"{duration:.1f}s" if duration else "-"
            
            table.add_row(
                f"[{color}]{icon}[/{color}]",
                task.get("name", "Unknown"),
                task.get("task_type", "unknown").replace("_", " ").title(),
                f"{task.get('progress', 0):.0f}%",
                duration_str,
            )
        
        return table
    
    def create_environment_table(self, env_report: Dict) -> Table:
        """创建环境状态表格"""
        table = Table(
            title="🔍 环境状态",
            show_header=True,
            border_style=self.theme.colors.border_primary,
        )
        
        table.add_column("组件", style="cyan", width=20)
        table.add_column("状态", style="white", width=10)
        table.add_column("版本", style="yellow", width=15)
        table.add_column("说明", style="dim", width=40)
        
        # 操作系统
        table.add_row(
            "操作系统",
            "[green]✅[/green]",
            "-",
            env_report.get("os_info", "未知"),
        )
        
        # Python
        python_status = "[green]✅[/green]" if env_report.get("python_version") else "[red]❌[/red]"
        table.add_row(
            "Python",
            python_status,
            env_report.get("python_version", "未安装") or "未安装",
            "核心运行环境",
        )
        
        # Git
        git_status = "[green]✅[/green]" if env_report.get("git_version") else "[yellow]⚠️[/yellow]"
        table.add_row(
            "Git",
            git_status,
            env_report.get("git_version", "未安装") or "未安装",
            "版本控制",
        )
        
        # Opencode
        opencode_status = (
            "[green]✅[/green]" if env_report.get("opencode_available") 
            else "[red]❌[/red]"
        )
        table.add_row(
            "Opencode",
            opencode_status,
            "可用" if env_report.get("opencode_available") else "不可用",
            "代码生成核心工具",
        )
        
        # Qwencode
        qwencode_status = (
            "[green]✅[/green]" if env_report.get("qwencode_available") 
            else "[dim]⚪[/dim]"
        )
        table.add_row(
            "Qwencode",
            qwencode_status,
            "可用" if env_report.get("qwencode_available") else "未安装",
            "可选：批量代码处理",
        )
        
        return table


class ProgressDisplay:
    """进度显示组件"""
    
    def __init__(self, theme: Optional[ThemeManager] = None):
        self.theme = theme or ThemeManager()
        self._progress: Optional[Progress] = None
    
    def create_progress(self, description: str = "执行中...") -> Progress:
        """创建进度条"""
        return Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[bold cyan]{task.description}[/bold cyan]"),
            BarColumn(bar_width=40, style=self.theme.colors.progress_primary),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            expand=True,
        )
    
    def display_task_progress(
        self,
        task_name: str,
        total: int = 100,
        update_func=None
    ):
        """显示任务进度"""
        with self.create_progress(task_name) as progress:
            task_id = progress.add_task("", total=total)
            
            if update_func:
                for value in update_func():
                    progress.update(task_id, completed=value)
    
    def create_live_layout(self) -> Layout:
        """创建实时布局"""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        
        return layout


class CodeDisplay:
    """代码显示组件"""
    
    def __init__(self, theme: Optional[ThemeManager] = None):
        self.theme = theme or ThemeManager()
    
    def show_code(
        self,
        code: str,
        language: str = "python",
        title: Optional[str] = None,
        line_numbers: bool = True
    ) -> Syntax:
        """显示代码"""
        return Syntax(
            code,
            language,
            theme="monokai",
            line_numbers=line_numbers,
            word_wrap=True,
        )
    
    def create_code_panel(
        self,
        code: str,
        language: str = "python",
        file_path: Optional[str] = None
    ) -> Panel:
        """创建代码面板"""
        syntax = self.show_code(code, language)
        
        title = file_path or f"📄 代码 ({language})"
        
        return Panel(
            syntax,
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
            padding=(0, 0),
        )


class BriefingDisplay:
    """简报显示组件"""
    
    def __init__(self, theme: Optional[ThemeManager] = None):
        self.theme = theme or ThemeManager()
    
    def create_briefing(self, briefing: str) -> Panel:
        """创建任务简报面板"""
        return Panel(
            Markdown(briefing),
            title="[bold green]📊 任务简报[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
