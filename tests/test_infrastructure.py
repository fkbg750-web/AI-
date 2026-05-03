"""
Infrastructure and local fallback tests.
"""
import pytest

from src.agents.fallback_client import RuleBasedClient
from src.agents.orchestrator import IntentType, OrchestratorAgent
from src.agents.utils import parse_json_object
from src.ingestion.processor import SourceDocument, chunk_text
from src.knowledge.graph_store import GraphStore


def test_parse_json_object_from_fenced_response():
    result = parse_json_object('```json\n{"intent": "query"}\n```')

    assert result == {"intent": "query"}


def test_chunk_text_preserves_content_with_overlap():
    chunks = chunk_text("abcdefghij", chunk_size=4, overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=4, overlap=4)


def test_source_document_defaults():
    document = SourceDocument(content="会议纪要")

    assert document.source_type == "manual"
    assert document.created_at


def test_graph_store_sanitizes_cypher_identifiers():
    assert GraphStore._safe_label("Decision-Type") == "Decision_Type"
    assert GraphStore._safe_label("123", "Entity") == "Entity"


@pytest.mark.asyncio
async def test_rule_based_orchestrator_store_without_backend():
    orchestrator = OrchestratorAgent(anthropic_client=RuleBasedClient())

    result = await orchestrator.process("记录：张三负责更新技术文档")

    assert result.success is True
    assert result.intent == IntentType.STORE
    assert "未配置存储后端" in result.final_response


@pytest.mark.asyncio
async def test_rule_based_orchestrator_query():
    orchestrator = OrchestratorAgent(anthropic_client=RuleBasedClient())

    result = await orchestrator.process("谁负责更新技术文档？")

    assert result.success is True
    assert result.intent == IntentType.QUERY
    assert result.answer
