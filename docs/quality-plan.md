# TeamMind 质量提升计划

## 当前基线

TeamMind 现在具备一个可运行的工程基线：

- `python -m compileall -q src demo tests` 通过
- `ruff check src tests` 通过
- `mypy src` 通过
- `python -m pytest --cov=src tests -q -p no:cacheprovider` 通过
- 当前测试数：13
- 当前覆盖率：53%

## 已完成

- 修复 CLI 与 Streamlit Demo 的语法问题
- 统一 Agent 的 `process()` / 语义化方法入口
- 增加 Orchestrator 的最小 Store / Query 编排
- 增加本地规则 fallback client，便于无 API Key 的 smoke test
- 修复 Neo4j 动态 Label / Relationship 的 Cypher 写法
- 将 OpenAI 缺失时的向量 fallback 改为确定性伪向量
- 增加 FastAPI `health` / `plan` / `query` 最小入口
- 增加 ingestion 文本切分工具
- 增加基础设施测试

## 下一阶段目标

### P0：核心链路

- 为 StoreAgent 增加完整单元测试
- 增加 VectorStore / GraphStore 的 mock 单元测试
- 增加本地 Docker Compose 集成测试
- 将 Orchestrator 的 query 流程升级为真正的 hybrid retrieval

### P1：生产可用性

- 增加 API 鉴权与请求校验
- 增加结构化日志
- 增加错误类型和重试策略
- 增加 Slack / Notion 摄入适配器

### P2：体验与部署

- 增加 Streamlit 与 API 的真实连接
- 增加 GitHub Actions coverage artifact
- 增加示例数据导入脚本
- 增加部署说明和环境变量矩阵

## 验收标准

- 单元测试覆盖率达到 70%+
- Store / Query 两条主流程均有端到端测试
- Docker Compose 下 Qdrant 和 Neo4j 集成测试通过
- README 中所有命令可复制执行
