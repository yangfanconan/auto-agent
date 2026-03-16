"""
测试知识库模块
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from core.knowledge_base import KnowledgeBase, ProjectIndex, CodeInfo


class TestKnowledgeBase:
    """知识库测试"""

    @pytest.fixture
    def temp_project(self):
        """创建临时项目目录"""
        temp_dir = tempfile.mkdtemp()

        # 创建示例 Python 文件
        src_dir = Path(temp_dir) / "src"
        src_dir.mkdir()

        # 创建示例代码
        (src_dir / "__init__.py").write_text('"""示例包"""')
        (src_dir / "main.py").write_text('''
"""主模块"""

def hello(name: str) -> str:
    """打招呼"""
    return f"Hello, {name}!"

class Calculator:
    """计算器类"""

    def add(self, a: int, b: int) -> int:
        """加法"""
        return a + b

    def subtract(self, a: int, b: int) -> int:
        """减法"""
        return a - b
''')

        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_init(self, temp_project):
        """测试初始化"""
        kb = KnowledgeBase(temp_project)
        assert kb.project_path == Path(temp_project)
        assert kb.index is None

    def test_index_project(self, temp_project):
        """测试索引项目"""
        kb = KnowledgeBase(temp_project)
        index = kb.index_project()

        assert index is not None
        assert len(index.files) > 0
        assert len(index.classes) > 0
        assert len(index.functions) > 0

    def test_index_classes(self, temp_project):
        """测试类索引"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        assert "Calculator" in kb.index.classes
        calc_info = kb.index.classes["Calculator"]
        assert calc_info.type == "class"
        assert calc_info.docstring == "计算器类"

    def test_index_functions(self, temp_project):
        """测试函数索引"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        assert "hello" in kb.index.functions
        func_info = kb.index.functions["hello"]
        assert func_info.type == "function"
        assert func_info.docstring == "打招呼"

    def test_search_class(self, temp_project):
        """测试搜索类"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        results = kb.search("Calculator", "class")
        assert len(results) > 0
        assert results[0]["name"] == "Calculator"

    def test_search_function(self, temp_project):
        """测试搜索函数"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        results = kb.search("hello", "function")
        assert len(results) > 0
        assert results[0]["name"] == "hello"

    def test_search_all(self, temp_project):
        """测试全局搜索"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        results = kb.search("add")
        assert len(results) > 0

    def test_query(self, temp_project):
        """测试问答查询"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        answer = kb.query("有哪些类？")
        assert "Calculator" in answer

    def test_get_file_content(self, temp_project):
        """测试获取文件内容"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        content = kb.get_file_content("src/main.py")
        assert content is not None
        assert "Calculator" in content

    def test_get_code_context(self, temp_project):
        """测试获取代码上下文"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        context = kb.get_code_context("Calculator")
        assert context is not None
        assert context["type"] == "class"

    def test_save_and_load_index(self, temp_project):
        """测试保存和加载索引"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        # 保存索引
        index_path = Path(temp_project) / ".knowledge_index.json"
        kb.save_index(str(index_path))
        assert index_path.exists()

        # 创建新的知识库实例
        kb2 = KnowledgeBase(temp_project)
        assert kb2.index is None

        # 加载索引
        loaded = kb2.load_index(str(index_path))
        assert loaded is True
        assert kb2.index is not None
        assert "Calculator" in kb2.index.classes

    def test_skip_patterns(self, temp_project):
        """测试跳过文件模式"""
        kb = KnowledgeBase(temp_project)

        # 创建应跳过的文件
        pycache = Path(temp_project) / "__pycache__"
        pycache.mkdir()
        (pycache / "test.pyc").write_text("test")

        kb.index_project()

        # 不应包含 __pycache__ 中的文件
        for path in kb.index.files:
            assert "__pycache__" not in path

    def test_index_to_dict(self, temp_project):
        """测试索引转字典"""
        kb = KnowledgeBase(temp_project)
        kb.index_project()

        index_dict = kb.index.to_dict()

        assert "project_name" in index_dict
        assert "created_at" in index_dict
        assert "files" in index_dict
        assert "classes" in index_dict
        assert "functions" in index_dict


class TestCodeInfo:
    """代码信息测试"""

    def test_code_info_creation(self):
        """测试代码信息创建"""
        info = CodeInfo(
            file_path="test.py",
            name="TestClass",
            type="class",
            docstring="测试类",
        )

        assert info.file_path == "test.py"
        assert info.name == "TestClass"
        assert info.type == "class"
        assert info.docstring == "测试类"

    def test_code_info_to_dict(self):
        """测试代码信息转字典"""
        info = CodeInfo(
            file_path="test.py",
            name="test_func",
            type="function",
        )

        info_dict = info.to_dict()

        assert info_dict["file_path"] == "test.py"
        assert info_dict["name"] == "test_func"
        assert info_dict["type"] == "function"
