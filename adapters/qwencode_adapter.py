"""
Qwencode/Qwen 工具适配器
支持调用 qwencode/qwen 进行代码生成、格式化、编码优化等
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

try:
    from ..utils import ToolCallException, get_logger, ToolConfig
except ImportError:
    from utils import ToolCallException, get_logger, ToolConfig


@dataclass
class QwencodeResult:
    """Qwencode 调用结果"""
    success: bool
    output: str
    error: str = ""
    exit_code: int = 0
    duration: float = 0.0


class QwencodeAdapter:
    """Qwencode/Qwen 工具适配器"""

    # 支持的操作类型
    SUPPORTED_OPERATIONS = ["format", "generate", "optimize", "convert", "escape"]

    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self.logger = get_logger()
        self._path: Optional[Path] = None
        self._version: Optional[str] = None

        # 自动检测路径
        self._detect_path()

    def _detect_path(self):
        """检测 qwencode/qwen 安装路径"""
        # 优先使用配置路径
        if self.config.path:
            path = Path(self.config.path)
            if path.exists():
                self._path = path
                self.logger.info(f"使用配置的工具路径：{self._path}")
                return

        # 尝试从 PATH 查找 qwen（优先）
        try:
            result = subprocess.run(
                ["which", "qwen"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                self._path = Path(result.stdout.strip())
                self.logger.info(f"从 PATH 找到 qwen: {self._path}")
                return
        except Exception:
            pass

        # 尝试从 PATH 查找 qwencode
        try:
            result = subprocess.run(
                ["which", "qwencode"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                self._path = Path(result.stdout.strip())
                self.logger.info(f"从 PATH 找到 qwencode: {self._path}")
                return
        except Exception:
            pass

        self.logger.warning("未找到 qwen/qwencode 可执行文件")

    @property
    def is_available(self) -> bool:
        """检查工具是否可用"""
        return self._path is not None and self._path.exists()

    @property
    def version(self) -> Optional[str]:
        """获取工具版本"""
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
            self.logger.error(f"获取版本失败：{e}")

        return None
    
    @property
    def _is_qwen(self) -> bool:
        """判断是否是 qwen 命令"""
        return self._path.name == "qwen" if self._path else True

    def call(
        self,
        prompt: str,
        options: Optional[Dict] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None
    ) -> QwencodeResult:
        """
        调用 qwen/qwencode 执行任务

        Args:
            prompt: 任务提示词
            options: 额外选项
            timeout: 超时时间（秒）
            retries: 重试次数

        Returns:
            QwencodeResult: 调用结果
        """
        timeout = timeout or self.config.timeout
        max_retries = retries or self.config.max_retries

        if not self.is_available:
            raise ToolCallException("qwen", "工具不可用", {"path": str(self._path)})

        # 构建命令
        is_qwen = self._is_qwen
        cmd = [str(self._path)]
        
        if is_qwen:
            # qwen 命令格式：qwen -p "prompt"
            cmd.append("-p")
            cmd.append(prompt)
            
            # 添加选项
            if options:
                if options.get("model"):
                    cmd.extend(["-m", options["model"]])
                if options.get("sandbox"):
                    cmd.append("--sandbox")
                if options.get("debug"):
                    cmd.append("--debug")
        else:
            # qwencode 命令格式：qwencode generate --prompt "xxx"
            cmd.append("generate")
            cmd.extend(["--prompt", prompt])
            
            if options:
                for key, value in options.items():
                    cmd.append(f"--{key}")
                    if value is not True:
                        cmd.append(str(value))

        self.logger.debug(f"执行 {'qwen' if is_qwen else 'qwencode'}: {' '.join(cmd)}")

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
                    cwd=options.get("cwd") if options else None
                )

                duration = time.time() - start_time

                tool_result = QwencodeResult(
                    success=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr,
                    exit_code=result.returncode,
                    duration=duration
                )

                return tool_result

            except subprocess.TimeoutExpired:
                last_error = f"执行超时（{timeout}秒）"
                self.logger.warning(f"调用超时，重试 {attempt + 1}/{max_retries}")
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"调用失败：{e}，重试 {attempt + 1}/{max_retries}")

        raise ToolCallException("qwen", last_error, {"prompt": prompt[:200]})

    def call_interactive(
        self,
        prompt: str,
        project_dir: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> QwencodeResult:
        """交互式调用"""
        options = {"cwd": project_dir} if project_dir else {}
        return self.call(prompt, options=options, timeout=timeout)

    def generate_code(
        self,
        description: str,
        language: str = "python",
        project_dir: Optional[str] = None
    ) -> QwencodeResult:
        """生成代码"""
        options = {"cwd": project_dir} if project_dir else {}
        prompt = f"请用{language}编写以下功能的代码：{description}"
        return self.call(prompt, options=options)

    def format_code(
        self,
        code: str,
        language: str = "python"
    ) -> QwencodeResult:
        """格式化代码"""
        prompt = f"请格式化以下{language}代码，遵循最佳实践：\n\n```{language}\n{code}\n```"
        return self.call(prompt)

    def optimize_code(
        self,
        code: str,
        language: str = "python",
        level: str = "standard"
    ) -> QwencodeResult:
        """优化代码"""
        prompt = f"请优化以下{language}代码（{level}级别），提升性能和可读性：\n\n```{language}\n{code}\n```"
        return self.call(prompt)

    def __repr__(self) -> str:
        return f"QwencodeAdapter(path={self._path}, version={self.version}, available={self.is_available})"
