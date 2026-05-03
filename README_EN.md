# TeamMind - AI-Powered Team Knowledge Memory

> A local-first AI knowledge memory system that helps teams preserve project history, understand decision context, and connect fragmented information.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude-purple.svg)](https://anthropic.com)

[Chinese README](README.md)

## Features

### Multi-Agent Workflow

```text
Orchestrator -> Extract -> Comprehend -> Relate -> Store
```

TeamMind splits knowledge work across focused agents instead of relying on one large prompt for every task.

### Hybrid Knowledge Store

- Vector database: semantic search over related knowledge fragments
- Graph database: entity relationships, decision chains, and context paths

### RAG + Graph Retrieval

TeamMind is designed for both natural-language Q&A and relationship-aware reasoning, such as "which tasks were affected by this decision?"

### Local-First Design

Core knowledge data is stored locally in Qdrant and Neo4j, while LLM calls can use cloud APIs.

## Quick Start

### Requirements

- Python 3.11+
- Docker and Docker Compose
- Claude API key, or another compatible LLM setup

### Install

```bash
git clone https://github.com/fkbg750-web/AI-.git
cd AI-

# Start local services
docker-compose up -d

# Install dependencies
pip install -r requirements.txt

# Optional development install
pip install -e ".[dev,demo]"

# Configure environment variables
cp .env.example .env
# Edit .env and add your API keys

# Run the Streamlit demo
cd demo && streamlit run app.py
```

Open `http://localhost:8501` to try the demo.

## Local Validation

```bash
python -m compileall -q src demo tests
ruff check src tests
mypy src
python -m pytest -q -p no:cacheprovider
python -m pytest --cov=src tests -q -p no:cacheprovider
```

Current baseline:

- 13 tests passing
- Ruff passing
- Mypy passing
- Coverage baseline: 53%

## Architecture

```text
Data Sources
Slack | Notion | Email | Local Files
        |
        v
Ingestion Layer
Normalize -> Chunk -> Attach metadata
        |
        v
Agent Layer
Orchestrator -> Extract -> Comprehend -> Relate -> Store
        |
        v
Knowledge Layer
Qdrant vector store + Neo4j graph store
        |
        v
Interfaces
Streamlit demo | FastAPI | CLI
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed system design.

## Core Flows

### Knowledge Ingestion

```text
Document/message -> Parse -> Chunk -> Extract -> Understand -> Relate -> Store
```

### Knowledge Query

```text
User question -> Query rewrite -> Vector retrieval + graph retrieval -> Context fusion -> Answer with sources
```

### Decision Tracking

```text
Meeting notes -> Extract decisions -> Link tasks and owners -> Store graph context -> Query decision history
```

## Project Structure

```text
teammind/
├── src/
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── extractor.py
│   │   ├── comprehender.py
│   │   ├── relater.py
│   │   ├── store.py
│   │   └── fallback_client.py
│   ├── knowledge/
│   │   ├── vector_store.py
│   │   └── graph_store.py
│   ├── ingestion/
│   │   └── processor.py
│   └── api/
│       └── main.py
├── demo/
│   └── app.py
├── docs/
│   ├── project-overview.md
│   ├── design.md
│   └── quality-plan.md
├── tests/
├── docker-compose.yml
├── requirements.txt
├── README.md
└── README_EN.md
```

## API

TeamMind includes a minimal FastAPI entrypoint:

- `GET /health`
- `POST /plan`
- `POST /query`

Run it with:

```bash
uvicorn src.api.main:app --reload
```

## CLI

```bash
python -m src.cli
```

The CLI can use the real Claude client when configured, or a deterministic local fallback client for smoke testing.

## Tech Stack

| Component | Technology |
| --- | --- |
| LLM | Claude API |
| Vector database | Qdrant |
| Graph database | Neo4j |
| API | FastAPI |
| Demo UI | Streamlit |
| Automation | n8n |

## License

MIT License. See [LICENSE](LICENSE).

## Contact

- GitHub Issues: https://github.com/fkbg750-web/AI-/issues

