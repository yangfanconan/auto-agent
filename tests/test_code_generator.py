"""
代码生成器单元测试
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from modules.code_generator import (
    CodeGenerator,
    CodeFile,
    CodeGenerationResult
)


class TestCodeFile:
    """测试 CodeFile 数据类"""

    def test_code_file_creation(self):
        """测试创建代码文件"""
        code_file = CodeFile(
            path="/path/to/file.py",
            content="print('hello')",
            language="python",
            description="测试文件"
        )

        assert code_file.path == "/path/to/file.py"
        assert code_file.content == "print('hello')"
        assert code_file.language == "python"
        assert code_file.description == "测试文件"
        assert code_file.tests == []

    def test_code_file_with_tests(self):
        """测试带测试的代码文件"""
        code_file = CodeFile(
            path="/path/to/file.py",
            content="print('hello')",
            language="python",
            tests=["test_file.py"]
        )

        assert len(code_file.tests) == 1
        assert code_file.tests[0] == "test_file.py"


class TestCodeGenerationResult:
    """测试 CodeGenerationResult 数据类"""

    def test_result_creation(self):
        """测试创建结果"""
        result = CodeGenerationResult(success=True)

        assert result.success is True
        assert result.files == []
        assert result.errors == []
        assert result.warnings == []
        assert result.metadata == {}

    def test_result_to_dict(self):
        """测试转换为字典"""
        code_file = CodeFile(
            path="/path/to/file.py",
            content="code",
            language="python"
        )

        result = CodeGenerationResult(
            success=True,
            files=[code_file],
            errors=["error1"],
            warnings=["warning1"]
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["file_count"] == 1
        assert data["errors"] == ["error1"]
        assert data["warnings"] == ["warning1"]


class TestCodeGenerator:
    """测试 CodeGenerator 类"""

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generator_initialization(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试生成器初始化"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        assert generator.workspace == Path(temp_workspace)
        assert generator._generated_files == []

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_basic_framework_python(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试生成 Python 基础框架"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        code = generator._generate_basic_framework("测试功能", "python")

        assert "测试功能" in code
        assert "def main():" in code

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_basic_framework_javascript(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试生成 JavaScript 基础框架"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        code = generator._generate_basic_framework(
            "Test function", "javascript")

        assert "Test function" in code
        assert "function main()" in code

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_basic_framework_other(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试生成其他语言基础框架"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        code = generator._generate_basic_framework("Test", "java")

        assert "Test" in code
        assert "//" in code

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_extract_code_from_output(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试从输出提取代码"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        output = '''```python
def hello():
    print("hello")
```'''

        code = generator._extract_code_from_output(output, "python")

        assert "def hello():" in code

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_extract_code_no_block(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试没有代码块时返回原内容"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        output = "just plain text"

        code = generator._extract_code_from_output(output, "python")

        assert code == "just plain text"

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_success(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试生成代码成功"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        with patch.object(generator, '_generate_with_opencode') as mock_gen:
            mock_gen.return_value = "def hello(): pass"

            result = generator.generate("测试功能", "python")

            assert result.success is True
            assert len(result.files) == 1

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_with_output_dir(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试指定输出目录生成"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        output_dir = Path(temp_workspace) / "output"
        output_dir.mkdir()

        with patch.object(generator, '_generate_with_opencode') as mock_gen:
            mock_gen.return_value = "code"

            result = generator.generate(
                "测试", "python", output_dir=str(output_dir))

            assert result.success is True

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_failure(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试生成代码失败"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        with patch.object(generator, '_generate_with_opencode') as mock_gen:
            mock_gen.return_value = None

            result = generator.generate("测试功能", "python")

            assert result.success is False
            assert len(result.errors) > 0

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_with_opencode_success(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试使用 opencode 生成成功"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_opencode = MagicMock()
        mock_opencode.is_available = True
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "```python\ncode\n```"
        mock_opencode.call_interactive.return_value = mock_result
        mock_get_tool.return_value = mock_opencode

        generator = CodeGenerator(workspace=temp_workspace)
        generator.opencode = mock_opencode

        code = generator._generate_with_opencode("测试", "python")

        assert code is not None

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_with_qwencode(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试使用 qwencode 生成"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_qwencode = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "code"
        mock_qwencode.generate_code.return_value = mock_result
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)
        generator.qwencode = mock_qwencode
        generator.opencode = None

        code = generator._generate_with_qwencode("测试", "python")

        assert code == "code"

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_module(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试生成模块"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        with patch.object(generator, 'generate') as mock_gen:
            mock_gen.return_value = CodeGenerationResult(
                success=True,
                files=[
                    CodeFile(
                        path="test.py",
                        content="code",
                        language="python")]
            )

            result = generator.generate_module("test_module", "测试模块")

            assert result.success is True

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_refactor_code(self, mock_get_tool,
                           mock_get_logger, temp_workspace):
        """测试重构代码"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        test_file = Path(temp_workspace) / "test.py"
        test_file.write_text("def old(): pass")

        result = generator.refactor_code(str(test_file), "standard")

        assert isinstance(result, CodeGenerationResult)

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_get_generated_files(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试获取已生成文件列表"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        code_file = CodeFile(path="test.py", content="code", language="python")
        generator._generated_files.append(code_file)

        files = generator.get_generated_files()

        assert len(files) == 1
        assert files[0].path == "test.py"

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_task_handler(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试任务处理器接口"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        mock_subtask = MagicMock()
        mock_subtask.description = "测试功能"
        mock_subtask.metadata = {"language": "python"}

        with patch.object(generator, 'generate') as mock_gen:
            mock_gen.return_value = CodeGenerationResult(
                success=True,
                files=[
                    CodeFile(
                        path="test.py",
                        content="code",
                        language="python")]
            )

            result = generator.generate_task("plan_001", mock_subtask)

            assert "代码生成成功" in result

    @patch('modules.code_generator.get_logger')
    @patch('modules.code_generator.get_tool')
    def test_generate_task_handler_failure(
            self, mock_get_tool, mock_get_logger, temp_workspace):
        """测试任务处理器失败"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_get_tool.return_value = None

        generator = CodeGenerator(workspace=temp_workspace)

        mock_subtask = MagicMock()
        mock_subtask.description = "测试功能"
        mock_subtask.metadata = {"language": "python"}

        with patch.object(generator, 'generate') as mock_gen:
            mock_gen.return_value = CodeGenerationResult(
                success=False,
                errors=["生成失败"]
            )

            result = generator.generate_task("plan_001", mock_subtask)

            assert "代码生成失败" in result
