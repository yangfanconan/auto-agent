"""
测试根模块
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import_main():
    """测试主模块可导入"""
    import main
    assert main is not None


def test_import_core():
    """测试核心模块可导入"""
    from core import AutoAgent
    assert AutoAgent is not None


def test_import_utils():
    """测试工具模块可导入"""
    from utils import get_logger
    assert get_logger is not None
