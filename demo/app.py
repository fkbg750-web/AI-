"""
TeamMind Demo - Streamlit 演示界面
"""
import streamlit as st
import json
from datetime import datetime
from typing import Optional

# 模拟数据（实际项目中从后端 API 获取）
DEMO_KNOWLEDGE = [
    {
        "id": "1",
        "content": "会议结论：我们决定采用 JWT 方案来实现用户认证。原因是扩展性好，支持微服务架构。",
        "info_type": "decision",
        "summary": "决定采用 JWT 认证方案",
        "source": {"type": "slack", "channel": "#tech-discuss"},
        "created_at": "2024-01-15T10:30:00",
        "decisions": [{"content": "采用 JWT 方案", "confidence": 0.95}],
        "key_points": ["JWT方案通过", "扩展性好", "支持微服务"]
    },
    {
        "id": "2",
        "content": "张三负责更新技术文档，需要在 1 月 20 日前完成。文档需要包含 JWT 的实现细节和迁移指南。",
        "info_type": "task",
        "summary": "张三负责更新技术文档",
        "source": {"type": "notion", "title": "任务分配"},
        "created_at": "2024-01-15T10:35:00",
        "action_items": [{"task": "更新技术文档", "owner": "张三", "deadline": "2024-01-20"}],
        "key_points": ["负责人张三", "截止1月20日", "包含JWT实现细节"]
    },
    {
        "id": "3",
        "content": "李四提议使用 Redis 缓存 Session，但经过讨论，大家认为这会增加运维复杂度，最终被否决。",
        "info_type": "discussion",
        "summary": "Redis Session 方案被否决",
        "source": {"type": "meeting", "title": "技术评审会议"},
        "created_at": "2024-01-15T11:00:00",
        "key_points": ["Redis方案被否决", "运维复杂度高", "最终选JWT"]
    },
    {
        "id": "4",
        "content": "用户认证重构项目启动，目标是在 2 月底前完成。用户故事：US-101 到 US-105。",
        "info_type": "project",
        "summary": "用户认证重构项目启动",
        "source": {"type": "notion", "title": "项目计划"},
        "created_at": "2024-01-10T09:00:00",
        "projects": [{"name": "用户认证重构", "status": "进行中", "deadline": "2024-02-28"}]
    }
]

DEMO_GRAPH = {
    "nodes": [
        {"id": "jwt_decision", "type": "Decision", "label": "JWT 方案"},
        {"id": "redis_rejected", "type": "Decision", "label": "Redis 方案（否决）"},
        {"id": "tech_review", "type": "Meeting", "label": "技术评审会议"},
        {"id": "zhangsan", "type": "Person", "label": "张三"},
        {"id": "auth_project", "type": "Project", "label": "认证重构项目"},
        {"id": "tech_doc", "type": "Document", "label": "技术文档"},
        {"id": "lisi", "type": "Person", "label": "李四"}
    ],
    "edges": [
        {"from": "jwt_decision", "to": "tech_review", "type": "decided_in", "label": "决定于"},
        {"from": "jwt_decision", "to": "redis_rejected", "type": "replaces", "label": "替代"},
        {"from": "tech_doc", "type": "related_to", "to": "jwt_decision", "label": "相关"},
        {"from": "tech_doc", "to": "zhangsan", "type": "assigned_to", "label": "负责人"},
        {"from": "auth_project", "to": "tech_review", "type": "discussed_in", "label": "讨论于"},
        {"from": "lisi", "to": "redis_rejected", "type": "proposed", "label": "提议"}
    ]
}

DEMO_QA_HISTORY = [
    {"question": "我们采用了什么认证方案？", "answer": "我们采用了 JWT 方案来实现用户认证。这个决定是在 1 月 15 日的技术评审会议上做出的，主要原因是 JWT 具有良好的扩展性，能够支持未来的微服务架构。"},
    {"question": "为什么否决了 Redis Session 方案？", "answer": "Redis Session 方案被否决的原因是会增加运维复杂度。李四最初提出了这个方案，但在技术评审会议上经过讨论后，大家认为需要额外维护 Redis 集群的成本太高。"},
    {"question": "谁负责更新技术文档？", "answer": "张三负责更新技术文档，需要在 1 月 20 日前完成。文档需要包含 JWT 的实现细节和迁移指南，方便后续开发人员参考。"}
]


def init_session_state():
    """初始化会话状态"""
    if "qa_history" not in st.session_state:
        st.session_state.qa_history = DEMO_QA_HISTORY.copy()

    if "graph_data" not in st.session_state:
        st.session_state.graph_data = DEMO_GRAPH.copy()

    if "knowledge_base" not in st.session_state:
        st.session_state.knowledge_base = DEMO_KNOWLEDGE.copy()


def render_header():
    """渲染页面头部"""
    st.set_page_config(
        page_title="TeamMind - 智能团队知识助手",
        page_icon="🧠",
        layout="wide"
    )

    st.title("🧠 TeamMind")
    st.caption('智能团队知识记忆系统 — 让 AI 成为团队的"老员工"')


def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.header("功能导航")

        page = st.radio(
            "选择功能",
            ["💬 智能问答", "🔗 知识图谱", "📚 知识库", "➕ 添加知识"],
            label_visibility="collapsed"
        )

        st.divider()

        st.caption("**技术架构**")
        st.caption("""
        - 多 Agent 协作
        - 向量 + 图数据库
        - RAG 混合检索
        - 本地优先部署
        """)

        st.divider()

        with st.expander("关于项目"):
            st.info("""
            **TeamMind** 是一个实验性项目，
            旨在为小型团队打造具有持久
            记忆能力的 AI 助手。

            核心技术：Claude API + Qdrant + Neo4j
            """)

        return page


def render_qa_page():
    """渲染问答页面"""
    st.header("💬 智能问答")

    st.markdown("""
    基于团队知识库的自然语言问答。
    AI 会理解上下文，给出有依据的回答。
    """)

    # 预设问题
    st.subheader("快捷问题")
    cols = st.columns(3)

    quick_questions = [
        "我们采用了什么认证方案？",
        "为什么否决了 Redis Session 方案？",
        "谁负责更新技术文档？"
    ]

    for i, q in enumerate(quick_questions):
        with cols[i]:
            if st.button(q, key=f"quick_{i}"):
                st.session_state.current_question = q

    st.divider()

    # 问答输入
    question = st.text_input(
        "问一个问题",
        value=st.session_state.get("current_question", ""),
        placeholder="例如：上次讨论的那个认证方案后来怎么定的？",
        key="question_input"
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        search_btn = st.button("🔍 搜索答案", type="primary")

    # 清空按钮
    if st.button("🗑️ 清空"):
        st.session_state.current_question = ""
        st.rerun()

    st.divider()

    # 显示问答历史
    st.subheader("问答历史")

    for i, qa in enumerate(reversed(st.session_state.qa_history)):
        with st.container():
            st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                <div style="color: #1f77b4; font-weight: bold; margin-bottom: 8px;">
                    👤 你：{qa['question']}
                </div>
                <div style="color: #2e7d32; margin-left: 10px;">
                    🤖 TeamMind：{qa['answer']}
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_graph_page():
    """渲染知识图谱页面"""
    st.header("🔗 知识图谱")

    st.markdown("""
    可视化团队知识中的实体关系。
    节点代表实体，边代表关系。
    """)

    # 图例
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("🟢 **Decision** 决策")
    with col2:
        st.markdown("🔵 **Person** 人员")
    with col3:
        st.markdown("🟠 **Project** 项目")
    with col4:
        st.markdown("🟣 **Document** 文档")

    st.divider()

    # 简单的图可视化（使用文字表示）
    st.subheader("实体关系图")

    # 显示节点
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**节点 (Nodes)**")
        for node in DEMO_GRAPH["nodes"]:
            icon = {"Decision": "📋", "Person": "👤", "Project": "📁", "Document": "📄", "Meeting": "📅"}.get(node["type"], "🔵")
            st.markdown(f"{icon} `{node['type']}` — {node['label']}")

    with col_right:
        st.markdown("**关系 (Edges)**")
        for edge in DEMO_GRAPH["edges"]:
            st.markdown(f"`{edge['from']}` —[{edge['type']}]→ `{edge['to']}`")

    st.divider()

    # 交互式查询
    st.subheader("查询实体上下文")

    query = st.text_input("输入实体名称查询关联信息", placeholder="例如：JWT")

    if st.button("🔍 查询"):
        # 简单模拟查询结果
        if "jwt" in query.lower():
            st.success("找到相关实体和关系：")
            st.markdown("""
            - **JWT 方案** (Decision)
              - 决定于：技术评审会议
              - 替代了：Redis 方案
              - 相关文档：技术文档
              - 负责人：张三
            """)
        elif "张三" in query:
            st.success("找到相关实体和关系：")
            st.markdown("""
            - **张三** (Person)
              - 负责：技术文档
              - 参与：技术评审会议
            """)
        else:
            st.info("未找到相关实体，请尝试其他关键词")


def render_knowledge_page():
    """渲染知识库页面"""
    st.header("📚 知识库")

    st.markdown("""
    团队知识的集合，包括决策、任务、讨论和文档。
    """)

    # 筛选器
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_type = st.selectbox(
            "筛选类型",
            ["全部", "decision", "task", "discussion", "project"]
        )

    # 显示知识条目
    for item in DEMO_KNOWLEDGE:
        if filter_type != "全部" and item["info_type"] != filter_type:
            continue

        icon = {
            "decision": "📋",
            "task": "📌",
            "discussion": "💬",
            "project": "📁"
        }.get(item["info_type"], "📄")

        with st.expander(f"{icon} {item['summary']} ({item['info_type']})"):
            st.markdown(f"**来源**: {item['source']}")
            st.markdown(f"**时间**: {item['created_at']}")
            st.markdown(f"**内容**: {item['content']}")

            if "key_points" in item:
                st.markdown("**关键点**:")
                for point in item["key_points"]:
                    st.markdown(f"- {point}")


def render_add_knowledge_page():
    """渲染添加知识页面"""
    st.header("➕ 添加知识")

    st.markdown("""
    添加新的团队知识到知识库。
    支持多种格式：会议纪要、讨论结论、决策记录等。
    """)

    # 输入表单
    with st.form("add_knowledge_form"):
        content = st.text_area(
            "内容",
            height=150,
            placeholder="输入要添加的知识内容..."
        )

        col1, col2 = st.columns(2)
        with col1:
            source_type = st.selectbox(
                "来源类型",
                ["slack", "notion", "email", "meeting", "file"]
            )

        with col2:
            source_id = st.text_input("来源标识", placeholder="channel名或文档ID")

        info_type = st.selectbox(
            "信息类型",
            ["discussion", "decision", "task", "document"]
        )

        submitted = st.form_submit_button("🚀 添加到知识库", type="primary")

        if submitted and content:
            st.success("✅ 知识已添加到处理队列")
            st.info("""
            **处理流程**：
            1. Extract Agent 提取实体
            2. Comprehend Agent 理解语义
            3. Relate Agent 关联关系
            4. Store Agent 存储到知识库
            """)


def main():
    """主函数"""
    init_session_state()
    render_header()
    page = render_sidebar()

    if page == "💬 智能问答":
        render_qa_page()
    elif page == "🔗 知识图谱":
        render_graph_page()
    elif page == "📚 知识库":
        render_knowledge_page()
    elif page == "➕ 添加知识":
        render_add_knowledge_page()


if __name__ == "__main__":
    main()
