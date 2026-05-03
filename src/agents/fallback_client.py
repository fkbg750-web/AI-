"""Small deterministic client used when no LLM provider is configured."""
import json
from dataclasses import dataclass


@dataclass
class _ContentBlock:
    text: str


@dataclass
class _MessageResponse:
    content: list[_ContentBlock]


class RuleBasedMessages:
    """Anthropic-like messages API for local development and tests."""

    def create(self, system: str, messages: list[dict], **_: object) -> _MessageResponse:
        text = messages[-1].get("content", "") if messages else ""
        if "信息提取 Agent" in system:
            payload = {
                "entities": [],
                "info_type": "discussion",
                "key_points": [line.strip() for line in text.splitlines() if line.strip()][:5],
                "confidence": 0.3,
            }
        elif "语义理解 Agent" in system:
            payload = {
                "summary": text.replace("\n", " ")[:160],
                "decisions": [],
                "action_items": [],
                "sentiment": "neutral",
                "key_topics": [],
            }
        elif "知识图谱关联 Agent" in system:
            payload = {"relations": [], "new_nodes": [], "confidence": 0.3}
        else:
            query_words = ["是什么", "怎么", "为什么", "谁", "?", "？"]
            store_words = ["添加", "记录", "告诉", "分享", "决定", "负责", "会议"]
            if any(word in text for word in query_words):
                intent = "query"
            elif any(word in text for word in store_words):
                intent = "store"
            else:
                intent = "other"
            payload = {"intent": intent, "sub_tasks": []}

        return _MessageResponse(content=[_ContentBlock(text=json.dumps(payload, ensure_ascii=False))])


class RuleBasedClient:
    """Minimal client exposing ``messages.create`` like Anthropic."""

    def __init__(self):
        self.messages = RuleBasedMessages()
