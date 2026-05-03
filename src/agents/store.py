"""
Store Agent - 知识存储器
将处理后的信息写入向量数据库和图数据库
"""
import json
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - used when running mocked tests without deps
    Anthropic = object

if TYPE_CHECKING:
    from src.knowledge.vector_store import VectorStore
    from src.knowledge.graph_store import GraphStore


@dataclass
class StorageResult:
    """存储结果"""
    vector_stored: bool
    graph_stored: bool
    vector_id: Optional[str] = None
    graph_ids: list[str] = field(default_factory=list)
    error: Optional[str] = None


class StoreAgent:
    """
    存储 Agent

    职责：
    1. 将文本内容 Embedding 后存入向量数据库
    2. 创建/更新图数据库节点和边
    3. 保存原始文档引用
    4. 维护元数据索引
    """

    def __init__(
        self,
        anthropic_client: Anthropic,
        vector_store: 'VectorStore',
        graph_store: 'GraphStore'
    ):
        self.client = anthropic_client
        self.vector_store = vector_store
        self.graph_store = graph_store

    async def process(
        self,
        content: str,
        extract_result: dict,
        comprehend_result: dict,
        relate_result: dict,
        metadata: Optional[dict] = None
    ) -> StorageResult:
        """
        存储处理后的知识

        Args:
            content: 原始内容
            extract_result: 提取结果
            comprehend_result: 理解结果
            relate_result: 关联结果
            metadata: 额外元数据

        Returns:
            StorageResult: 存储结果
        """
        result = StorageResult(
            vector_stored=False,
            graph_stored=False
        )

        # 1. 存储到向量数据库
        try:
            vector_id = await self._store_to_vector(
                content=content,
                extract_result=extract_result,
                comprehend_result=comprehend_result,
                metadata=metadata
            )
            result.vector_id = vector_id
            result.vector_stored = True
        except Exception as e:
            result.error = f"Vector storage failed: {str(e)}"

        # 2. 存储到图数据库
        try:
            graph_ids = await self._store_to_graph(
                extract_result=extract_result,
                comprehend_result=comprehend_result,
                relate_result=relate_result
            )
            result.graph_ids = graph_ids
            result.graph_stored = True
        except Exception as e:
            if result.error:
                result.error += f"; Graph storage failed: {str(e)}"
            else:
                result.error = f"Graph storage failed: {str(e)}"

        return result

    async def _store_to_vector(
        self,
        content: str,
        extract_result: dict,
        comprehend_result: dict,
        metadata: Optional[dict] = None
    ) -> str:
        """
        存储到向量数据库

        Args:
            content: 原始内容
            extract_result: 提取结果
            comprehend_result: 理解结果
            metadata: 额外元数据

        Returns:
            str: 存储 ID
        """
        # 构建 payload
        payload = {
            "content": content,
            "info_type": extract_result.get("info_type", "discussion"),
            "entities": extract_result.get("entities", []),
            "key_points": extract_result.get("key_points", []),
            "summary": comprehend_result.get("summary", ""),
            "decisions": comprehend_result.get("decisions", []),
            "action_items": comprehend_result.get("action_items", []),
            "key_topics": comprehend_result.get("key_topics", []),
            "source": metadata or {},
            "created_at": datetime.now().isoformat()
        }

        # 使用向量存储
        vector_id = await self.vector_store.insert(
            content=content,
            payload=payload
        )

        return vector_id

    async def _store_to_graph(
        self,
        extract_result: dict,
        comprehend_result: dict,
        relate_result: dict
    ) -> list[str]:
        """
        存储到图数据库

        Args:
            extract_result: 提取结果
            comprehend_result: 理解结果
            relate_result: 关联结果

        Returns:
            list[str]: 创建的节点/关系 ID 列表
        """
        ids = []

        # 1. 创建/更新实体节点
        for entity in extract_result.get("entities", []):
            node_id = await self.graph_store.upsert_node(
                node_type=entity.get("type", "Entity"),
                node_id=entity.get("name", ""),
                properties={
                    "name": entity.get("name", ""),
                    **entity.get("properties", {})
                }
            )
            if node_id:
                ids.append(node_id)

        # 2. 创建决策节点
        for decision in comprehend_result.get("decisions", []):
            node_id = await self.graph_store.upsert_node(
                node_type="Decision",
                node_id=f"decision_{hash(decision.get('content', ''))}",
                properties={
                    "content": decision.get("content", ""),
                    "confidence": decision.get("confidence", 0.5),
                    "reason": decision.get("reason", ""),
                    "created_at": datetime.now().isoformat()
                }
            )
            if node_id:
                ids.append(node_id)

        # 3. 创建任务节点
        for action in comprehend_result.get("action_items", []):
            node_id = await self.graph_store.upsert_node(
                node_type="Task",
                node_id=f"task_{hash(action.get('task', ''))}",
                properties={
                    "content": action.get("task", ""),
                    "owner": action.get("owner", ""),
                    "deadline": action.get("deadline", ""),
                    "priority": action.get("priority", "medium"),
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }
            )
            if node_id:
                ids.append(node_id)

        # 4. 创建关系
        for relation in relate_result.get("relations", []):
            edge_id = await self.graph_store.upsert_edge(
                from_node=relation.get("from", ""),
                to_node=relation.get("to", ""),
                edge_type=relation.get("type", "RELATED_TO"),
                properties=relation.get("properties", {})
            )
            if edge_id:
                ids.append(edge_id)

        return ids

    def to_dict(self, result: StorageResult) -> dict:
        """转换为可序列化格式"""
        return {
            "vector_stored": result.vector_stored,
            "graph_stored": result.graph_stored,
            "vector_id": result.vector_id,
            "graph_ids": result.graph_ids,
            "error": result.error
        }

