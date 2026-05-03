"""Shared helpers for agent implementations."""
import inspect
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
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {"value": value}
