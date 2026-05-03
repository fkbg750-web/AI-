"""
TeamMind CLI - 命令行入口
"""
import sys
import asyncio
from typing import Optional

import anthropic
from dotenv import load_dotenv

from src.agents import OrchestratorAgent, StoreAgent
from src.knowledge import VectorStore, GraphStore


def print_welcome():
    """打印欢迎信息"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🧠 TeamMind - 智能团队知识记忆系统                       ║
║                                                           ║
║   让 AI 成为团队的"老员工"                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)


def print_menu():
    """打印菜单"""
    print("""
可用命令：
  1. add <文本>     - 添加知识到知识库
  2. query <问题>   - 提问
  3. stats          - 查看知识库统计
  4. graph <实体>   - 查询实体上下文
  5. help           - 显示帮助
  6. quit/exit      - 退出
    """)


async def add_knowledge(orchestrator: OrchestratorAgent, text: str):
    """添加知识"""
    print(f"\n📥 正在处理: {text[:50]}...")
    result = await orchestrator.process(text)

    if result.success:
        print(f"✅ 成功存储到知识库")
        print(f"   - 提取实体: {len(result.extracted_entities)} 个")
        print(f"   - 理解摘要: {result.comprehended_summary[:50]}...")
        print(f"   - 关联关系: {len(result.related_relations)} 个")
    else:
        print(f"❌ 处理失败: {result.error}")


async def query_knowledge(orchestrator: OrchestratorAgent, question: str):
    """查询知识"""
    print(f"\n🔍 正在回答: {question}")
    result = await orchestrator.query(question)

    if result.success:
        print(f"\n🤖 回答:\n{result.answer}")
        if result.sources:
            print(f"\n📚 参考来源:")
            for src in result.sources[:3]:
                print(f"   - [{src['info_type']}] {src['content'][:60]}...")
    else:
        print(f"❌ 查询失败: {result.error}")


def main():
    """主函数"""
    load_dotenv()

    print_welcome()

    # 初始化客户端
    anthropic_client = anthropic.Anthropic()

    # 初始化知识库（需要先启动 Docker Compose）
    try:
        vector_store = VectorStore(
            qdrant_url="http://localhost",
            qdrant_port=6333,
            openai_api_key=None  # 填入 OPENAI_API_KEY
        )
        graph_store = GraphStore(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password"
        )
        print("✅ 知识库连接成功\n")
    except Exception as e:
        print(f"⚠️  知识库连接失败: {e}")
        print("   请确保已运行: docker-compose up -d\n")
        graph_store = None
        vector_store = None

    # 初始化 Orchestrator
    store_agent = StoreAgent(
        anthropic_client=anthropic_client,
        vector_store=vector_store,
        graph_store=graph_store
    ) if vector_store and graph_store else None

    orchestrator = OrchestratorAgent(
        anthropic_client=anthropic_client,
        store_agent=store_agent
    )

    print_menu()

    # 交互循环
    while True:
        try:
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            # 解析命令
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ["quit", "exit", "q"]:
                print("\n👋 再见！")
                break

            elif cmd == "help":
                print_menu()

            elif cmd == "add" and arg:
                asyncio.run(add_knowledge(orchestrator, arg))

            elif cmd == "query" and arg:
                asyncio.run(query_knowledge(orchestrator, arg))

            elif cmd == "stats":
                if graph_store:
                    stats = asyncio.run(graph_store.get_statistics())
                    print("\n📊 知识库统计:")
                    for key, count in stats.items():
                        print(f"   - {key}: {count}")
                else:
                    print("⚠️  知识库未连接")

            elif cmd == "graph" and arg:
                if graph_store:
                    context = asyncio.run(graph_store.get_entity_context(arg))
                    print(f"\n🔗 {arg} 的关联:")
                    print(f"   节点: {context['nodes']}")
                    print(f"   关系: {context['relations']}")
                else:
                    print("⚠️  知识库未连接")

            else:
                print("❌ 未知命令，输入 'help' 查看帮助")

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 错误: {e}")


if __name__ == "__main__":
    main()
