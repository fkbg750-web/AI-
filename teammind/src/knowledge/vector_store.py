"""
Vector Store - 向量数据库接口
基于 Qdrant 实现语义检索
"""
from typing import Optional
from datetime import datetime
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class VectorStore:
    """
    向量数据库存储和检索

    功能：
    1. 存储文档向量和元数据
    2. 语义相似度检索
    3. 混合检索（向量 + 关键词）
    """

    COLLECTION_NAME = "team_knowledge"
    VECTOR_SIZE = 1536  # OpenAI embedding size

    def __init__(self, qdrant_url: str, qdrant_port: int = 6333, openai_api_key: Optional[str] = None):
        """
        初始化向量存储

        Args:
            qdrant_url: Qdrant 服务地址
            qdrant_port: Qdrant 端口
            openai_api_key: OpenAI API Key（用于生成 Embedding）
        """
        self.client = QdrantClient(url=qdrant_url, port=qdrant_port)
        self._openai_client = None

        if openai_api_key and OpenAI:
            self._openai_client = OpenAI(api_key=openai_api_key)

        # 确保 Collection 存在
        self._ensure_collection()

    def _ensure_collection(self):
        """确保 Collection 存在"""
        try:
            self.client.get_collection(self.COLLECTION_NAME)
        except (UnexpectedResponse, Exception):
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )

    async def get_embedding(self, text: str) -> list[float]:
        """
        获取文本的 Embedding 向量

        Args:
            text: 待嵌入的文本

        Returns:
            list[float]: 向量
        """
        if self._openai_client:
            response = self._openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        else:
            # 降级：返回随机向量（仅用于开发测试）
            import random
            return [random.random() for _ in range(self.VECTOR_SIZE)]

    async def insert(
        self,
        content: str,
        payload: dict,
        vector: Optional[list[float]] = None
    ) -> str:
        """
        插入文档

        Args:
            content: 文档内容
            payload: 元数据
            vector: 预计算的向量（如果为 None，自动生成）

        Returns:
            str: 文档 ID
        """
        # 生成向量
        if vector is None:
            vector = await self.get_embedding(content)

        # 生成 ID
        doc_id = str(uuid.uuid4())

        # 添加时间戳
        payload["created_at"] = payload.get("created_at", datetime.now().isoformat())

        # 构建点
        point = PointStruct(
            id=doc_id,
            vector=vector,
            payload=payload
        )

        # 插入
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[point]
        )

        return doc_id

    async def search(
        self,
        query: str,
        limit: int = 5,
        filter_conditions: Optional[dict] = None,
        score_threshold: float = 0.7
    ) -> list[dict]:
        """
        语义检索

        Args:
            query: 查询文本
            limit: 返回数量
            filter_conditions: 过滤条件
            score_threshold: 最低相似度分数

        Returns:
            list[dict]: 检索结果
        """
        # 生成查询向量
        query_vector = await self.get_embedding(query)

        # 执行搜索
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=filter_conditions
        )

        # 格式化结果
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "content": hit.payload.get("content", ""),
                "info_type": hit.payload.get("info_type", "unknown"),
                "source": hit.payload.get("source", {}),
                "summary": hit.payload.get("summary", ""),
                "key_points": hit.payload.get("key_points", []),
                "decisions": hit.payload.get("decisions", []),
                "created_at": hit.payload.get("created_at", "")
            }
            for hit in results
        ]

    async def hybrid_search(
        self,
        query: str,
        limit: int = 5,
        info_types: Optional[list[str]] = None,
        date_range: Optional[tuple[str, str]] = None
    ) -> list[dict]:
        """
        混合检索（结合过滤条件）

        Args:
            query: 查询文本
            limit: 返回数量
            info_types: 信息类型过滤
            date_range: 日期范围过滤

        Returns:
            list[dict]: 检索结果
        """
        # 构建过滤条件
        must_conditions = []

        if info_types:
            must_conditions.append({
                "key": "info_type",
                "match": {"any": info_types}
            })

        if date_range:
            must_conditions.append({
                "key": "created_at",
                "range": {
                    "gte": date_range[0],
                    "lte": date_range[1]
                }
            })

        filter_conditions = {"must": must_conditions} if must_conditions else None

        return await self.search(
            query=query,
            limit=limit,
            filter_conditions=filter_conditions
        )

    async def delete(self, doc_id: str) -> bool:
        """
        删除文档

        Args:
            doc_id: 文档 ID

        Returns:
            bool: 是否成功
        """
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[doc_id]
            )
            return True
        except Exception:
            return False

    async def count(self) -> int:
        """获取文档总数"""
        info = self.client.get_collection(self.COLLECTION_NAME)
        return info.points_count
