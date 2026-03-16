"""
知识库模块
管理项目知识、代码索引、问答查询
"""

import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

try:
    from ..utils import get_logger
except ImportError:
    from utils import get_logger


@dataclass
class CodeInfo:
    """代码信息"""
    file_path: str
    name: str
    type: str  # class, function, method, variable
    docstring: Optional[str] = None
    signature: Optional[str] = None
    line_start: int = 0
    line_end: int = 0
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "file_path": self.file_path,
            "name": self.name,
            "type": self.type,
            "docstring": self.docstring,
            "signature": self.signature,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "imports": self.imports,
            "dependencies": self.dependencies,
        }


@dataclass
class ProjectIndex:
    """项目索引"""
    project_name: str
    created_at: str
    files: Dict[str, Dict] = field(default_factory=dict)
    classes: Dict[str, CodeInfo] = field(default_factory=dict)
    functions: Dict[str, CodeInfo] = field(default_factory=dict)
    imports: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "project_name": self.project_name,
            "created_at": self.created_at,
            "files": self.files,
            "classes": {k: v.to_dict() for k, v in self.classes.items()},
            "functions": {k: v.to_dict() for k, v in self.functions.items()},
            "imports": self.imports,
        }


class KnowledgeBase:
    """项目知识库"""

    def __init__(self, project_path: str = "."):
        self.logger = get_logger()
        self.project_path = Path(project_path)
        self.index: Optional[ProjectIndex] = None
        self._cache: Dict[str, Any] = {}

    def index_project(
            self, file_patterns: Optional[List[str]] = None) -> ProjectIndex:
        """
        索引项目结构和代码

        Args:
            file_patterns: 文件匹配模式

        Returns:
            ProjectIndex: 项目索引
        """
        self.logger.info(f"开始索引项目：{self.project_path}")

        file_patterns = file_patterns or ["**/*.py"]

        self.index = ProjectIndex(
            project_name=self.project_path.name,
            created_at=datetime.now().isoformat()
        )

        # 索引文件
        for pattern in file_patterns:
            for file_path in self.project_path.glob(pattern):
                # 跳过测试和虚拟环境
                if self._should_skip(file_path):
                    continue

                rel_path = str(file_path.relative_to(self.project_path))

                # 索引文件内容
                file_info = self._index_file(file_path)
                if file_info:
                    self.index.files[rel_path] = file_info

        self.logger.info(f"项目索引完成：{len(self.index.files)} 个文件")

        return self.index

    def _should_skip(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        skip_patterns = [
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            "dist", "build", ".pytest_cache", "*.pyc"
        ]

        for pattern in skip_patterns:
            if pattern in str(file_path):
                return True

        return False

    def _index_file(self, file_path: Path) -> Optional[Dict]:
        """索引单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_info = {
                "path": str(file_path),
                "size": len(content),
                "lines": content.count('\n') + 1,
                "classes": [],
                "functions": [],
                "imports": [],
            }

            # 解析 Python AST
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_info = self._extract_class_info(
                            file_path, node, content)
                        file_info["classes"].append(class_info["name"])
                        self.index.classes[class_info["name"]] = class_info

                    elif isinstance(node, ast.FunctionDef):
                        func_info = self._extract_function_info(
                            file_path, node, content)
                        file_info["functions"].append(func_info["name"])
                        self.index.functions[func_info["name"]] = func_info

                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            import_name = alias.name
                            if import_name not in file_info["imports"]:
                                file_info["imports"].append(import_name)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            if node.module not in file_info["imports"]:
                                file_info["imports"].append(node.module)

            except SyntaxError:
                self.logger.debug(f"无法解析 {file_path}: 语法错误")

            return file_info

        except Exception as e:
            self.logger.error(f"索引文件失败 {file_path}: {e}")
            return None

    def _extract_class_info(self, file_path: Path,
                            node: ast.ClassDef, content: str) -> CodeInfo:
        """提取类信息"""
        docstring = ast.get_docstring(node)

        # 获取方法列表
        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]

        return CodeInfo(
            file_path=str(file_path),
            name=node.name,
            type="class",
            docstring=docstring,
            signature=f"class {node.name}",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            imports=[],
            dependencies=methods,
        )

    def _extract_function_info(
            self, file_path: Path, node: ast.FunctionDef, content: str) -> CodeInfo:
        """提取函数信息"""
        docstring = ast.get_docstring(node)

        # 构建函数签名
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        signature = f"def {node.name}({', '.join(args)})"

        return CodeInfo(
            file_path=str(file_path),
            name=node.name,
            type="function",
            docstring=docstring,
            signature=signature,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            imports=[],
            dependencies=[],
        )

    def search(self, query: str, search_type: str = "all") -> List[Dict]:
        """
        搜索项目内容

        Args:
            query: 搜索关键词
            search_type: 搜索类型 (all/class/function/file)

        Returns:
            List[Dict]: 搜索结果
        """
        if not self.index:
            return []

        results = []
        query_lower = query.lower()

        if search_type in ["all", "class"]:
            for name, info in self.index.classes.items():
                if query_lower in name.lower() or (
                        info.docstring and query_lower in info.docstring.lower()):
                    results.append({
                        "type": "class",
                        "name": name,
                        "file": info.file_path,
                        "docstring": info.docstring,
                    })

        if search_type in ["all", "function"]:
            for name, info in self.index.functions.items():
                if query_lower in name.lower() or (
                        info.docstring and query_lower in info.docstring.lower()):
                    results.append({
                        "type": "function",
                        "name": name,
                        "file": info.file_path,
                        "docstring": info.docstring,
                    })

        if search_type in ["all", "file"]:
            for path, info in self.index.files.items():
                if query_lower in path.lower():
                    results.append({
                        "type": "file",
                        "name": path,
                        "info": f"{info['lines']} 行代码",
                    })

        return results

    def query(self, question: str) -> str:
        """
        问答式查询

        Args:
            question: 问题

        Returns:
            str: 回答
        """
        if not self.index:
            return "项目尚未索引，请先调用 index_project()"

        # 简单关键词匹配
        keywords = question.lower().split()

        # 查找相关类
        for kw in keywords:
            if kw in ["类", "class"]:
                continue
            results = self.search(kw, "class")
            if results:
                return f"找到相关类：{', '.join([r['name'] for r in results])}"

        # 查找相关函数
        for kw in keywords:
            if kw in ["函数", "function", "方法", "method"]:
                continue
            results = self.search(kw, "function")
            if results:
                return f"找到相关函数：{', '.join([r['name'] for r in results])}"

        # 统计信息
        total_files = len(self.index.files)
        total_classes = len(self.index.classes)
        total_functions = len(self.index.functions)

        return f"""项目概览:
- 文件数：{total_files}
- 类数：{total_classes}
- 函数数：{total_functions}

未找到与问题直接相关的内容，请尝试更具体的关键词。"""

    def get_file_content(self, file_path: str) -> Optional[str]:
        """获取文件内容"""
        full_path = self.project_path / file_path
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def get_code_context(self, name: str) -> Optional[Dict]:
        """获取代码上下文"""
        if not self.index:
            return None

        # 查找类
        if name in self.index.classes:
            info = self.index.classes[name]
            return {
                "type": "class",
                "info": info.to_dict(),
                "content": self.get_file_content(info.file_path),
            }

        # 查找函数
        if name in self.index.functions:
            info = self.index.functions[name]
            return {
                "type": "function",
                "info": info.to_dict(),
                "content": self.get_file_content(info.file_path),
            }

        return None

    def save_index(self, path: Optional[str] = None):
        """保存索引到文件"""
        if not self.index:
            return

        save_path = Path(path) if path else self.project_path / \
            ".knowledge_index.json"

        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(self.index.to_dict(), f, ensure_ascii=False, indent=2)

        self.logger.info(f"索引已保存：{save_path}")

    def load_index(self, path: Optional[str] = None) -> bool:
        """从文件加载索引"""
        load_path = Path(path) if path else self.project_path / \
            ".knowledge_index.json"

        if not load_path.exists():
            return False

        try:
            with open(load_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.index = ProjectIndex(
                project_name=data["project_name"],
                created_at=data["created_at"],
                files=data.get("files", {}),
                classes={
                    k: CodeInfo(
                        **v) for k,
                    v in data.get(
                        "classes",
                        {}).items()},
                functions={
                    k: CodeInfo(
                        **v) for k,
                    v in data.get(
                        "functions",
                        {}).items()},
                imports=data.get("imports", {}),
            )

            self.logger.info(f"索引已加载：{load_path}")
            return True

        except Exception as e:
            self.logger.error(f"加载索引失败：{e}")
            return False
