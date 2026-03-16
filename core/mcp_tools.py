"""
MCP (Model Context Protocol) 工具系统

参考 Qwen Code 的工具设计，实现标准化的工具调用机制
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import inspect


class ToolError(Exception):
    """工具错误"""
    pass


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class ToolSchema:
    """工具模式定义"""
    name: str
    description: str
    parameters: List[ToolParameter]
    returns: str = "string"

    def to_dict(self) -> Dict:
        """转换为字典格式（OpenAI function calling 风格）"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        p.name: {
                            "type": p.type,
                            "description": p.description,
                            **({"enum": p.enum} if p.enum else {})
                        }
                        for p in self.parameters
                    },
                    "required": [p.name for p in self.parameters if p.required]
                }
            }
        }


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """工具执行结果"""
    call_id: str
    name: str
    content: str
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "tool_call_id": self.call_id,
            "role": "tool",
            "name": self.name,
            "content": self.content
        }


class MCPTool:
    """MCP 工具基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._func: Optional[Callable] = None
        self._schema: Optional[ToolSchema] = None

    def set_handler(self, func: Callable):
        """设置处理函数"""
        self._func = func
        self._schema = self._generate_schema(func)

    def _generate_schema(self, func: Callable) -> ToolSchema:
        """从函数签名生成模式"""
        sig = inspect.signature(func)
        params = []

        for name, param in sig.parameters.items():
            if name == 'self':
                continue

            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list or param.annotation == List:
                param_type = "array"
            elif param.annotation == dict or param.annotation == Dict:
                param_type = "object"

            params.append(ToolParameter(
                name=name,
                type=param_type,
                description=f"参数 {name}",
                required=param.default == inspect.Parameter.empty,
                default=param.default if param.default != inspect.Parameter.empty else None
            ))

        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=params
        )

    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        if not self._func:
            raise ToolError(f"工具 {self.name} 未设置处理函数")

        try:
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func(**kwargs)
            else:
                result = self._func(**kwargs)

            return ToolResult(
                call_id=f"call_{self.name}_{id(result)}",
                name=self.name,
                content=str(result) if result is not None else "",
                success=True
            )
        except Exception as e:
            return ToolResult(
                call_id=f"call_{self.name}_error",
                name=self.name,
                content="",
                success=False,
                error=str(e)
            )

    @property
    def schema(self) -> Dict:
        """获取工具模式"""
        return self._schema.to_dict() if self._schema else {}


class MCPToolRegistry:
    """MCP 工具注册表"""

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}
        self._middleware: List[Callable] = []

    def register(self, name: str, description: str, func: Optional[Callable] = None):
        """注册工具"""
        tool = MCPTool(name, description)
        if func:
            tool.set_handler(func)
        self._tools[name] = tool
        return tool

    def tool(self, name: str, description: str):
        """装饰器方式注册工具"""
        def decorator(func: Callable):
            self.register(name, description, func)
            return func
        return decorator

    def get(self, name: str) -> Optional[MCPTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        """列出所有工具"""
        return [tool.schema for tool in self._tools.values()]

    async def execute(self, call: ToolCall) -> ToolResult:
        """执行工具调用"""
        tool = self._tools.get(call.name)
        if not tool:
            return ToolResult(
                call_id=call.id,
                name=call.name,
                content="",
                success=False,
                error=f"工具 '{call.name}' 不存在"
            )

        # 应用中间件
        for middleware in self._middleware:
            call = await middleware(call)

        return await tool.execute(**call.arguments)

    def add_middleware(self, middleware: Callable):
        """添加中间件"""
        self._middleware.append(middleware)


# ========== 预定义工具 ==========

registry = MCPToolRegistry()


@registry.tool("read_file", "读取文件内容")
def read_file(path: str, offset: int = 0, limit: int = 100) -> str:
    """读取文件"""
    from pathlib import Path
    try:
        content = Path(path).read_text(encoding='utf-8')
        lines = content.split('\n')
        selected = lines[offset:offset + limit]
        return '\n'.join(selected)
    except Exception as e:
        return f"错误: {e}"


@registry.tool("write_file", "写入文件内容")
def write_file(path: str, content: str, append: bool = False) -> str:
    """写入文件"""
    from pathlib import Path
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        mode = 'a' if append else 'w'
        with open(path, mode, encoding='utf-8') as f:
            f.write(content)
        return f"文件已{'追加' if append else '写入'}: {path}"
    except Exception as e:
        return f"错误: {e}"


@registry.tool("list_directory", "列出目录内容")
def list_directory(path: str = ".", pattern: str = "*") -> str:
    """列出目录"""
    from pathlib import Path
    try:
        p = Path(path)
        items = list(p.glob(pattern))
        result = []
        for item in sorted(items)[:50]:
            icon = "📁" if item.is_dir() else "📄"
            size = item.stat().st_size if item.is_file() else "-"
            result.append(f"{icon} {item.name} ({size} bytes)")
        return '\n'.join(result) if result else "目录为空"
    except Exception as e:
        return f"错误: {e}"


@registry.tool("execute_command", "执行系统命令")
def execute_command(command: str, timeout: int = 30) -> str:
    """执行命令"""
    import subprocess
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=timeout
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr] {result.stderr}"
        return output or "命令执行完成（无输出）"
    except subprocess.TimeoutExpired:
        return "错误: 命令执行超时"
    except Exception as e:
        return f"错误: {e}"


@registry.tool("search_code", "搜索代码")
def search_code(query: str, path: str = ".", file_pattern: str = "*.py") -> str:
    """搜索代码"""
    import subprocess
    try:
        result = subprocess.run(
            ["grep", "-r", "-n", query, path, f"--include={file_pattern}"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split('\n')[:30]
        return '\n'.join(lines) if lines[0] else "未找到匹配"
    except Exception as e:
        return f"错误: {e}"


@registry.tool("get_current_time", "获取当前时间")
def get_current_time(timezone: str = "UTC") -> str:
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().isoformat()


@registry.tool("calculate", "计算表达式")
def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        # 安全计算
        allowed = {"__builtins__": {}}
        result = eval(expression, allowed, {"abs": abs, "max": max, "min": min, "sum": sum})
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


# 异步工具示例
@registry.tool("analyze_code", "分析代码质量")
async def analyze_code(path: str) -> str:
    """分析代码"""
    await asyncio.sleep(0.1)  # 模拟异步操作
    return f"代码分析完成: {path}\n- 行数: 100\n- 复杂度: 中等\n- 建议: 添加更多注释"


if __name__ == "__main__":
    # 测试
    print("注册的工具:")
    for tool in registry.list_tools():
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")

    # 测试执行
    async def test():
        call = ToolCall(id="test1", name="calculate", arguments={"expression": "2 + 2 * 10"})
        result = await registry.execute(call)
        print(f"\n计算结果: {result.content}")

        call2 = ToolCall(id="test2", name="list_directory", arguments={"path": "."})
        result2 = await registry.execute(call2)
        print(f"\n目录列表:\n{result2.content[:500]}")

    asyncio.run(test())
