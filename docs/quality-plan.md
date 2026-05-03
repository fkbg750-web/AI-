# TeamMind 质量提升计划书

## 一、现状分析

### 1.1 已有基础

| 类别 | 现状 | 评分 |
|------|------|------|
| 单元测试 | Agent 基础测试（mock LLM）| ⭐⭐ |
| 代码规范 | ruff + mypy 配置完成 | ⭐⭐⭐ |
| CI/CD | GitHub Actions 基础配置 | ⭐⭐⭐ |
| 文档 | README + ARCHITECTURE + DESIGN | ⭐⭐⭐ |

### 1.2 待提升项

- Integration Test：未覆盖（无真实数据库测试）
- E2E Test：未覆盖（无端到端流程测试）
- 测试覆盖率：< 30%
- 错误处理：未系统化
- 性能基准：未建立

---

## 二、质量提升计划

### Phase 1：测试体系完善（预计 3-5 天）

#### 1.1 单元测试增强

**目标**：覆盖率提升至 60%+

```
tests/
├── unit/                    # 单元测试（已有）
│   ├── test_agents.py
│   └── conftest.py
├── integration/              # 集成测试（新增）
│   ├── test_vector_store.py
│   ├── test_graph_store.py
│   └── test_agent_pipeline.py
└── e2e/                     # 端到端测试（新增）
    └── test_full_flow.py
```

**任务清单**：

- [ ] `tests/unit/test_knowledge.py` — VectorStore / GraphStore 单元测试
- [ ] `tests/unit/test_cli.py` — CLI 命令行测试
- [ ] `tests/integration/test_qdrant.py` — Qdrant 真实连接测试
- [ ] `tests/integration/test_neo4j.py` — Neo4j 真实连接测试
- [ ] `tests/e2e/test_ingest_flow.py` — 摄入 → 存储全流程测试
- [ ] `tests/e2e/test_query_flow.py` — 问答全流程测试

#### 1.2 Integration Test 实现

```python
# tests/integration/test_vector_store.py 示例
import pytest
from qdrant_client import QdrantClient

@pytest.fixture(scope="module")
def qdrant_client():
    client = QdrantClient(host="localhost", port=6333)
    yield client
    # cleanup

class TestVectorStore:
    """Qdrant 集成测试"""

    @pytest.fixture(autouse=True)
    def setup_collection(self, qdrant_client):
        collection_name = "test_knowledge"
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        yield
        qdrant_client.delete_collection(collection_name)

    def test_upsert_and_retrieve(self, qdrant_client):
        """测试写入和检索"""
        # 写入向量
        qdrant_client.upsert(
            collection_name="test_knowledge",
            points=[
                PointStruct(id=1, vector=[0.1]*1536, payload={"text": "测试"})
            ]
        )
        # 检索
        results = qdrant_client.search(
            collection_name="test_knowledge",
            query_vector=[0.1]*1536,
            limit=1
        )
        assert len(results) == 1
        assert results[0].payload["text"] == "测试"
```

#### 1.3 E2E Test 实现

```python
# tests/e2e/test_ingest_flow.py 示例
class TestIngestFlow:
    """端到端摄入流程测试"""

    @pytest.fixture(autouse=True)
    def setup_system(self):
        """初始化真实系统"""
        vector_store = VectorStore()  # 真实连接
        graph_store = GraphStore()    # 真实连接
        orchestrator = OrchestratorAgent(
            vector_store=vector_store,
            graph_store=graph_store
        )
        self.orchestrator = orchestrator
        yield
        # cleanup

    @pytest.mark.asyncio
    async def test_meeting_notes_to_knowledge(self):
        """会议纪要 → 知识存储"""
        meeting_content = """
        会议主题：认证方案评审
        参与人：张三、李四

        讨论：
        - 李四提议使用 Session 方案
        - 张三建议 JWT 方案
        - 最终决定：采用 JWT

        任务：
        - 张三负责实现 JWT 模块
        """

        result = await self.orchestrator.process(meeting_content)

        assert result.success is True
        # 验证向量存储
        vectors = self.vector_store.search("认证方案", limit=5)
        assert len(vectors) > 0
        # 验证图存储
        graph = self.graph_store.get_entities_by_type("Decision")
        assert any("JWT" in str(e) for e in graph)
```

---

### Phase 2：错误处理与边界情况（预计 2-3 天）

#### 2.1 错误分类体系

```python
# src/exceptions.py
class TeamMindError(Exception):
    """基础异常"""
    pass

class LLMError(TeamMindError):
    """LLM 调用失败"""
    pass

class VectorStoreError(TeamMindError):
    """向量存储错误"""
    pass

class GraphStoreError(TeamMindError):
    """图数据库错误"""
    pass

class ValidationError(TeamMindError):
    """数据验证错误"""
    pass

class RateLimitError(LLMError):
    """API 限流"""
    pass
```

#### 2.2 重试机制

```python
# src/utils/retry.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def call_llm_with_retry(client, messages):
    """LLM 调用（含重试）"""
    try:
        return await client.messages.create(messages=messages)
    except RateLimitError:
        raise  # 让 tenacity 重试
    except APIError as e:
        if e.is_retryable:
            raise
        raise LLMError(f"不可重试的错误: {e}") from e
```

#### 2.3 降级策略

```python
class HybridRetrieval:
    """混合检索（带降级）"""

    async def search(self, query: str):
        vector_result = None
        graph_result = None

        # 向量检索失败不影响图检索
        try:
            vector_result = await self.vector_store.search(query)
        except VectorStoreError as e:
            logger.warning(f"向量检索失败: {e}")

        try:
            graph_result = await self.graph_store.search(query)
        except GraphStoreError as e:
            logger.warning(f"图检索失败: {e}")

        # 至少有一个成功
        if vector_result is None and graph_result is None:
            raise RetrievalError("向量和图检索均失败")

        return self.fuse_results(vector_result, graph_result)
```

#### 2.4 测试用例

- [ ] `tests/unit/test_exceptions.py` — 异常体系测试
- [ ] `tests/unit/test_retry.py` — 重试机制测试
- [ ] `tests/unit/test_degradation.py` — 降级策略测试
- [ ] `tests/integration/test_error_handling.py` — 真实环境错误处理

---

### Phase 3：性能与监控（预计 2 天）

#### 3.1 性能基准

```python
# benchmarks/test_performance.py
import time
import pytest

class TestPerformanceBenchmarks:
    """性能基准测试"""

    @pytest.mark.asyncio
    async def test_extraction_latency(self):
        """实体提取延迟 < 2s"""
        start = time.time()
        result = await extract_agent.extract(SAMPLE_MEETING)
        latency = time.time() - start
        assert latency < 2.0, f"提取延迟 {latency}s 超过 2s"

    @pytest.mark.asyncio
    async def test_vector_search_latency(self):
        """向量检索延迟 < 100ms"""
        start = time.time()
        results = await vector_store.search("认证方案", limit=10)
        latency = time.time() - start
        assert latency < 0.1, f"检索延迟 {latency}s 超过 100ms"

    @pytest.mark.asyncio
    async def test_graph_traversal_latency(self):
        """图遍历延迟 < 200ms（3跳）"""
        start = time.time()
        results = await graph_store.traverse("JWT", depth=3)
        latency = time.time() - start
        assert latency < 0.2, f"图遍历 {latency}s 超过 200ms"
```

#### 3.2 监控指标

```python
# src/monitoring.py
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class Metrics:
    """监控指标"""
    request_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0

    @property
    def avg_latency(self) -> float:
        return self.total_latency / self.request_count if self.request_count else 0

    @property
    def error_rate(self) -> float:
        return self.error_count / self.request_count if self.request_count else 0

class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.vector_store_metrics = Metrics()
        self.graph_store_metrics = Metrics()
        self.llm_metrics = Metrics()

    def record_vector_search(self, latency: float, error: Optional[Exception] = None):
        self.vector_store_metrics.request_count += 1
        self.vector_store_metrics.total_latency += latency
        if error:
            self.vector_store_metrics.error_count += 1

    def export_prometheus(self) -> str:
        """导出 Prometheus 格式"""
        return f"""
# HELP teammind_vector_requests_total Total vector requests
# TYPE teammind_vector_requests_total counter
teammind_vector_requests_total {self.vector_store_metrics.request_count}
"""
```

---

### Phase 4：代码质量（持续）

#### 4.1 Pre-commit 配置

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.8
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

#### 4.2 Coverage 目标

| 阶段 | 覆盖率目标 | 关键文件 |
|------|-----------|----------|
| 当前 | 30% | Agent 核心 |
| Phase 1 完成后 | 60% | + Knowledge + Utils |
| Phase 2 完成后 | 80% | + Error Handling |
| 最终目标 | 90% | 全覆盖 |

---

## 三、实施时间线

```
Week 1: Phase 1（测试体系）
├─ Day 1-2: 单元测试增强
├─ Day 3-4: Integration Test
└─ Day 5: E2E Test + Coverage Report

Week 2: Phase 2（错误处理）
├─ Day 1-2: 异常体系 + 重试机制
└─ Day 3: 降级策略 + 测试

Week 3: Phase 3（性能监控）
├─ Day 1: 性能基准测试
└─ Day 2: 监控埋点 + Dashboard

Week 4+: Phase 4（持续改进）
└─ Pre-commit + Coverage Gate + Code Review
```

---

## 四、验收标准

### 测试覆盖
- [ ] 单元测试覆盖率 ≥ 60%
- [ ] Integration Test 覆盖所有存储层
- [ ] E2E Test 覆盖核心流程

### 错误处理
- [ ] 所有异常有明确分类
- [ ] LLM 调用有重试机制
- [ ] 混合检索有降级策略

### 性能
- [ ] 提取延迟 < 2s
- [ ] 向量检索 < 100ms
- [ ] 图遍历 < 200ms

### CI/CD
- [ ] PR 必须通过所有测试
- [ ] Coverage 下降触发 CI 失败
- [ ] Type check 必须通过

---

## 五、资源估算

| 任务 | 预估工时 | 优先级 |
|------|----------|--------|
| 单元测试增强 | 1-2 天 | P0 |
| Integration Test | 1-2 天 | P0 |
| E2E Test | 1 天 | P1 |
| 错误处理 | 2 天 | P1 |
| 性能基准 | 1 天 | P2 |
| 监控埋点 | 1 天 | P2 |
| Pre-commit + CI | 0.5 天 | P0 |

**总计：7.5 天（约 2 周）**

---

## 六、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| Integration Test 环境不稳定 | 测试结果不可靠 | Docker Compose 固定版本 |
| 性能测试受网络影响 | 基准不准 | 内网测试 + 多次取平均值 |
| 覆盖率目标过高 | 团队压力 | 分阶段目标，灵活调整 |
| LLM Mock 难以覆盖真实场景 | 测试有效性低 | Integration Test 使用真实 LLM |

---

## 七、后续规划

质量体系完成后，可进入：

1. **功能迭代**：Slack/Notion 摄入、多轮对话
2. **安全加固**：输入校验、SQL 注入防护、API 认证
3. **可观测性**：结构化日志、分布式追踪
4. **文档自动化**：API 文档自动生成、代码注释生成
