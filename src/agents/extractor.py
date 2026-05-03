"""
Extract Agent - 信息提取器
从非结构化文本中提取实体和关键信息
"""
from dataclasses import dataclass, field
from datetime import datetime

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - used when running mocked tests without deps
    Anthropic = object

from src.agents.utils import maybe_await, normalize_entity_type, parse_json_object


@dataclass
class Entity:
    """实体"""
    type: str  # person, project, decision, task, document, meeting
    name: str
    properties: dict = field(default_factory=dict)


@dataclass
class ExtractResult:
    """提取结果"""
    entities: list[Entity]
    info_type: str  # decision, task, discussion, document, meeting
    source: dict
    key_points: list[str]
    raw_output: dict


class ExtractAgent:
    """
    提取 Agent

    职责：
    1. 从文本中提取命名实体
    2. 分类信息类型
    3. 标注信息来源
    4. 提取关键要点
    """

    SYSTEM_PROMPT = """你是一个专业的信息提取 Agent。

从给定的文本中提取：
1. **实体**：人名、项目名、决策、任务、文档、会议等
2. **信息类型**：decision（决策）、task（任务）、discussion（讨论）、document（文档）、meeting（会议）
3. **关键要点**：3-5 个核心信息点

输出格式（JSON）：
{
    "entities": [
        {
            "type": "person|project|decision|task|document|meeting",
            "name": "实体名称",
            "properties": {"role": "职位", "status": "状态", ...}
        }
    ],
    "info_type": "decision|task|discussion|document|meeting",
    "key_points": ["要点1", "要点2", "要点3"],
    "confidence": 0.95
}

请直接输出 JSON，不要有其他内容。"""

    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client

    async def process(
        self,
        content: str,
        source_type: str = "unknown",
        source_id: str = "",
        metadata: dict | None = None
    ) -> ExtractResult:
        """
        提取文本中的实体和信息

        Args:
            content: 待处理的文本内容
            source_type: 来源类型（slack, notion, email, file）
            source_id: 来源 ID
            metadata: 额外元数据

        Returns:
            ExtractResult: 提取结果
        """
        # 调用 LLM 提取
        response = await maybe_await(self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}]
        ))

        result_text = response.content[0].text

        try:
            result_json = parse_json_object(result_text)
        except (ValueError, TypeError):
            # 降级处理
            return self._fallback_extract(content, source_type, source_id)

        # 构建实体列表
        entities = []
        for ent_data in result_json.get("entities", []):
            entities.append(Entity(
                type=normalize_entity_type(ent_data.get("type", "Entity")),
                name=ent_data.get("name", ""),
                properties=ent_data.get("properties", {})
            ))

        # 构建来源信息
        source = {
            "type": source_type,
            "id": source_id,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        return ExtractResult(
            entities=entities,
            info_type=result_json.get("info_type", "discussion"),
            source=source,
            key_points=result_json.get("key_points", []),
            raw_output=result_json
        )

    async def extract(
        self,
        content: str,
        source_type: str = "unknown",
        source_id: str = "",
        metadata: dict | None = None
    ) -> ExtractResult:
        """Semantic alias for the unified process entrypoint."""
        return await self.process(content, source_type, source_id, metadata)

    def _fallback_extract(
        self,
        content: str,
        source_type: str,
        source_id: str
    ) -> ExtractResult:
        """降级提取：简单正则匹配"""
        # 简单实现：仅提取关键点
        sentences = content.split("。")
        key_points = [s.strip() for s in sentences if len(s.strip()) > 10][:5]

        return ExtractResult(
            entities=[],
            info_type="discussion",
            source={
                "type": source_type,
                "id": source_id,
                "timestamp": datetime.now().isoformat()
            },
            key_points=key_points,
            raw_output={}
        )

    def to_dict(self, result: ExtractResult) -> dict:
        """转换为可序列化格式"""
        return {
            "entities": [
                {"type": e.type, "name": e.name, "properties": e.properties}
                for e in result.entities
            ],
            "info_type": result.info_type,
            "source": result.source,
            "key_points": result.key_points
        }
