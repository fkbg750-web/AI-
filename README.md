# TeamMind - 智能团队知识记忆系统

> 让 AI 成为团队的"老员工" — 记住项目历史、理解决策背景、串联碎片信息

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude-purple.svg)](https://anthropic.com)

## 核心特性

### 🔄 多 Agent 协作架构
```
Orchestrator → Extract / Comprehend / Relate / Store
```
四个专业 Agent 分工协作，避免单一大模型处理所有任务导致的效果不稳定。

### 🧠 混合知识库
- **向量数据库**：语义检索，语义相似的内容
- **图数据库**：关系推理，实体之间的关联链路

### 📚 RAG + Graph 混合检索
不仅能做 RAG 问答，还能推理"这个决策影响了哪些任务"。

### 🏠 本地优先
核心数据本地存储，LLM 云端调用，兼顾隐私和效果。

---

## 快速开始

### 前置要求
- Python 3.11+
- Docker & Docker Compose（本地开发）
- Claude API Key（或其他 LLM API）

### 安装

```bash
# 克隆项目
git clone https://github.com/your-username/teammind.git
cd teammind

# 启动本地服务（Qdrant + Neo4j）
docker-compose up -d

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 运行演示
cd demo && streamlit run app.py
```

访问 `http://localhost:8501` 即可体验。

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      数据摄入层                              │
│   Slack │ Notion │ 邮件 │ 本地文件 → n8n 自动化摄入          │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Agent 编排层                             │
│                                                             │
│   ┌─────────┐  ┌───────────┐  ┌─────────┐  ┌─────────┐   │
│   │ Extract │→ │ Comprehend│→ │ Relate  │→ │  Store  │   │
│   │ Agent   │  │  Agent    │  │ Agent   │  │ Agent   │   │
│   └─────────┘  └───────────┘  └─────────┘  └─────────┘   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      知识库层                               │
│          Qdrant (向量)  +  Neo4j (图谱)                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      对话接口层                             │
│          Streamlit Demo │ API │ Slack Bot                   │
└─────────────────────────────────────────────────────────────┘
```

详细架构设计见 [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 核心逻辑

### 1. 数据摄入流程

```
文档/消息 → 解析 → 分段 → 去重 → Embedding → 索引 → 关联
```

### 2. 多跳问答

```
用户提问 → Query 改写 → 向量检索 + 图检索 → 上下文融合 → LLM 生成 → 答案 + 引用
```

### 3. 决策追踪

```
会议内容 → 提取决策点 → 关联任务/成员 → 存入图谱 → 可视化决策链路
```

---

## 项目结构

```
teammind/
├── src/
│   ├── agents/           # Agent 实现
│   │   ├── orchestrator.py
│   │   ├── extractor.py
│   │   ├── comprehender.py
│   │   ├── relater.py
│   │   └── store.py
│   ├── knowledge/        # 知识库
│   │   ├── vector_store.py
│   │   └── graph_store.py
│   ├── ingestion/        # 数据摄入
│   │   └── processor.py
│   └── api/              # REST API
│       └── main.py
├── demo/
│   └── app.py            # Streamlit 演示界面
├── docker-compose.yml     # 本地服务
├── requirements.txt
└── README.md
```

---

## 在线演示

**Streamlit Cloud**: [待部署]

演示功能：
- 自然语言问答（基于示例数据）
- 知识图谱可视化
- 决策链路追踪

---

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| LLM | Claude API / GPT-4 |
| 向量数据库 | Qdrant |
| 图数据库 | Neo4j |
| 数据摄入 | n8n |
| API | FastAPI |
| 前端 | Streamlit / React |
| 桌面客户端 | Tauri |

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 联系方式

- GitHub Issues: [问题反馈](https://github.com/your-username/teammind/issues)
- 邮箱: your-email@example.com
