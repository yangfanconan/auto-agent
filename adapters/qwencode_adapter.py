"""
Qwencode 工具适配器
支持调用 qwencode 进行批量代码生成、格式化、编码优化等
"""

import subprocess
from pathlib import Path
from typing import Optional, Dict, List
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
    """Qwencode 工具适配器"""
    
    # 支持的编码格式
    SUPPORTED_ENCODINGS = ["utf-8", "gbk", "gb2312", "latin-1", "ascii"]
    
    # 支持的操作类型
    SUPPORTED_OPERATIONS = ["format", "generate", "optimize", "convert", "escape"]
    
    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self.logger = get_logger()
        self._path: Optional[Path] = None
        self._version: Optional[str] = None
        
        # 自动检测 qwencode 路径
        self._detect_path()
    
    def _detect_path(self):
        """检测 qwencode 安装路径"""
        # 优先使用配置路径
        if self.config.path:
            path = Path(self.config.path)
            if path.exists():
                self._path = path
                self.logger.info(f"使用配置的 qwencode 路径：{self._path}")
                return
        
        # 检测常见路径
        common_paths = [
            Path.home() / ".qwencode" / "bin" / "qwencode",
            Path("/usr/local/bin/qwencode"),
            Path("/opt/homebrew/bin/qwencode"),
        ]
        
        for path in common_paths:
            if path.exists():
                self._path = path
                self.logger.info(f"检测到 qwencode: {self._path}")
                return
        
        # 尝试从 PATH 查找
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
        
        self.logger.warning("未找到 qwencode 可执行文件，将使用插件模式")
    
    @property
    def is_available(self) -> bool:
        """检查 qwencode 是否可用"""
        return self._path is not None and self._path.exists()
    
    @property
    def version(self) -> Optional[str]:
        """获取 qwencode 版本"""
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
            self.logger.error(f"获取 qwencode 版本失败：{e}")
        
        return None
    
    def _build_command(
        self,
        operation: str,
        input_text: Optional[str] = None,
        input_file: Optional[str] = None,
        output_file: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> List[str]:
        """构建命令行参数"""
        cmd = [str(self._path)]
        
        # 添加操作类型
        if operation in self.SUPPORTED_OPERATIONS:
            cmd.append(operation)
        else:
            raise ValueError(f"不支持的操作类型：{operation}")
        
        # 添加选项
        if options:
            for key, value in options.items():
                if len(key) == 1:
                    cmd.append(f"-{key}")
                else:
                    cmd.append(f"--{key}")
                if value is not True:
                    cmd.append(str(value))
        
        # 添加输入文件
        if input_file:
            cmd.extend(["-i", input_file])
        
        # 添加输出文件
        if output_file:
            cmd.extend(["-o", output_file])
        
        return cmd, input_text
    
    def call(
        self,
        operation: str,
        input_text: Optional[str] = None,
        input_file: Optional[str] = None,
        output_file: Optional[str] = None,
        options: Optional[Dict] = None,
        timeout: Optional[int] = None,
        retries: Optional[int] = None
    ) -> QwencodeResult:
        """
        调用 qwencode 执行任务
        
        Args:
            operation: 操作类型 (format/generate/optimize/convert/escape)
            input_text: 输入文本
            input_file: 输入文件路径
            output_file: 输出文件路径
            options: 额外选项
            timeout: 超时时间（秒）
            retries: 重试次数
        
        Returns:
            QwencodeResult: 调用结果
        """
        timeout = timeout or self.config.timeout
        max_retries = retries or self.config.max_retries
        
        if operation not in self.SUPPORTED_OPERATIONS:
            raise ValueError(f"不支持的操作类型：{operation}")
        
        # 构建命令
        cmd = [str(self._path), operation]
        
        # 添加选项
        if options:
            for key, value in options.items():
                cmd.append(f"--{key}")
                if value is not True:
                    cmd.append(str(value))
        
        # 添加输入文件
        if input_file:
            cmd.extend(["--input", input_file])
        
        # 添加输出文件
        if output_file:
            cmd.extend(["--output", output_file])
        
        self.logger.debug(f"执行 qwencode: {' '.join(cmd)}")
        
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                import time
                start_time = time.time()
                
                # 如果有输入文本，通过 stdin 传递
                if input_text and not input_file:
                    result = subprocess.run(
                        cmd,
                        input=input_text,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                else:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                
                duration = time.time() - start_time
                
                qwencode_result = QwencodeResult(
                    success=result.returncode == 0,
                    output=result.stdout,
                    error=result.stderr,
                    exit_code=result.returncode,
                    duration=duration
                )
                
                # 记录工具调用日志
                self.logger.tool_call(
                    "qwencode",
                    {"operation": operation, "options": options},
                    qwencode_result.output[:500] if qwencode_result.success else qwencode_result.error[:500],
                    qwencode_result.success
                )
                
                return qwencode_result
                
            except subprocess.TimeoutExpired:
                last_error = f"执行超时（{timeout}秒）"
                self.logger.warning(f"qwencode 调用超时，重试 {attempt + 1}/{max_retries}")
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"qwencode 调用失败：{e}，重试 {attempt + 1}/{max_retries}")
        
        raise ToolCallException("qwencode", last_error, {"operation": operation})
    
    def format_code(
        self,
        code: str,
        language: str = "python",
        options: Optional[Dict] = None
    ) -> QwencodeResult:
        """
        格式化代码
        
        Args:
            code: 待格式化的代码
            language: 编程语言
            options: 额外选项
        
        Returns:
            QwencodeResult: 格式化后的代码
        """
        opts = options or {}
        opts["lang"] = language
        return self.call("format", input_text=code, options=opts)
    
    def generate_code(
        self,
        description: str,
        language: str = "python",
        template: Optional[str] = None,
        output_file: Optional[str] = None
    ) -> QwencodeResult:
        """
        批量生成代码
        
        Args:
            description: 代码功能描述
            language: 编程语言
            template: 代码模板
            output_file: 输出文件路径
        
        Returns:
            QwencodeResult: 生成的代码
        """
        options = {"lang": language}
        if template:
            options["template"] = template
        
        input_text = description
        return self.call("generate", input_text=input_text, options=options, output_file=output_file)
    
    def optimize_code(
        self,
        code: str,
        language: str = "python",
        level: str = "standard"
    ) -> QwencodeResult:
        """
        优化代码
        
        Args:
            code: 待优化的代码
            language: 编程语言
            level: 优化级别 (basic/standard/aggressive)
        
        Returns:
            QwencodeResult: 优化后的代码
        """
        options = {"lang": language, "level": level}
        return self.call("optimize", input_text=code, options=options)
    
    def convert_encoding(
        self,
        text: str,
        from_encoding: str = "utf-8",
        to_encoding: str = "gbk"
    ) -> QwencodeResult:
        """
        转换编码
        
        Args:
            text: 待转换的文本
            from_encoding: 源编码
            to_encoding: 目标编码
        
        Returns:
            QwencodeResult: 转换后的文本
        """
        if from_encoding not in self.SUPPORTED_ENCODINGS:
            raise ValueError(f"不支持的源编码：{from_encoding}")
        if to_encoding not in self.SUPPORTED_ENCODINGS:
            raise ValueError(f"不支持的目标编码：{to_encoding}")
        
        options = {"from": from_encoding, "to": to_encoding}
        return self.call("convert", input_text=text, options=options)
    
    def escape_text(
        self,
        text: str,
        escape_type: str = "html"
    ) -> QwencodeResult:
        """
        转义文本
        
        Args:
            text: 待转义的文本
            escape_type: 转义类型 (html/xml/url/json)
        
        Returns:
            QwencodeResult: 转义后的文本
        """
        options = {"type": escape_type}
        return self.call("escape", input_text=text, options=options)
    
    def __repr__(self) -> str:
        return f"QwencodeAdapter(path={self._path}, version={self.version}, available={self.is_available})"
