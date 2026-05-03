"""
Agent Tests
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.extractor import ExtractAgent, Entity, ExtractResult
from src.agents.comprehender import ComprehendAgent, Decision, ActionItem
from src.agents.relater import RelateAgent, Relation
from src.agents.orchestrator import OrchestratorAgent, IntentType


class TestExtractAgent:
    """Extract Agent 测试"""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"entities": [], "info_type": "discussion", "key_points": []}')]
        ))
        return client

    @pytest.fixture
    def agent(self, mock_client):
        return ExtractAgent(anthropic_client=mock_client)

    @pytest.mark.asyncio
    async def test_extract_basic(self, agent):
        """测试基本提取功能"""
        result = await agent.extract("张三负责更新技术文档")

        assert isinstance(result, ExtractResult)
        assert result.info_type in ["discussion", "decision", "task", "project"]

    @pytest.mark.asyncio
    async def test_extract_entities(self, agent):
        """测试实体提取"""
        result = await agent.extract("李四和王五讨论了微服务架构")

        # 验证实体提取
        assert isinstance(result.entities, list)


class TestComprehendAgent:
    """Comprehend Agent 测试"""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"summary": "测试摘要", "decisions": [], "action_items": [], "key_topics": []}')]
        ))
        return client

    @pytest.fixture
    def agent(self, mock_client):
        return ComprehendAgent(anthropic_client=mock_client)

    @pytest.mark.asyncio
    async def test_comprehend_basic(self, agent):
        """测试基本理解功能"""
        entities = [
            Entity(name="张三", type="Person", properties={})
        ]

        result = await agent.comprehend(
            content="我们决定采用 JWT 方案",
            entities=entities
        )

        assert isinstance(result.summary, str)
        assert isinstance(result.decisions, list)


class TestRelateAgent:
    """Relate Agent 测试"""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"relations": [], "graph_updates": []}')]
        ))
        return client

    @pytest.fixture
    def agent(self, mock_client):
        return RelateAgent(anthropic_client=mock_client)

    @pytest.mark.asyncio
    async def test_relate_basic(self, agent):
        """测试基本关联功能"""
        entities = [
            Entity(name="JWT", type="Decision", properties={}),
            Entity(name="认证", type="Project", properties={})
        ]
        summary = "采用 JWT 实现认证"

        result = await agent.relate(entities=entities, summary=summary)

        assert isinstance(result.relations, list)


class TestOrchestratorAgent:
    """Orchestrator Agent 测试"""

    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.messages.create = AsyncMock(return_value=MagicMock(
            content=[MagicMock(text='{"intent": "store", "reasoning": "存储知识"}')]
        ))
        return client

    @pytest.fixture
    def agent(self, mock_client):
        store_agent = MagicMock()
        store_agent.process = AsyncMock(return_value=MagicMock(
            vector_stored=True,
            graph_stored=True
        ))
        return OrchestratorAgent(
            anthropic_client=mock_client,
            store_agent=store_agent
        )

    @pytest.mark.asyncio
    async def test_orchestrate_store(self, agent):
        """测试存储流程"""
        result = await agent.process("张三负责更新文档")

        assert result.success is True
        assert result.intent == IntentType.STORE

    @pytest.mark.asyncio
    async def test_orchestrate_query(self, agent):
        """测试查询流程"""
        agent.store_agent = None  # 模拟无存储
        result = await agent.query("我们采用了什么方案？")

        assert result.success is True
        assert result.intent == IntentType.QUERY
