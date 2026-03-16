"""
控制台 UI 模块
提供增强的交互式控制台界面
"""

import sys
import readline
from typing import Optional, List, Dict, Callable
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

from .themes import ThemeManager
from .components import TaskPanel, StatusTable, ProgressDisplay, BriefingDisplay


# 命令定义
COMMANDS = {
    "quit": {"aliases": ["exit", "q"], "desc": "退出程序"},
    "help": {"aliases": ["h", "?"], "desc": "显示帮助信息"},
    "status": {"aliases": ["s"], "desc": "查看当前任务状态"},
    "history": {"aliases": ["hist"], "desc": "查看任务历史"},
    "retry": {"aliases": [], "desc": "重试失败任务 (retry <task_id>)"},
    "cancel": {"aliases": [], "desc": "取消当前任务"},
    "config": {"aliases": [], "desc": "查看/修改配置"},
    "tools": {"aliases": [], "desc": "查看工具状态"},
    "clear": {"aliases": ["cls"], "desc": "清屏"},
    "export": {"aliases": [], "desc": "导出任务报告 (export json|md)"},
    "theme": {"aliases": [], "desc": "切换主题 (theme <name>)"},
    "briefing": {"aliases": ["b"], "desc": "显示任务简报"},
}


class ConsoleUI:
    """增强控制台 UI"""

    def __init__(self, theme: str = "default"):
        self.console = Console()
        self.theme_manager = ThemeManager(theme)
        self.task_panel = TaskPanel(self.theme_manager)
        self.status_table = StatusTable(self.theme_manager)
        self.progress_display = ProgressDisplay(self.theme_manager)
        self.briefing_display = BriefingDisplay(self.theme_manager)

        # 命令历史
        self._command_history: List[str] = []
        self._max_history = 100

        # 设置自动补全
        self._setup_autocomplete()

    def _setup_autocomplete(self):
        """设置命令自动补全"""
        def completer(text, state):
            commands = self._get_all_commands()
            matches = [cmd for cmd in commands if cmd.startswith(text)]
            return matches[state] if state < len(matches) else None

        readline.set_completer(completer)
        readline.parse_and_bind('tab: complete')

    def _get_all_commands(self) -> List[str]:
        """获取所有命令（包括别名）"""
        commands = []
        for cmd, info in COMMANDS.items():
            commands.append(cmd)
            commands.extend(info.get("aliases", []))
        return commands

    def print_banner(self):
        """打印欢迎横幅"""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   [bold cyan]Auto-Agent[/bold cyan] 全自动工程化编程智能体 v2.0.0          ║
║                                                           ║
║   支持 qwencode/opencode 工具                             ║
║   全流程自动化：环境→开发→测试→交付→Git                   ║
║                                                           ║
║   [dim]输入 'help' 查看可用命令 | 按 Tab 自动补全[/dim]                  ║
╚═══════════════════════════════════════════════════════════╝
        """
        self.console.print(Markdown(banner))

    def print_tools_status(self, tools: Dict):
        """打印工具状态"""
        self.console.print("\n[bold]📦 工具状态:[/bold]\n")

        for name, info in tools.items():
            status = "[green]✅[/green]" if info.get(
                "available", False) else "[red]❌[/red]"
            version = info.get("version", "N/A")
            self.console.print(f"  {status} [bold]{name}[/bold]: {version}")

    def print_task_result(self, result: Dict):
        """打印任务结果"""
        panel = self.task_panel.create_task_result(result)
        self.console.print(panel)

    def print_error(self, error: str, suggestion: Optional[str] = None):
        """打印错误信息"""
        panel = self.task_panel.create_error(error, suggestion)
        self.console.print(panel)

    def print_help(self):
        """打印帮助信息"""
        panel = self.task_panel.create_help(COMMANDS)
        self.console.print(panel)

    def print_subtasks_table(self, subtasks: List[Dict]):
        """打印子任务表格"""
        table = self.status_table.create_subtasks_table(subtasks)
        self.console.print(table)

    def print_environment_report(self, report: Dict):
        """打印环境报告"""
        table = self.status_table.create_environment_table(report)
        self.console.print(table)

        # 显示问题和建议
        if report.get("issues"):
            self.console.print("\n[bold red]⚠️  发现问题:[/bold red]")
            for issue in report["issues"]:
                self.console.print(f"  • {issue}")

        if report.get("recommendations"):
            self.console.print("\n[bold yellow]💡 建议:[/bold yellow]")
            for rec in report["recommendations"]:
                self.console.print(f"  • {rec}")

    def print_briefing(self, briefing: str):
        """打印任务简报"""
        panel = self.briefing_display.create_briefing(briefing)
        self.console.print(panel)

    def get_user_input(self, prompt_text: str = "📝 任务指令") -> Optional[str]:
        """获取用户输入"""
        try:
            user_input = Prompt.ask(
                f"\n[{
                    self.theme_manager.colors.progress_primary}]{prompt_text}[/{
                    self.theme_manager.colors.progress_primary}]"
            )

            # 记录历史
            if user_input:
                self._command_history.append(user_input)
                if len(self._command_history) > self._max_history:
                    self._command_history.pop(0)

            return user_input.strip()
        except (KeyboardInterrupt, EOFError):
            return None

    def get_user_input_multiline(
            self, prompt_text: str = "输入内容") -> Optional[str]:
        """获取多行用户输入"""
        self.console.print(f"[dim]{prompt_text} (输入 '.' 单独一行结束):[/dim]")

        lines = []
        while True:
            try:
                line = input()
                if line.strip() == '.':
                    break
                lines.append(line)
            except (KeyboardInterrupt, EOFError):
                return None

        return '\n'.join(lines)

    def confirm(self, message: str, default: bool = False) -> bool:
        """确认对话框"""
        return Confirm.ask(message, default=default)

    def select_option(
        self,
        message: str,
        options: List[str],
        default: int = 0
    ) -> int:
        """选择选项"""
        self.console.print(f"\n[bold]{message}[/bold]")
        for i, opt in enumerate(options):
            marker = "●" if i == default else "○"
            self.console.print(
                f"  [{
                    self.theme_manager.colors.progress_primary}]{marker}[/{
                    self.theme_manager.colors.progress_primary}] [{i}] {opt}")

        try:
            choice = Prompt.ask(
                "选择",
                default=str(default),
                choices=[str(i) for i in range(len(options))]
            )
            return int(choice)
        except (ValueError, KeyboardInterrupt):
            return default

    def show_progress(self, description: str, total: int = 100):
        """显示进度条"""
        return self.progress_display.create_progress(description)

    def clear_screen(self):
        """清屏"""
        self.console.clear()

    def print_command(self, command: str) -> bool:
        """
        处理命令输入
        返回 True 表示已处理，False 表示需要作为任务执行
        """
        cmd_lower = command.lower().strip()

        # 检查是否是命令
        matched_cmd = None
        for cmd, info in COMMANDS.items():
            if cmd_lower == cmd or cmd_lower in info.get("aliases", []):
                matched_cmd = cmd
                break

        if not matched_cmd:
            return False  # 不是命令，作为任务执行

        # 执行命令
        if matched_cmd == "quit":
            self.console.print("\n[green]👋 再见！[/green]")
            sys.exit(0)

        elif matched_cmd == "help":
            self.print_help()

        elif matched_cmd == "clear":
            self.clear_screen()

        elif matched_cmd == "status":
            self.console.print("[yellow]暂无正在执行的任务[/yellow]")

        elif matched_cmd == "history":
            self._show_history()

        elif matched_cmd == "theme":
            self._change_theme()

        elif matched_cmd == "tools":
            self.console.print("[yellow]请在启动时查看工具状态[/yellow]")

        elif matched_cmd == "config":
            self.console.print("[yellow]配置功能开发中...[/yellow]")

        elif matched_cmd == "export":
            self.console.print("[yellow]导出功能开发中...[/yellow]")

        elif matched_cmd == "retry":
            self.console.print("[yellow]重试功能开发中...[/yellow]")

        elif matched_cmd == "cancel":
            self.console.print("[yellow]取消功能开发中...[/yellow]")

        elif matched_cmd == "briefing":
            self.console.print("[yellow]暂无任务简报[/yellow]")

        return True  # 已处理

    def _show_history(self):
        """显示命令历史"""
        if not self._command_history:
            self.console.print("[dim]暂无命令历史[/dim]")
            return

        self.console.print("\n[bold]📜 命令历史:[/bold]\n")
        for i, cmd in enumerate(self._command_history[-10:], 1):  # 显示最近 10 条
            self.console.print(f"  [dim]{i:2}.[/dim] {cmd}")

    def _change_theme(self):
        """切换主题"""
        themes = ThemeManager.list_themes()
        idx = self.select_option("选择主题", themes)
        self.theme_manager.load_theme(themes[idx])
        self.console.print(f"[green]已切换到主题：{themes[idx]}[/green]")
