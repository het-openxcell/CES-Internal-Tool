# CES DDR Platform

Internal platform foundation for Canadian Energy Services DDR extraction, analysis, correction, and reporting workflows.

## Local Services

```bash
cp .env.example .env
docker compose up -d
docker compose ps
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
