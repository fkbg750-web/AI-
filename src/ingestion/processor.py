"""Utilities for preparing raw text before it enters the agent pipeline."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SourceDocument:
    """A normalized document from Slack, Notion, email, or a local file."""

    content: str
    source_type: str = "manual"
    source_id: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """Split text into overlapping chunks without dropping content."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = text.strip()
    if not normalized:
        return []

    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(normalized[start:end])
        if end == len(normalized):
            break
        start = end - overlap
    return chunks
