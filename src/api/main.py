"""FastAPI entrypoint for TeamMind."""
from fastapi import FastAPI
from pydantic import BaseModel, Field

from src.agents.fallback_client import RuleBasedClient
from src.agents.orchestrator import OrchestratorAgent


class TextRequest(BaseModel):
    """Natural-language request payload."""

    content: str = Field(..., min_length=1)


class QueryRequest(BaseModel):
    """Knowledge query payload."""

    question: str = Field(..., min_length=1)


app = FastAPI(title="TeamMind API", version="0.1.0")


def build_orchestrator() -> OrchestratorAgent:
    """Build a local orchestrator that works without external credentials."""
    return OrchestratorAgent(anthropic_client=RuleBasedClient())


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "teammind"}


@app.post("/plan")
async def plan(request: TextRequest) -> dict:
    """Return the orchestrator's task plan for a piece of text."""
    result = await build_orchestrator().process(request.content)
    return {
        "success": result.success,
        "intent": result.intent.value,
        "tasks": [
            {
                "name": task.name,
                "agent": task.agent,
                "depends_on": task.depends_on,
            }
            for task in result.sub_tasks
        ],
        "final_response": result.final_response,
    }


@app.post("/query")
async def query(request: QueryRequest) -> dict:
    """Run the minimal query flow."""
    result = await build_orchestrator().query(request.question)
    return {
        "success": result.success,
        "intent": result.intent.value,
        "answer": result.answer,
        "sources": result.sources,
    }
