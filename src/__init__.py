"""
TeamMind - 智能团队知识记忆系统

让 AI 成为团队的"老员工"，解决信息碎片化、知识流失等问题。
"""
__version__ = "0.1.0"

from src.agents import (
    OrchestratorAgent,
    ExtractAgent,
    ComprehendAgent,
    RelateAgent,
    StoreAgent,
)
from src.knowledge import VectorStore, GraphStore

__all__ = [
    "__version__",
    "OrchestratorAgent",
    "ExtractAgent",
    "ComprehendAgent",
    "RelateAgent",
    "StoreAgent",
    "VectorStore",
    "GraphStore",
]
