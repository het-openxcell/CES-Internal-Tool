# CES Backend

FastAPI backend for the Canadian Energy Service internal tool. Handles PDF log extraction, data analysis, embeddings, and report generation.

## Stack

- Python 3.12+
- FastAPI + Uvicorn
- SQLAlchemy + Alembic + asyncpg
- Qdrant (vector store)
- Google GenAI
- pdfplumber / pypdf (PDF extraction)
- bcrypt / python-jose (auth)

## API Routes

| Route | Description |
|-------|-------------|
| `/api/v1/auth` | Authentication (login, register, token refresh) |
| `/api/v1/users` | User management |
| `/api/v1/ddr` | DDR (drill data report) operations |
| `/api/v1/pipeline` | Extraction pipeline |
| `/api/v1/keywords` | Keyword management |
| `/api/v1/health` | Health checks |

## Setup

Requires `uv`. Copy `.env.example` to `.env` and fill values.

```bash
cp .env.example .env
uv sync
source .venv/bin/activate
uvicorn main:backend_app --reload
```

## Tests

```bash
pytest
```

## Lint

```bash
ruff check .
ruff format .
```

## Migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```
