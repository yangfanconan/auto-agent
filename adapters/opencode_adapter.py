"""
Opencode 工具适配器
支持调用 opencode 进行代码编写、架构设计、注释完善等
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from ..utils import ToolCallException, get_logger, ToolConfig
except ImportError:
    from utils import ToolCallException, get_logger, ToolConfig


@dataclass
class OpencodeResult:
    """Opencode 调用结果"""
    success: bool
    output: str
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0


class OpencodeAdapter:
    """Opencode 工具适配器"""
    
    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self.logger = get_logger()
        self._path: Optional[Path] = None
        self._version: Optional[str] = None
        
        # 自动检测 opencode 路径
        self._detect_path()
    
    def _detect_path(self):
        """检测 opencode 安装路径"""
        # 优先使用配置路径
        if self.config.path:
            path = Path(self.config.path)
            if path.exists():
                self._path = path
                self.logger.info(f"使用配置的 opencode 路径：{self._path}")
                return
        
        # 检测常见路径
        common_paths = [
            Path.home() / ".opencode" / "bin" / "opencode",
            Path("/usr/local/bin/opencode"),
            Path("/opt/homebrew/bin/opencode"),
        ]
        
        for path in common_paths:
            if path.exists():
                self._path = path
                self.logger.info(f"检测到 opencode: {self._path}")
                return
        
        # 尝试从 PATH 查找
        result = subprocess.run(
            ["which", "opencode"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            self._path = Path(result.stdout.strip())
            self.logger.info(f"从 PATH 找到 opencode: {self._path}")
            return
        
        self.logger.warning("未找到 opencode 可执行文件")
    
    @property
    def is_available(self) -> bool:
        """检查 opencode 是否可用"""
        return self._path is not None and self._path.exists()
    
    @property
    def version(self) -> Optional[str]:
        """获取 opencode 版本"""
        if self._version:
            return self._version
        
        if not self.is_available:
            return None
        
        try:
            result = subprocess.run(
                [str(self._path), "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                self._version = result.stdout.strip()
                return self._version
        except Exception as e:
            self.logger.error(f"获取 opencode 版本失败：{e}")
        
        return None
    
    def _build_command(self, prompt: str, args: Optional[Dict] = None) -> List[str]:
        """构建命令行参数"""
        cmd = [str(self._path)]
        
        # 添加额外参数
        if args:
            for key, value in args.items():
                if len(key) == 1:
                    cmd.append(f"-{key}")
                else:
                    cmd.append(f"--{key}")
                if value is not True:
                    cmd.append(str(value))
        
        # 添加提示词
        cmd.extend(["--prompt", prompt])
        
        return cmd
    
    def call(
        self,
        prompt: str,
        args: Optional[Dict] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None
    ) -> OpencodeResult:
        """
        调用 opencode 执行任务
        
        Args:
            prompt: 任务提示词
            args: 额外命令行参数
            timeout: 超时时间（秒）
            retries: 重试次数
        
        Returns:
            OpencodeResult: 调用结果
        """
        timeout = timeout or self.config.timeout
        max_retries = retries or self.config.max_retries
        
        if not self.is_available:
            raise ToolCallException("opencode", "工具不可用", {"path": str(self._path)})
        
        cmd = self._build_command(prompt, args)
        self.logger.debug(f"执行 opencode: {' '.join(cmd)}")
        
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                import time
                start_time = time.time()
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=args.get("cwd") if args else None
                )
                
                duration = time.time() - start_time
                
                opencode_result = OpencodeResult(
                    success=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr,
                    exit_code=result.returncode,
                    duration=duration
                )
                
                # 记录工具调用日志
                self.logger.tool_call(
                    "opencode",
                    {"prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt, "args": args},
                    opencode_result.output[:500] if opencode_result.success else opencode_result.error[:500],
                    opencode_result.success
                )
                
                return opencode_result
                
            except subprocess.TimeoutExpired:
                last_error = f"执行超时（{timeout}秒）"
                self.logger.warning(f"opencode 调用超时，重试 {attempt + 1}/{max_retries}")
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"opencode 调用失败：{e}，重试 {attempt + 1}/{max_retries}")
        
        raise ToolCallException("opencode", last_error, {"prompt": prompt[:200]})
    
    def call_interactive(
        self,
        prompt: str,
        project_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> OpencodeResult:
        """
        交互式调用 opencode（适用于复杂任务）
        
        Args:
            prompt: 任务提示词
            project_dir: 项目目录
            timeout: 超时时间
        
        Returns:
            OpencodeResult: 调用结果
        """
        args = {"cwd": project_dir} if project_dir else {}
        return self.call(prompt, args=args, timeout=timeout)
    
    def generate_code(
        self,
        description: str,
        language: str = "python",
        project_dir: Optional[str] = None
    ) -> OpencodeResult:
        """
        生成代码
        
        Args:
            description: 代码功能描述
            language: 编程语言
            project_dir: 项目目录
        
        Returns:
            OpencodeResult: 生成的代码
        """
        prompt = f"请用{language}编写以下功能的代码：{description}"
        return self.call_interactive(prompt, project_dir)
    
    def review_code(
        self,
        code: str,
        language: str = "python"
    ) -> OpencodeResult:
        """
        代码审查
        
        Args:
            code: 待审查的代码
            language: 编程语言
        
        Returns:
            OpencodeResult: 审查结果
        """
        prompt = f"请审查以下{language}代码，指出问题并给出改进建议：\n\n```{language}\n{code}\n```"
        return self.call(prompt)
    
    def explain_code(
        self,
        code: str,
        language: str = "python"
    ) -> OpencodeResult:
        """
        解释代码
        
        Args:
            code: 待解释的代码
            language: 编程语言
        
        Returns:
            OpencodeResult: 解释结果
        """
        prompt = f"请详细解释以下{language}代码的功能和实现逻辑：\n\n```{language}\n{code}\n```"
        return self.call(prompt)
    
    def __repr__(self) -> str:
        return f"OpencodeAdapter(path={self._path}, version={self.version}, available={self.is_available})"
