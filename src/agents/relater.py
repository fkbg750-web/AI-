"""
Relate Agent - 关系关联器
识别实体间关系，构建和更新知识图谱
"""
import json
from dataclasses import dataclass, field

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - used when running mocked tests without deps
    Anthropic = object

from src.agents.utils import maybe_await, parse_json_object, to_plain_dict


@dataclass
class Relation:
    """关系"""
    from_entity: str
    to_entity: str
    relation_type: str  # decided_by, affects, assigned_to, part_of, etc.
    properties: dict = field(default_factory=dict)


@dataclass
class GraphUpdate:
    """图谱更新操作"""
    operation: str  # upsert_node, upsert_edge, delete_node
    node_type: str | None = None
    node_id: str | None = None
    properties: dict | None = None
    from_node: str | None = None
    to_node: str | None = None
    edge_type: str | None = None


@dataclass
class RelateResult:
    """关联结果"""
    relations: list[Relation]
    graph_updates: list[GraphUpdate]
    new_nodes: list[dict]
    confidence: float


class RelateAgent:
    """
    关联 Agent

    职责：
    1. 分析实体间的语义关系
    2. 识别关系类型（决定、影响、归属等）
    3. 生成图数据库操作指令
    4. 构建实体关联链路
    """

    SYSTEM_PROMPT = """你是一个专业的知识图谱关联 Agent。

给定一组实体和理解结果，识别它们之间的关系：

**关系类型**：
- decided_by: 决策由某会议/讨论产生
- affects: 影响某个项目/任务
- supersedes: 替代某个旧决策
- assigned_to: 任务分配给某人
- part_of: 属于某个项目/文档
- discussed_in: 在某会议/讨论中被提及
- contributed: 某人对文档有贡献
- related_to: 一般关联

**输出格式（JSON）**：
{
    "relations": [
        {
            "from_entity": "实体A",
            "to_entity": "实体B",
            "relation_type": "decided_by|affects|assigned_to|part_of|discussed_in|contributed|related_to",
            "properties": {"weight": 0.9, "note": "说明"}
        }
    ],
    "new_nodes": [
        {
            "node_type": "Decision|Person|Project|Task",
            "node_id": "唯一ID",
            "properties": {"name": "名称", "status": "状态"}
        }
    ],
    "confidence": 0.85,
    "reasoning": "关联推理过程"
}

请直接输出 JSON，不要有其他内容。"""

    # 常见关系类型映射
    RELATION_TYPE_MAP = {
        "decides": "decided_by",
        "decided_in": "decided_by",
        "affects": "affects",
        "impacts": "affects",
        "replaces": "supersedes",
        "supersedes": "supersedes",
        "assigns": "assigned_to",
        "assigned_to": "assigned_to",
        "belongs_to": "part_of",
        "part_of": "part_of",
        "mentioned_in": "discussed_in",
        "discussed_in": "discussed_in",
        "writes": "contributed",
        "contributed": "contributed",
        "related": "related_to",
        "related_to": "related_to"
    }

    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client

    async def process(
        self,
        entities: list[dict],
        comprehend_result: dict,
        existing_context: dict | None = None
    ) -> RelateResult:
        """
        分析实体关系

        Args:
            entities: 实体列表
            comprehend_result: 理解结果（包含决策、行动项等）
            existing_context: 现有上下文（已有的图谱节点）

        Returns:
            RelateResult: 关联结果
        """
        # 构建输入
        context = ""
        if existing_context:
            context = f"\n\n现有上下文（相关节点）：{json.dumps(existing_context, ensure_ascii=False, indent=2)}\n"

        prompt = f"""请分析以下实体和理解结果，识别实体间的关系：

**实体列表**：
{json.dumps(entities, ensure_ascii=False, indent=2)}

**理解结果**：
{json.dumps(comprehend_result, ensure_ascii=False, indent=2)}
{context}

请识别所有有意义的关系，并生成图谱更新指令。"""

        response = await maybe_await(self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        ))

        result_text = response.content[0].text

        try:
            result_json = parse_json_object(result_text)
        except (ValueError, TypeError):
            return self._fallback_relate(entities, comprehend_result)

        # 构建关系列表
        relations = [
            Relation(
                from_entity=r.get("from_entity", ""),
                to_entity=r.get("to_entity", ""),
                relation_type=self.RELATION_TYPE_MAP.get(
                    r.get("relation_type", "related_to"),
                    r.get("relation_type", "related_to")
                ),
                properties=r.get("properties", {})
            )
            for r in result_json.get("relations", [])
        ]

        # 构建图谱更新指令
        graph_updates = []
        for update in result_json.get("graph_updates", []):
            if update.get("operation") == "upsert_edge":
                graph_updates.append(GraphUpdate(
                    operation="upsert_edge",
                    from_node=update.get("from"),
                    to_node=update.get("to"),
                    edge_type=update.get("type")
                ))

        return RelateResult(
            relations=relations,
            graph_updates=graph_updates,
            new_nodes=result_json.get("new_nodes", []),
            confidence=result_json.get("confidence", 0.5)
        )

    async def relate(
        self,
        entities: list,
        summary: str = "",
        comprehend_result: dict | None = None,
        existing_context: dict | None = None
    ) -> RelateResult:
        """Semantic alias for the unified process entrypoint."""
        entity_dicts = [to_plain_dict(entity) for entity in entities]
        context = comprehend_result or {
            "summary": summary,
            "decisions": [],
            "action_items": [],
            "key_topics": [],
        }
        return await self.process(
            entities=entity_dicts,
            comprehend_result=context,
            existing_context=existing_context,
        )

    def _fallback_relate(
        self,
        entities: list[dict],
        comprehend_result: dict
    ) -> RelateResult:
        """降级关联：简单规则匹配"""
        relations = []

        # 简单关联：从决策到相关实体
        decisions = comprehend_result.get("decisions", [])
        if decisions and entities:
            # 假设第一个实体与决策相关
            relations.append(Relation(
                from_entity=decisions[0].get("content", ""),
                to_entity=entities[0].get("name", ""),
                relation_type="related_to"
            ))

        return RelateResult(
            relations=relations,
            graph_updates=[],
            new_nodes=[],
            confidence=0.3
        )

    def to_cypher(self, result: RelateResult) -> list[str]:
        """
        将关联结果转换为 Cypher 查询

        Returns:
            list[str]: Cypher 查询列表
        """
        cypher_queries = []

        # 创建节点
        for node in result.new_nodes:
            node_id = node.get("node_id", "")
            node_type = node.get("node_type", "Entity")
            props = node.get("properties", {})

            # 转义属性值
            props_str = ", ".join([
                f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}"
                for k, v in props.items()
            ])

            cypher = f"""
MERGE (n:{node_type} {{id: '{node_id}'}})
SET n += {{{props_str}}}
SET n.updated_at = timestamp()
"""
            cypher_queries.append(cypher.strip())

        # 创建关系
        for rel in result.relations:
            from_id = rel.from_entity.replace("'", "\\'")
            to_id = rel.to_entity.replace("'", "\\'")
            rel_type = rel.relation_type.upper()

            cypher = f"""
MATCH (a), (b)
WHERE a.name = '{from_id}' AND b.name = '{to_id}'
MERGE (a)-[r:{rel_type}]->(b)
SET r.updated_at = timestamp()
"""
            cypher_queries.append(cypher.strip())

        return cypher_queries

    def to_dict(self, result: RelateResult) -> dict:
        """转换为可序列化格式"""
        return {
            "relations": [
                {
                    "from": r.from_entity,
                    "to": r.to_entity,
                    "type": r.relation_type,
                    "properties": r.properties
                }
                for r in result.relations
            ],
            "new_nodes": result.new_nodes,
            "confidence": result.confidence
        }
