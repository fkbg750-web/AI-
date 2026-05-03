# TeamMind 架构设计文档

## 1. 设计目标

1. **多 Agent 协作** - 专业 Agent 分工，避免单点失败
2. **混合知识库** - 向量 + 图谱，语义 + 关系双重检索
3. **本地优先** - 数据自主可控，隐私保障
4. **可扩展** - 易于添加新的数据源和 Agent

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户交互层                               │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│    │  Streamlit  │  │  Slack Bot  │  │   REST API  │            │
│    │   (Demo)    │  │  (生产)     │  │  (集成)     │            │
│    └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                       Orchestrator Agent                        │
│                                                                 │
│   意图理解 → 任务分解 → Agent 调度 → 结果聚合 → 响应生成          │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
        ┌─────────────────────┬─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Extract Agent │    │Comprehend     │    │ Relate Agent  │
│               │    │   Agent       │    │               │
│ - 提取实体    │    │               │    │ - 关系识别    │
│ - 分类信息    │    │ - 语义理解    │    │ - 图谱构建   │
│ - 标注来源    │    │ - 决策识别    │    │ - 链路维护   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┴─────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                         Store Agent                             │
│            写入向量数据库 + 图数据库 + 原始文档存储                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                        知识库层                                 │
│                                                                 │
│    ┌─────────────────┐        ┌─────────────────┐              │
│    │  Qdrant         │        │  Neo4j          │              │
│    │  (向量数据库)    │        │  (图数据库)      │              │
│    │                 │        │                 │              │
│    │  - 语义向量     │        │  - 实体节点     │              │
│    │  - 文档分块     │        │  - 关系边       │              │
│    │  - 全文检索     │        │  - 路径查询     │              │
│    └─────────────────┘        └─────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                        数据摄入层                               │
│                                                                 │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│    │  Slack  │  │ Notion  │  │  邮件   │  │ 本地文件 │            │
│    └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
│            ↓           ↓           ↓           ↓                │
│    ┌─────────────────────────────────────────────────┐          │
│    │           n8n 工作流自动化摄入                    │          │
│    └─────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent 设计

### 3.1 Orchestrator Agent（编排器）

**职责**：
- 理解用户意图
- 分解任务为子任务
- 调度专业 Agent
- 聚合结果生成响应

**Prompt 设计**：

```
你是一个团队知识助手 orchestrator。

用户输入：{user_input}
当前上下文：{context}

任务：
1. 判断用户意图（问答/添加知识/查询关系/其他）
2. 如果是问答，分解为：检索 → 理解 → 生成
3. 如果是添加知识，分解为：提取 → 理解 → 关联 → 存储
4. 调用相应 Agent

请输出：
- 意图类型
- 子任务列表
- 建议的 Agent 调度顺序
```

### 3.2 Extract Agent（提取器）

**职责**：
- 从非结构化文本中提取实体
- 分类信息类型（决策/任务/讨论/文档）
- 标注信息来源和时间

**输出格式**：

```json
{
  "entities": [
    {"type": "person", "name": "张三", "role": "产品经理"},
    {"type": "project", "name": "用户认证重构"},
    {"type": "decision", "content": "采用 JWT 方案", "reason": "扩展性好"}
  ],
  "info_type": "meeting_notes",
  "source": {"type": "slack", "channel": "#tech-discuss", "timestamp": "2024-01-15"},
  "key_points": ["方案A被否决", "JWT方案通过"]
}
```

### 3.3 Comprehend Agent（理解器）

**职责**：
- 理解语义含义
- 识别隐含意图
- 提取决策点和行动项

**输出格式**：

```json
{
  "summary": "本次会议讨论了用户认证方案，最终决定采用 JWT",
  "decisions": [
    {"content": "采用 JWT 方案", "confidence": 0.95}
  ],
  "action_items": [
    {"task": "更新技术文档", "owner": "李四", "deadline": "2024-01-20"}
  ],
  "sentiment": "positive",
  "key_topics": ["认证", "安全", "扩展性"]
}
```

### 3.4 Relate Agent（关联器）

**职责**：
- 识别实体间关系
- 构建/更新知识图谱
- 维护关联链路

**输出格式**：

```json
{
  "relations": [
    {"from": "JWT方案", "type": "decided_by", "to": "技术评审会议"},
    {"from": "JWT方案", "type": "replaces", "to": "Session方案"},
    {"from": "李四", "type": "responsible_for", "to": "更新技术文档"}
  ],
  "graph_updates": [
    {"operation": "upsert_node", "node_type": "Decision", "id": "jwt_decision_2024"},
    {"operation": "upsert_edge", "from": "jwt_decision", "to": "tech_review", "type": "decided_in"}
  ]
}
```

### 3.5 Store Agent（存储器）

**职责**：
- 向量数据库写入
- 图数据库写入
- 原始文档存储
- 元数据管理

---

## 4. 知识库设计

### 4.1 向量数据库（Qdrant）

**Collection 设计**：

```python
{
    "name": "team_knowledge",
    "vectors": {
        "size": 1536,  # OpenAI embedding size
        "distance": "Cosine"
    },
    "payload_schema": {
        "content": "text",
        "source_type": "slack|notion|email|file",
        "source_id": "message_id or file_path",
        "team_id": "team_uuid",
        "created_at": "timestamp",
        "entities": ["entity_list"],
        "info_type": "decision|task|discussion|document",
        "parent_id": "parent_document_id (for threading)"
    }
}
```

**检索策略**：
- 语义相似度 > 0.8
- 时间衰减：最近 30 天权重 1.0，每过 30 天 -0.1
- 来源权重：团队内部 > 外部引用

### 4.2 图数据库（Neo4j）

**节点类型**：

| 节点类型 | 属性 | 说明 |
|---------|------|------|
| Person | name, role, team | 团队成员 |
| Project | name, status, start_date | 项目 |
| Document | title, type, url | 文档 |
| Decision | content, timestamp, status | 决策 |
| Task | content, owner, deadline, status | 任务 |
| Meeting | title, date, participants | 会议 |
| Message | content, channel, timestamp | 消息 |

**关系类型**：

| 关系 | 说明 |
|------|------|
| (:Person)-[:BELONGS_TO]->(:Team) | 成员归属 |
| (:Decision)-[:MADE_IN]->(:Meeting) | 决策来源 |
| (:Decision)-[:AFFECTS]->(:Project) | 决策影响 |
| (:Decision)-[:SUPERSEDES]->(:Decision) | 决策替代 |
| (:Task)-[:ASSIGNED_TO]->(:Person) | 任务分配 |
| (:Task)-[:PART_OF]->(:Project) | 任务归属 |
| (:Document)-[:DISCUSSED_IN]->(:Meeting) | 文档讨论 |
| (:Person)-[:CONTRIBUTED]->(:Document) | 文档贡献 |

**典型查询**：

```cypher
// 查询某个决策的影响链
MATCH (d:Decision {content: "采用JWT方案"})
-[:AFFECTS|IMPLEMENTED_IN|REVIEWED_BY*1..3]->(affected)
RETURN d, affected

// 查询新成员的上下文
MATCH (p:Person {name: "新成员"})-[*2..3]-(related)
WHERE related:Decision OR related:Project OR related:Document
RETURN DISTINCT related
```

---

## 5. 数据流程

### 5.1 知识添加流程

```
1. 数据源 (Slack/Notion/邮件)
       ↓
2. n8n Webhook 触发
       ↓
3. Orchestrator 接收原始内容
       ↓
4. Extract Agent: 提取实体，分类信息
       ↓
5. Comprehend Agent: 理解语义，识别决策
       ↓
6. Relate Agent: 识别关联，构建图谱边
       ↓
7. Store Agent:
   ├─ Qdrant: 写入向量 + payload
   ├─ Neo4j: 创建/更新节点和边
   └─ 文件存储: 保存原始文档
       ↓
8. 返回存储确认
```

### 5.2 问答流程

```
1. 用户提问
       ↓
2. Query 处理:
   - 改写（同义词扩展）
   - 提取关键词
   - 判断意图类型
       ↓
3. 混合检索:
   ├─ 向量检索 (Qdrant): Top-K 相关文档
   └─ 图检索 (Neo4j): 相关实体路径
       ↓
4. 上下文组装:
   - 合并检索结果
   - 去重和排序
   - 构建 Prompt
       ↓
5. LLM 生成:
   - 基于上下文生成答案
   - 标注信息来源
   - 推荐相关问题
       ↓
6. 返回结果 + 引用
```

---

## 6. 错误处理

### 6.1 Agent 失败策略

| 场景 | 策略 |
|------|------|
| 单个 Agent 超时 | 重试 2 次，失败则返回部分结果 |
| LLM API 不可用 | 降级到规则匹配 |
| 向量数据库不可用 | 仅使用图数据库检索 |
| 图数据库不可用 | 仅使用向量检索 |

### 6.2 数据一致性

- 向量库和图库使用异步写入
- 写入前检查重复（基于 source_id）
- 定期一致性校验任务

---

## 7. 安全设计

### 7.1 数据安全

- 本地数据 AES-256 加密
- LLM API 调用仅传输 Embedding
- 敏感信息自动脱敏

### 7.2 访问控制

- 团队级数据隔离
- 角色基础访问控制（RBAC）
- API 密钥管理

---

## 8. 部署架构

### 8.1 本地开发

```bash
docker-compose up  # Qdrant + Neo4j
pip install -r requirements.txt
export ANTHROPIC_API_KEY=xxx
cd demo && streamlit run app.py
```

### 8.2 生产部署

```
┌─────────────────────────────────────────────────────────┐
│                      Cloudflare                         │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│   │   Tunnel    │  │   Pages     │  │   R2         │   │
│   │  (API)      │  │  (前端)     │  │ (文件存储)   │   │
│   └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────┐
│                      用户服务器                          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│   │  FastAPI    │  │  Qdrant     │  │  Neo4j      │   │
│   │  (后端)     │  │  (向量库)   │  │  (图库)     │   │
│   └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 9. 扩展计划

### 9.1 v2.0 功能

- [ ] 多团队支持
- [ ] 实时协作编辑
- [ ] Slack/飞书 Bot 集成
- [ ] WebDAV 文件同步

### 9.2 v3.0 功能

- [ ] 本地 LLM 支持（Llama/Ollama）
- [ ] 离线模式
- [ ] 团队知识图谱可视化
- [ ] 自动化知识更新提醒

---

*文档版本：v0.1.0 | 最后更新：2024-01-15*
