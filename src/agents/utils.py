"""Shared helpers for agent implementations."""
import inspect
import json
import re
from dataclasses import asdict, is_dataclass
from typing import Any


async def maybe_await(value: Any) -> Any:
    """Return an awaited value when a mock/client call is async."""
    if inspect.isawaitable(value):
        return await value
    return value


def to_plain_dict(value: Any) -> dict:
    """Convert dataclasses and simple objects into dictionaries."""
    if isinstance(value, dict):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {"value": value}


def parse_json_object(text: str) -> dict:
    """Parse a JSON object from direct JSON or a fenced LLM response."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(raw[start:end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object")
    return parsed


def normalize_entity_type(entity_type: str) -> str:
    """Normalize common entity type spellings into graph labels."""
    mapping = {
        "person": "Person",
        "project": "Project",
        "decision": "Decision",
        "task": "Task",
        "document": "Document",
        "meeting": "Meeting",
        "message": "Message",
        "entity": "Entity",
    }
    return mapping.get((entity_type or "").lower(), entity_type or "Entity")
