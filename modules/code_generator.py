"""
代码生成模块
调用 opencode/qwencode 等工具自动编写代码
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

try:
    from ..utils import get_logger, CodeGenerationException
    from ..adapters import get_tool, OpencodeAdapter, QwencodeAdapter
except ImportError:
    from utils import get_logger, CodeGenerationException
    from adapters import get_tool, OpencodeAdapter, QwencodeAdapter


@dataclass
class CodeFile:
    """代码文件"""
    path: str
    content: str
    language: str
    description: str = ""
    tests: List[str] = field(default_factory=list)


@dataclass
class CodeGenerationResult:
    """代码生成结果"""
    success: bool
    files: List[CodeFile] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "files": [{"path": f.path, "language": f.language, "description": f.description} for f in self.files],
            "errors": self.errors,
            "warnings": self.warnings,
            "file_count": len(self.files)
        }


class CodeGenerator:
    """代码生成器"""
    
    # 语言到文件扩展名的映射
    LANGUAGE_EXTENSIONS = {
        "python": "py",
        "javascript": "js",
        "typescript": "ts",
        "java": "java",
        "go": "go",
        "rust": "rs",
        "cpp": "cpp",
        "c": "c",
        "html": "html",
        "css": "css",
        "sql": "sql",
        "shell": "sh",
        "yaml": "yaml",
        "json": "json",
        "markdown": "md",
    }
    
    def __init__(self, workspace: str = "."):
        self.logger = get_logger()
        self.workspace = Path(workspace)
        
        # 获取工具适配器
        self.opencode = get_tool("opencode")
        self.qwencode = get_tool("qwencode")
        
        # 生成的文件记录
        self._generated_files: List[CodeFile] = []
    
    def generate(
        self,
        description: str,
        language: str = "python",
        output_dir: Optional[str] = None,
        filename: Optional[str] = None
    ) -> CodeGenerationResult:
        """
        生成代码
        
        Args:
            description: 代码功能描述
            language: 编程语言
            output_dir: 输出目录
            filename: 文件名
        
        Returns:
            CodeGenerationResult: 生成结果
        """
        self.logger.info(f"开始生成代码：{description[:50]}...")
        
        result = CodeGenerationResult(success=False)
        
        try:
            # 确定输出路径
            if output_dir:
                output_path = Path(output_dir)
            else:
                output_path = self.workspace
            
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 确定文件名
            if not filename:
                ext = self.LANGUAGE_EXTENSIONS.get(language.lower(), "txt")
                filename = f"generated_{len(self._generated_files) + 1}.{ext}"
            
            file_path = output_path / filename
            
            # 使用 opencode 生成代码
            code_content = self._generate_with_opencode(description, language)
            
            if not code_content:
                raise CodeGenerationException("代码生成失败，未获取到有效内容")
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code_content)
            
            # 记录生成的文件
            code_file = CodeFile(
                path=str(file_path),
                content=code_content,
                language=language,
                description=description
            )
            self._generated_files.append(code_file)
            result.files.append(code_file)
            
            result.success = True
            result.metadata["output_path"] = str(file_path)
            
            self.logger.info(f"代码生成成功：{file_path}")
            
        except Exception as e:
            result.errors.append(str(e))
            self.logger.error(f"代码生成失败：{e}")
        
        return result
    
    def _generate_with_opencode(self, description: str, language: str) -> Optional[str]:
        """使用 opencode 生成代码"""
        if self.opencode and hasattr(self.opencode, 'generate_code'):
            try:
                prompt = f"请用{language}编写以下功能的代码，要求：\n"
                prompt += "1. 代码结构清晰，遵循最佳实践\n"
                prompt += "2. 添加必要的注释\n"
                prompt += "3. 包含完整的错误处理\n\n"
                prompt += f"功能描述：{description}"
                
                result = self.opencode.call_interactive(prompt, str(self.workspace))
                
                if result.success:
                    # 提取代码内容
                    code = self._extract_code_from_output(result.output, language)
                    return code
                else:
                    self.logger.warning(f"Opencode 调用失败：{result.error}")
            
            except Exception as e:
                self.logger.warning(f"使用 opencode 生成代码失败：{e}")
        
        # 降级方案：使用 qwencode
        return self._generate_with_qwencode(description, language)
    
    def _generate_with_qwencode(self, description: str, language: str) -> Optional[str]:
        """使用 qwencode 生成代码（降级方案）"""
        if self.qwencode and hasattr(self.qwencode, 'generate_code'):
            try:
                result = self.qwencode.generate_code(description, language)
                
                if result.success:
                    return result.output
                else:
                    self.logger.warning(f"Qwencode 调用失败：{result.error}")
            
            except Exception as e:
                self.logger.warning(f"使用 qwencode 生成代码失败：{e}")
        
        # 如果都失败，返回基础代码框架
        return self._generate_basic_framework(description, language)
    
    def _generate_basic_framework(self, description: str, language: str) -> str:
        """生成基础代码框架（降级方案）"""
        if language.lower() == "python":
            return f'''"""
{description}

自动生成代码
"""

def main():
    """主函数"""
    # TODO: 实现功能
    print("功能：{description}")
    pass


if __name__ == "__main__":
    main()
'''
        elif language.lower() == "javascript":
            return f'''/**
 * {description}
 * 
 * 自动生成代码
 */

function main() {{
    // TODO: 实现功能
    console.log("功能：{description}");
}}

module.exports = {{ main }};
'''
        else:
            return f'''// {description}
// 自动生成代码

// TODO: 实现功能
'''
    
    def _extract_code_from_output(self, output: str, language: str) -> str:
        """从输出中提取代码"""
        import re
        
        # 尝试从 markdown 代码块中提取
        ext = self.LANGUAGE_EXTENSIONS.get(language.lower(), "")
        patterns = [
            f'```{language}(.*?)```',
            f'```{ext}(.*?)```',
            '```(.*?)```',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.DOTALL)
            if match:
                return match.group(1).strip()
        
        # 如果没有代码块，返回整个输出
        return output.strip()
    
    def generate_module(
        self,
        module_name: str,
        description: str,
        language: str = "python",
        output_dir: Optional[str] = None
    ) -> CodeGenerationResult:
        """
        生成模块（多文件）
        
        Args:
            module_name: 模块名称
            description: 模块功能描述
            language: 编程语言
            output_dir: 输出目录
        
        Returns:
            CodeGenerationResult: 生成结果
        """
        self.logger.info(f"开始生成模块：{module_name}")
        
        result = CodeGenerationResult(success=False)
        
        try:
            # 创建模块目录
            if output_dir:
                module_path = Path(output_dir) / module_name
            else:
                module_path = self.workspace / module_name
            
            module_path.mkdir(parents=True, exist_ok=True)
            
            # 生成主模块文件
            main_prompt = f"创建{module_name}模块的主文件，包含核心功能和接口"
            main_result = self.generate(main_prompt, language, str(module_path), f"__init__.{self.LANGUAGE_EXTENSIONS.get(language, 'py')}")
            
            if main_result.success:
                result.files.extend(main_result.files)
            
            # 生成工具函数文件
            utils_prompt = f"为{module_name}模块生成工具函数和辅助功能"
            utils_result = self.generate(utils_prompt, language, str(module_path), f"utils.{self.LANGUAGE_EXTENSIONS.get(language, 'py')}")
            
            if utils_result.success:
                result.files.extend(utils_result.files)
            
            result.success = len(result.files) > 0
            
        except Exception as e:
            result.errors.append(str(e))
            self.logger.error(f"模块生成失败：{e}")
        
        return result
    
    def refactor_code(
        self,
        file_path: str,
        optimization_level: str = "standard"
    ) -> CodeGenerationResult:
        """
        重构优化代码
        
        Args:
            file_path: 文件路径
            optimization_level: 优化级别 (basic/standard/aggressive)
        
        Returns:
            CodeGenerationResult: 重构结果
        """
        self.logger.info(f"开始重构代码：{file_path}")
        
        result = CodeGenerationResult(success=False)
        
        try:
            # 读取原代码
            with open(file_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
            
            # 使用 qwencode 优化
            if self.qwencode and hasattr(self.qwencode, 'optimize_code'):
                opt_result = self.qwencode.optimize_code(original_code, "python", optimization_level)
                
                if opt_result.success:
                    # 保存优化后的代码
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(opt_result.output)
                    
                    result.success = True
                    result.metadata["optimization_level"] = optimization_level
                else:
                    result.errors.append(f"优化失败：{opt_result.error}")
            else:
                # 使用 opencode 重构
                prompt = f"请重构优化以下代码，提升可读性和性能：\n\n```python\n{original_code}\n```"
                
                if self.opencode:
                    refactor_result = self.opencode.call(prompt)
                    if refactor_result.success:
                        new_code = self._extract_code_from_output(refactor_result.output, "python")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(new_code)
                        result.success = True
            
        except Exception as e:
            result.errors.append(str(e))
            self.logger.error(f"代码重构失败：{e}")
        
        return result
    
    def get_generated_files(self) -> List[CodeFile]:
        """获取已生成的文件列表"""
        return self._generated_files
    
    def generate_task(self, plan_id: str, subtask) -> str:
        """
        任务处理器接口
        
        Args:
            plan_id: 计划 ID
            subtask: 子任务
        
        Returns:
            str: 执行结果
        """
        try:
            description = subtask.description
            language = subtask.metadata.get("language", "python")
            output_dir = subtask.metadata.get("output_dir")
            
            result = self.generate(description, language, output_dir)
            
            if result.success:
                files_info = "\n".join([f"  - {f.path}" for f in result.files])
                return f"代码生成成功\n\n生成的文件:\n{files_info}"
            else:
                return f"代码生成失败：{', '.join(result.errors)}"
                
        except Exception as e:
            raise CodeGenerationException(f"代码生成失败：{e}")
