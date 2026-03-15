"""
代码生成模块
调用 opencode/qwencode 等工具自动编写代码

增强版：支持项目结构生成、代码审查、多文件生成
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import os

try:
    from ..utils import get_logger, CodeGenerationException
    from ..utils.cache import get_cache
    from ..adapters import get_tool, OpencodeAdapter, QwenAdapter
    from ..core.task_parser import PROJECT_TEMPLATES
except ImportError:
    from utils import get_logger, CodeGenerationException
    from utils.cache import get_cache
    from adapters import get_tool, OpencodeAdapter, QwenAdapter
    from core.task_parser import PROJECT_TEMPLATES


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
        self.qwen = get_tool("qwen")

        # 生成的文件记录
        self._generated_files: List[CodeFile] = []
    
    def initialize_project_structure(self, project_type: str, project_name: Optional[str] = None) -> CodeGenerationResult:
        """
        初始化项目结构
        
        Args:
            project_type: 项目类型 (python_package/web_api/cli_tool 等)
            project_name: 项目名称
        
        Returns:
            CodeGenerationResult: 生成结果
        """
        self.logger.info(f"初始化项目结构：{project_type}")
        
        result = CodeGenerationResult(success=False)
        
        if project_type not in PROJECT_TEMPLATES:
            result.errors.append(f"未知的项目类型：{project_type}")
            return result
        
        template = PROJECT_TEMPLATES[project_type]
        project_name = project_name or f"project_{datetime.now().strftime('%Y%m%d')}"
        
        try:
            created_files = []
            
            # 创建项目目录结构
            for item in template["structure"]:
                # 判断是文件还是目录
                if item.endswith('/'):
                    # 创建目录
                    dir_path = self.workspace / project_name / item.rstrip('/')
                    dir_path.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"创建目录：{dir_path}")
                else:
                    # 创建文件
                    file_path = self.workspace / project_name / item
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 生成文件内容
                    content = self._generate_boilerplate_content(item, project_name, project_type)
                    if content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        created_files.append(str(file_path))
                        self.logger.debug(f"创建文件：{file_path}")
            
            result.success = True
            result.files = [
                CodeFile(path=path, content="", language="text", description="项目文件")
                for path in created_files
            ]
            result.metadata["project_name"] = project_name
            result.metadata["project_type"] = project_type
            
            self.logger.info(f"项目结构初始化完成：{project_name}")
            
        except Exception as e:
            result.errors.append(f"项目结构初始化失败：{e}")
            self.logger.error(f"项目结构初始化失败：{e}")
        
        return result
    
    def _generate_boilerplate_content(self, file_path: str, project_name: str, project_type: str) -> Optional[str]:
        """生成样板文件内容"""
        
        if file_path == "README.md":
            return f"""# {project_name}

## 项目简介

{PROJECT_TEMPLATES.get(project_type, {}).get('description', '自动生成项目')}

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
python -m src.main
```

## 开发

## 测试

```bash
pytest
```

## 许可证

MIT
"""
        
        elif file_path == "requirements.txt":
            if project_type in ["web_api", "flask", "fastapi"]:
                return """fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
"""
            return """# 添加项目依赖
"""
        
        elif file_path == "setup.py":
            return f'''"""
{project_name} setup.py
"""
from setuptools import setup, find_packages

setup(
    name="{project_name}",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={{"": "src"}},
    install_requires=[
        # 添加依赖
    ],
    python_requires=">=3.8",
)
'''
        
        elif file_path == ".gitignore":
            return """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.env
.venv
"""
        
        elif file_path.endswith("__init__.py"):
            return f'"""\\n{project_name} module\\n"""\\n'
        
        elif file_path == "src/main.py":
            if project_type == "cli_tool":
                return '''"""
命令行工具主入口
"""
import argparse

def main():
    parser = argparse.ArgumentParser(description="命令行工具")
    parser.add_argument("command", help="要执行的命令")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()
    
    print(f"执行命令：{args.command}")
    if args.verbose:
        print("详细模式已启用")

if __name__ == "__main__":
    main()
'''
            return '''"""
主入口模块
"""

def main():
    """主函数"""
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        
        return None
    
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
        # 确保参数类型正确
        description = str(description) if description else "生成代码"
        language = str(language) if language else "python"
        
        self.logger.info(f"开始生成代码：{description[:50]}..., language={language}, type={type(language)}")

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
        """使用 opencode 生成代码（带缓存）"""
        if self.opencode and hasattr(self.opencode, 'generate_code'):
            try:
                # 检查缓存
                cache = get_cache()
                cached_code = cache.get_cached_code(description, language)
                if cached_code:
                    self.logger.info(f"使用缓存的代码：{description[:50]}...")
                    return cached_code
                
                prompt = f"请用{language}编写以下功能的代码，要求：\n"
                prompt += "1. 代码结构清晰，遵循最佳实践\n"
                prompt += "2. 添加必要的注释\n"
                prompt += "3. 包含完整的错误处理\n\n"
                prompt += f"功能描述：{description}"

                result = self.opencode.call_interactive(prompt, str(self.workspace))

                if result.success:
                    # 提取代码内容
                    code = self._extract_code_from_output(result.output, language)
                    
                    # 缓存结果
                    cache.cache_code(description, code, language)
                    
                    return code
                else:
                    self.logger.warning(f"Opencode 调用失败：{result.error}")

            except Exception as e:
                self.logger.warning(f"使用 opencode 生成代码失败：{e}")

        # 降级方案：使用 qwen
        return self._generate_with_qwen(description, language)

    def _generate_with_qwen(self, description: str, language: str) -> Optional[str]:
        """使用 qwen 生成代码（降级方案）"""
        if self.qwen and hasattr(self.qwen, 'generate_code'):
            try:
                result = self.qwen.generate_code(description, language)

                if result.success:
                    return result.output
                else:
                    self.logger.warning(f"Qwen 调用失败：{result.error}")

            except Exception as e:
                self.logger.warning(f"使用 qwen 生成代码失败：{e}")

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
            
            # 使用 qwen 优化
            if self.qwen and hasattr(self.qwen, 'optimize_code'):
                opt_result = self.qwen.optimize_code(original_code, "python", optimization_level)
                
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
    
    def review_code(
        self,
        code: str,
        language: str = "python",
        review_aspects: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        代码审查
        
        Args:
            code: 待审查的代码
            language: 编程语言
            review_aspects: 审查方面 (style/security/performance/maintainability)
        
        Returns:
            Dict: 审查结果
        """
        self.logger.info(f"开始代码审查")
        
        review_aspects = review_aspects or ["style", "security", "performance", "maintainability"]
        
        result = {
            "success": False,
            "issues": [],
            "suggestions": [],
            "score": 0,
            "details": {}
        }
        
        try:
            # 使用 opencode 进行代码审查
            if self.opencode:
                aspects_str = ", ".join(review_aspects)
                prompt = f"""请对以下{language}代码进行审查，重点关注：{aspects_str}

代码：
```{language}
{code}
```

请按以下格式返回审查结果：
1. 发现的问题（按严重程度排序）
2. 改进建议
3. 总体评分（0-100）
"""
                
                review_result = self.opencode.call(prompt)
                
                if review_result.success:
                    result["success"] = True
                    result["review"] = review_result.output
                    result["details"]["raw_review"] = review_result.output
            
            # 基础静态分析（降级方案）
            if not result["success"]:
                result = self._basic_static_analysis(code, language, result)
            
        except Exception as e:
            result["errors"] = [str(e)]
            self.logger.error(f"代码审查失败：{e}")
        
        return result
    
    def _basic_static_analysis(self, code: str, language: str, result: Dict) -> Dict:
        """基础静态分析（降级方案）"""
        
        if language != "python":
            return result
        
        issues = []
        suggestions = []
        
        lines = code.split('\n')
        
        # 检查项
        checks = [
            (len(code) > 10000, "代码过长，建议拆分为多个模块", "将代码拆分为更小的模块"),
            (any(len(line) > 120 for line in lines), "存在过长的行（>120 字符）", "使用黑色规范拆分长行"),
            ("import *" in code, "使用了通配符导入", "使用显式导入"),
            ("eval(" in code or "exec(" in code, "使用了 eval/exec，存在安全风险", "避免使用 eval/exec"),
            ("# TODO" in code or "# FIXME" in code, "存在待办事项注释", "完成待办事项"),
            (not any(line.strip().startswith('"""') or "'''" in line for line in lines), "缺少文档字符串", "为函数和类添加文档字符串"),
        ]
        
        score = 100
        for condition, issue, suggestion in checks:
            if condition:
                issues.append(issue)
                suggestions.append(suggestion)
                score -= 10
        
        result["success"] = True
        result["issues"] = issues
        result["suggestions"] = suggestions
        result["score"] = max(0, score)
        result["details"]["language"] = language
        result["details"]["lines_of_code"] = len(lines)
        
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
            # 获取任务描述（确保是字符串）
            description = str(subtask.description) if subtask.description else f"生成{subtask.name}"
            
            # 修复：确保 language 是字符串，而不是 SubTask 对象
            lang_value = subtask.metadata.get("language", "python")
            if isinstance(lang_value, str):
                language = lang_value
            else:
                language = "python"  # 默认值
            
            output_dir = subtask.metadata.get("output_dir")
            
            # 调试日志
            self.logger.info(f"代码生成任务：description={description[:50]}..., language={language} (type={type(language).__name__})")

            # 检查是否是项目初始化任务
            if subtask.task_type.value == "project_init":
                project_type = subtask.metadata.get("project_type", "python_package")
                project_name = subtask.metadata.get("project_name")
                result = self.initialize_project_structure(project_type, project_name)
            else:
                result = self.generate(str(description), str(language), output_dir)

            if result.success:
                files_info = "\n".join([f"  - {f.path}" for f in result.files])
                return f"代码生成成功\n\n生成的文件:\n{files_info}"
            else:
                return f"代码生成失败：{', '.join(result.errors)}"

        except Exception as e:
            self.logger.error(f"代码生成异常：{e}, language 类型：{type(subtask.metadata.get('language', 'python'))}")
            raise CodeGenerationException(f"代码生成失败：{e}")
