# CES DDR Platform

Internal platform foundation for Canadian Energy Services DDR extraction, analysis, correction, and reporting workflows.

## Local Services

```bash
cd ces-ddr-platform
cp .env.example .env
docker compose up -d
docker compose ps
```

## Migration Tooling

```bash
cd ces-ddr-platform
export POSTGRES_DSN="postgresql://ces:change-me-local-only@localhost:5432/ces_ddr"
docker compose up -d postgres
cd ces-backend
source .venv/bin/activate
alembic upgrade head
psql "$POSTGRES_DSN" -c "\d users"
alembic downgrade base
alembic upgrade head
pytest
```

## Frontend

```bash
cd ces-frontend
npm install
npm run dev
```

## Python Backend

```bash
cd ces-backend
uv sync
uvicorn app.main:app --reload
pytest
```
