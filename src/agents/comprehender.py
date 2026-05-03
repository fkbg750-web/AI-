"""
Comprehend Agent - 语义理解器
理解语义、识别决策点、提取行动项
"""
import json
from dataclasses import dataclass, field

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - used when running mocked tests without deps
    Anthropic = object

from src.agents.utils import maybe_await, parse_json_object, to_plain_dict


@dataclass
class Decision:
    """决策"""
    content: str
    confidence: float
    reason: str | None = None
    alternatives: list[str] = field(default_factory=list)


@dataclass
class ActionItem:
    """行动项"""
    task: str
    owner: str | None = None
    deadline: str | None = None
    priority: str = "medium"  # high, medium, low


@dataclass
class ComprehendResult:
    """理解结果"""
    summary: str
    decisions: list[Decision]
    action_items: list[ActionItem]
    sentiment: str  # positive, neutral, negative
    key_topics: list[str]
    raw_output: dict


class ComprehendAgent:
    """
    理解 Agent

    职责：
    1. 理解文本的语义含义
    2. 识别明确的和隐含的决策
    3. 提取行动项和负责人
    4. 判断情感倾向
    5. 提取主题关键词
    """

    SYSTEM_PROMPT = """你是一个专业的语义理解 Agent。

分析给定的文本内容：
1. **摘要**：用 1-2 句话总结主要内容
2. **决策识别**：识别明确的决策（如"决定采用X方案"）和隐含的决策（如"讨论了A vs B，最终倾向B"）
3. **行动项提取**：识别任务、负责人（如果提到）、截止日期（如果提到）
4. **情感分析**：判断整体情感倾向（positive/neutral/negative）
5. **主题提取**：提取 3-5 个核心主题关键词

输出格式（JSON）：
{
    "summary": "简要摘要",
    "decisions": [
        {
            "content": "决策内容",
            "confidence": 0.9,
            "reason": "决策原因（如果有）",
            "alternatives": ["备选方案（如果有）"]
        }
    ],
    "action_items": [
        {
            "task": "任务描述",
            "owner": "负责人（如果提到）",
            "deadline": "截止日期（如果提到）",
            "priority": "high|medium|low"
        }
    ],
    "sentiment": "positive|neutral|negative",
    "key_topics": ["主题1", "主题2", "主题3"],
    "implied_meaning": "隐含含义（如果有）"
}

请直接输出 JSON，不要有其他内容。"""

    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client

    async def process(
        self,
        content: str,
        extract_result: dict | None = None
    ) -> ComprehendResult:
        """
        理解文本内容

        Args:
            content: 待理解的文本
            extract_result: 可选的提取结果（提供额外上下文）

        Returns:
            ComprehendResult: 理解结果
        """
        # 如果有提取结果，融入 Prompt
        context = ""
        if extract_result:
            context = f"\n\n已知实体：{json.dumps(extract_result.get('entities', []), ensure_ascii=False)}\n"
            context += f"已知信息类型：{extract_result.get('info_type', 'unknown')}\n"
            context += f"已知关键点：{extract_result.get('key_points', [])}\n"

        prompt = f"""请分析以下内容：\n\n{content}{context}"""

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
            return self._fallback_comprehend(content)

        # 构建决策列表
        decisions = [
            Decision(
                content=d.get("content", ""),
                confidence=d.get("confidence", 0.5),
                reason=d.get("reason"),
                alternatives=d.get("alternatives", [])
            )
            for d in result_json.get("decisions", [])
        ]

        # 构建行动项列表
        action_items = [
            ActionItem(
                task=a.get("task", ""),
                owner=a.get("owner"),
                deadline=a.get("deadline"),
                priority=a.get("priority", "medium")
            )
            for a in result_json.get("action_items", [])
        ]

        return ComprehendResult(
            summary=result_json.get("summary", ""),
            decisions=decisions,
            action_items=action_items,
            sentiment=result_json.get("sentiment", "neutral"),
            key_topics=result_json.get("key_topics", []),
            raw_output=result_json
        )

    async def comprehend(
        self,
        content: str,
        entities: list | None = None,
        extract_result: dict | None = None
    ) -> ComprehendResult:
        """Semantic alias for the unified process entrypoint."""
        context = extract_result
        if context is None and entities is not None:
            context = {"entities": [to_plain_dict(entity) for entity in entities]}
        return await self.process(content=content, extract_result=context)

    def _fallback_comprehend(self, content: str) -> ComprehendResult:
        """降级理解：简单处理"""
        # 简单截取前 200 字符作为摘要
        summary = content[:200] + "..." if len(content) > 200 else content

        return ComprehendResult(
            summary=summary,
            decisions=[],
            action_items=[],
            sentiment="neutral",
            key_topics=[],
            raw_output={}
        )

    def to_dict(self, result: ComprehendResult) -> dict:
        """转换为可序列化格式"""
        return {
            "summary": result.summary,
            "decisions": [
                {
                    "content": d.content,
                    "confidence": d.confidence,
                    "reason": d.reason,
                    "alternatives": d.alternatives
                }
                for d in result.decisions
            ],
            "action_items": [
                {
                    "task": a.task,
                    "owner": a.owner,
                    "deadline": a.deadline,
                    "priority": a.priority
                }
                for a in result.action_items
            ],
            "sentiment": result.sentiment,
            "key_topics": result.key_topics
        }
