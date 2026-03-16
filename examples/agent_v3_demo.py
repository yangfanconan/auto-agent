"""
Auto-Agent v3.0 演示

展示新的 ReAct 架构、MCP 工具系统和对话管理
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_v3 import ReActAgent, run_agent
from core.mcp_tools import registry, ToolCall
from core.conversation import (
    ConversationManager, MessageRole, IntentRecognizer
)


async def demo_react_agent():
    """演示 ReAct Agent"""
    print("=" * 60)
    print("🤖 ReAct Agent 演示")
    print("=" * 60)

    agent = ReActAgent(max_iterations=10)

    # 示例任务
    tasks = [
        "创建一个 Python 文件，输出 Hello World",
        "读取当前目录下的 README.md 文件",
        "执行命令：ls -la",
    ]

    for task in tasks:
        print(f"\n📋 任务: {task}")
        print("-" * 40)

        result = await agent.run(task)

        print(f"✅ 成功: {result['success']}")
        print(f"📊 步骤数: {result['steps']}")
        print(f"📝 结果:\n{result['result'][:500]}")


async def demo_mcp_tools():
    """演示 MCP 工具系统"""
    print("\n" + "=" * 60)
    print("🔧 MCP 工具系统演示")
    print("=" * 60)

    # 列出所有工具
    print("\n📦 可用工具:")
    for tool in registry.list_tools():
        func = tool['function']
        print(f"  • {func['name']}: {func['description']}")

    # 执行工具
    print("\n⚡ 执行工具:")

    # 计算
    call = ToolCall(id="calc1", name="calculate", arguments={"expression": "2 ** 10 + 100"})
    result = await registry.execute(call)
    print(f"  calculate(2^10 + 100) = {result.content}")

    # 获取时间
    call = ToolCall(id="time1", name="get_current_time", arguments={})
    result = await registry.execute(call)
    print(f"  current_time = {result.content}")

    # 列出目录
    call = ToolCall(id="ls1", name="list_directory", arguments={"path": ".", "pattern": "*.py"})
    result = await registry.execute(call)
    print(f"  list_directory:\n{result.content[:300]}...")


async def demo_conversation():
    """演示对话管理"""
    print("\n" + "=" * 60)
    print("💬 对话管理演示")
    print("=" * 60)

    # 创建对话管理器
    manager = ConversationManager(storage_path="./demo_conversations.json")

    # 创建会话
    ctx = manager.create_session()
    print(f"\n🆕 创建会话: {ctx.session_id}")

    # 模拟对话
    conversations = [
        (MessageRole.USER, "帮我写一个快速排序算法"),
        (MessageRole.ASSISTANT, "好的，我来为你实现快速排序算法。这是一个经典的 divide-and-conquer 算法。"),
        (MessageRole.USER, "时间复杂度是多少？"),
        (MessageRole.ASSISTANT, "快速排序的平均时间复杂度是 O(n log n)，最坏情况下是 O(n²)。"),
        (MessageRole.USER, "那归并排序呢？"),
        (MessageRole.ASSISTANT, "归并排序的时间复杂度稳定为 O(n log n)，但需要额外的 O(n) 空间。"),
    ]

    print("\n📝 添加对话消息:")
    for role, content in conversations:
        msg = ctx.add_message(role, content)
        print(f"  [{role.value}] {content[:50]}...")

    # 意图识别
    print("\n🎯 意图识别:")
    recognizer = IntentRecognizer()

    test_inputs = [
        "帮我写一个快速排序算法",
        "读取文件内容",
        "运行测试",
        "搜索代码中的 bug",
        "解释一下这段代码",
    ]

    for text in test_inputs:
        intent, confidence = recognizer.get_primary_intent(text)
        print(f"  '{text[:30]}...' -> {intent} ({confidence:.2f})")

    # 获取历史
    print(f"\n📜 对话历史（最近3条）:")
    for msg in ctx.get_recent(3):
        print(f"  [{msg.role.value}] {msg.content[:60]}...")

    # 压缩上下文
    print(f"\n🗜️  压缩上下文:")
    compressed = manager.compress_context(ctx.session_id, keep_recent=2)
    print(compressed[:500])

    # 保存会话
    manager.save()
    print(f"\n💾 会话已保存")


async def demo_integration():
    """演示集成使用"""
    print("\n" + "=" * 60)
    print("🚀 完整集成演示")
    print("=" * 60)

    # 创建组件
    agent = ReActAgent()
    manager = ConversationManager()
    recognizer = IntentRecognizer()

    # 创建会话
    ctx = manager.create_session()
    print(f"\n🆕 会话ID: {ctx.session_id}")

    # 用户输入
    user_input = "创建一个 Python 脚本，计算斐波那契数列"
    print(f"\n👤 用户: {user_input}")

    # 识别意图
    intent, confidence = recognizer.get_primary_intent(user_input)
    print(f"🎯 意图: {intent} (置信度: {confidence:.2f})")

    # 添加到对话历史
    ctx.add_message(MessageRole.USER, user_input, {"intent": intent, "confidence": confidence})

    # 使用 Agent 处理
    print("\n🤖 Agent 处理中...")
    result = await agent.run(user_input)

    # 添加助手回复
    ctx.add_message(
        MessageRole.ASSISTANT,
        result['result'],
        {"success": result['success'], "steps": result['steps']}
    )

    print(f"✅ 完成: {result['success']}")
    print(f"📝 结果:\n{result['result'][:500]}")

    # 第二轮对话
    user_input2 = "再优化一下性能"
    print(f"\n👤 用户: {user_input2}")

    # 获取上下文
    context = ctx.get_history(max_tokens=1000)
    print(f"\n📜 上下文长度: {len(context)} 字符")

    # 处理（使用上下文）
    result2 = await agent.run(user_input2, {"context": context})

    ctx.add_message(MessageRole.ASSISTANT, result2['result'])

    print(f"✅ 完成: {result2['success']}")
    print(f"📝 结果:\n{result2['result'][:500]}")

    # 显示完整对话
    print(f"\n📜 完整对话历史:")
    for msg in ctx.messages:
        print(f"\n[{msg.role.value.upper()}] {msg.content[:100]}...")


async def main():
    """主函数"""
    print("\n" + "🌟" * 30)
    print("  Auto-Agent v3.0 架构演示")
    print("🌟" * 30 + "\n")

    try:
        # 运行各个演示
        await demo_react_agent()
        await demo_mcp_tools()
        await demo_conversation()
        await demo_integration()

        print("\n" + "=" * 60)
        print("✨ 所有演示完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())
