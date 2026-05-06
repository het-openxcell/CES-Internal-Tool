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
migrate -path ces-backend-go/migrations -database "$POSTGRES_DSN" up
psql "$POSTGRES_DSN" -c "\d users"
migrate -path ces-backend-go/migrations -database "$POSTGRES_DSN" down 1
migrate -path ces-backend-go/migrations -database "$POSTGRES_DSN" up
```

```bash
cd ces-ddr-platform/ces-backend-python
source .venv/bin/activate
export POSTGRES_DSN="postgresql://ces:change-me-local-only@localhost:5432/ces_ddr"
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
cd ces-backend-python
uv sync
uvicorn app.main:app --reload
pytest
```

## Go Backend

```bash
cd ces-backend-go
go run main.go
go test ./...
```
