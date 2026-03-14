"""
Git 自动化模块
管理 Git 仓库、提交、推送、分支操作
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

try:
    from ..utils import get_logger, GitException
except ImportError:
    from utils import get_logger, GitException


@dataclass
class GitStatus:
    """Git 状态"""
    branch: str
    is_dirty: bool
    staged_files: List[str] = field(default_factory=list)
    unstaged_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)


@dataclass
class CommitInfo:
    """提交信息"""
    hash: str
    short_hash: str
    author: str
    date: str
    message: str
    files_changed: int = 0


@dataclass
class GitReport:
    """Git 操作报告"""
    success: bool
    operation: str
    branch: Optional[str] = None
    commit_hash: Optional[str] = None
    message: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "operation": self.operation,
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "message": self.message,
            "errors": self.errors
        }


class GitManager:
    """Git 管理器"""
    
    # 提交类型映射
    COMMIT_TYPES = {
        "feat": "新功能",
        "fix": "修复 Bug",
        "docs": "文档更新",
        "style": "代码格式",
        "refactor": "重构",
        "test": "测试",
        "chore": "构建/工具",
        "perf": "性能优化",
        "ci": "CI 配置",
        "build": "构建系统",
    }
    
    def __init__(self, workspace: str = "."):
        self.logger = get_logger()
        self.workspace = Path(workspace)
        self._git_available = self._check_git()
    
    def _check_git(self) -> bool:
        """检查 Git 是否可用"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    @property
    def is_available(self) -> bool:
        """Git 是否可用"""
        return self._git_available
    
    def init_repo(self) -> bool:
        """初始化 Git 仓库"""
        if not self._git_available:
            raise GitException("Git 未安装")
        
        try:
            self.logger.info(f"初始化 Git 仓库：{self.workspace}")
            
            result = subprocess.run(
                ["git", "init"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                self.logger.info("Git 仓库初始化成功")
                return True
            else:
                raise GitException(f"Git 初始化失败：{result.stderr}")
                
        except Exception as e:
            raise GitException(f"Git 初始化异常：{e}")
    
    def get_status(self) -> GitStatus:
        """获取 Git 状态"""
        if not self._git_available:
            raise GitException("Git 未安装")
        
        try:
            # 获取当前分支
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace)
            )
            branch = branch_result.stdout.strip() or "main"
            
            # 获取状态
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace)
            )
            
            staged = []
            unstaged = []
            untracked = []
            
            for line in status_result.stdout.split('\n'):
                if not line.strip():
                    continue
                
                status_char = line[:2].strip()
                file_path = line[3:].strip()
                
                if line.startswith('??'):
                    untracked.append(file_path)
                elif line.startswith('M '):
                    unstaged.append(file_path)
                elif line.startswith('A ') or line.startswith('M '):
                    staged.append(file_path)
            
            is_dirty = bool(staged or unstaged or untracked)
            
            return GitStatus(
                branch=branch,
                is_dirty=is_dirty,
                staged_files=staged,
                unstaged_files=unstaged,
                untracked_files=untracked
            )
            
        except Exception as e:
            raise GitException(f"获取 Git 状态失败：{e}")
    
    def add_all(self) -> bool:
        """添加所有文件"""
        try:
            self.logger.info("添加所有文件到暂存区")
            
            result = subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                return True
            else:
                self.logger.warning(f"git add 警告：{result.stderr}")
                return True  # 通常非零退出码也可能是部分成功
                
        except Exception as e:
            raise GitException(f"git add 失败：{e}")
    
    def commit(
        self,
        message: str,
        commit_type: str = "feat"
    ) -> GitReport:
        """
        提交代码
        
        Args:
            message: 提交信息
            commit_type: 提交类型 (feat/fix/docs/style/refactor/test/chore/perf/ci/build)
        
        Returns:
            GitReport: 提交报告
        """
        if not self._git_available:
            return GitReport(
                success=False,
                operation="commit",
                errors=["Git 未安装"]
            )
        
        try:
            # 构建标准化提交信息
            type_desc = self.COMMIT_TYPES.get(commit_type, "更新")
            full_message = f"{commit_type}: {message}"
            
            self.logger.info(f"提交代码：{full_message}")
            
            # 先添加所有文件
            self.add_all()
            
            # 执行提交
            result = subprocess.run(
                ["git", "commit", "-m", full_message],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                # 获取提交哈希
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(self.workspace)
                )
                
                commit_hash = hash_result.stdout.strip()[:8]
                
                self.logger.info(f"提交成功：{commit_hash}")
                
                return GitReport(
                    success=True,
                    operation="commit",
                    branch=self.get_status().branch,
                    commit_hash=commit_hash,
                    message=full_message
                )
            else:
                # 检查是否没有需要提交的文件
                if "nothing to commit" in result.stdout:
                    self.logger.info("没有需要提交的文件")
                    return GitReport(
                        success=True,
                        operation="commit",
                        message="没有需要提交的文件"
                    )
                
                raise GitException(f"提交失败：{result.stderr}")
                
        except GitException as e:
            return GitReport(
                success=False,
                operation="commit",
                errors=[str(e)]
            )
        except Exception as e:
            return GitReport(
                success=False,
                operation="commit",
                errors=[f"提交异常：{e}"]
            )
    
    def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None
    ) -> GitReport:
        """
        推送代码
        
        Args:
            remote: 远程仓库名
            branch: 分支名
        
        Returns:
            GitReport: 推送报告
        """
        if not self._git_available:
            return GitReport(
                success=False,
                operation="push",
                errors=["Git 未安装"]
            )
        
        try:
            status = self.get_status()
            push_branch = branch or status.branch
            
            self.logger.info(f"推送到 {remote}/{push_branch}")
            
            result = subprocess.run(
                ["git", "push", "-u", remote, push_branch],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                self.logger.info("推送成功")
                return GitReport(
                    success=True,
                    operation="push",
                    branch=push_branch,
                    message=f"已推送到 {remote}/{push_branch}"
                )
            else:
                # 检查是否是远程仓库不存在
                if "does not appear to be a git repository" in result.stderr:
                    return GitReport(
                        success=False,
                        operation="push",
                        branch=push_branch,
                        errors=["远程仓库未配置或不可访问"]
                    )
                
                raise GitException(f"推送失败：{result.stderr}")
                
        except GitException as e:
            return GitReport(
                success=False,
                operation="push",
                errors=[str(e)]
            )
        except Exception as e:
            return GitReport(
                success=False,
                operation="push",
                errors=[f"推送异常：{e}"]
            )
    
    def create_branch(
        self,
        branch_name: str,
        from_branch: Optional[str] = None
    ) -> bool:
        """创建分支"""
        try:
            self.logger.info(f"创建分支：{branch_name}")
            
            cmd = ["git", "checkout", "-b", branch_name]
            if from_branch:
                cmd.append(from_branch)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                self.logger.info(f"分支 {branch_name} 创建成功")
                return True
            else:
                raise GitException(f"创建分支失败：{result.stderr}")
                
        except Exception as e:
            raise GitException(f"创建分支异常：{e}")
    
    def checkout(self, branch_name: str) -> bool:
        """切换分支"""
        try:
            self.logger.info(f"切换到分支：{branch_name}")
            
            result = subprocess.run(
                ["git", "checkout", branch_name],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace)
            )
            
            if result.returncode == 0:
                return True
            else:
                raise GitException(f"切换分支失败：{result.stderr}")
                
        except Exception as e:
            raise GitException(f"切换分支异常：{e}")
    
    def get_log(self, count: int = 10) -> List[CommitInfo]:
        """获取提交日志"""
        try:
            result = subprocess.run(
                [
                    "git", "log", f"-{count}",
                    "--format=%H|%h|%an|%ai|%s"
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace)
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append(CommitInfo(
                        hash=parts[0],
                        short_hash=parts[1],
                        author=parts[2],
                        date=parts[3],
                        message=parts[4]
                    ))
            
            return commits
            
        except Exception as e:
            self.logger.error(f"获取提交日志失败：{e}")
            return []
    
    def configure_user(self, name: str, email: str) -> bool:
        """配置 Git 用户信息"""
        try:
            subprocess.run(
                ["git", "config", "user.name", name],
                capture_output=True,
                timeout=10,
                cwd=str(self.workspace)
            )
            subprocess.run(
                ["git", "config", "user.email", email],
                capture_output=True,
                timeout=10,
                cwd=str(self.workspace)
            )
            self.logger.info(f"Git 用户已配置：{name} <{email}>")
            return True
        except Exception as e:
            raise GitException(f"配置 Git 用户失败：{e}")
    
    def commit_task(self, plan_id: str, subtask) -> str:
        """
        任务处理器接口
        
        Args:
            plan_id: 计划 ID
            subtask: 子任务
        
        Returns:
            str: 执行结果
        """
        try:
            # 检查是否是 Git 仓库
            git_dir = self.workspace / ".git"
            if not git_dir.exists():
                self.logger.info("初始化 Git 仓库")
                self.init_repo()
            
            # 获取提交信息
            commit_type = subtask.metadata.get("commit_type", "feat")
            commit_message = subtask.metadata.get(
                "commit_message",
                f"完成 {subtask.name}"
            )
            
            # 执行提交
            report = self.commit(commit_message, commit_type)
            
            if report.success:
                result = f"Git 提交成功\n\n"
                result += f"分支：{report.branch}\n"
                result += f"提交：{report.commit_hash}\n"
                result += f"信息：{report.message}"
                
                # 自动推送（如果配置了）
                if subtask.metadata.get("auto_push", False):
                    push_report = self.push()
                    if push_report.success:
                        result += f"\n推送：{push_report.message}"
                    else:
                        result += f"\n推送失败：{', '.join(push_report.errors)}"
                
                return result
            else:
                return f"Git 提交失败：{', '.join(report.errors)}"
                
        except Exception as e:
            raise GitException(f"Git 操作失败：{e}")
