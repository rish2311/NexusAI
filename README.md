# NexusAI — Sprint 1 (`v1.0`)

Authenticated AI chatbot with persistent conversations, SSE streaming, usage/quota tracking, and a Gemini free-tier LLM gateway.

**Budget: ₹0** — Gemini free tier only · local Docker · no paid APIs.

## What you get

1. Register / login (JWT + refresh rotation)
2. Create conversation threads
3. Stream token-by-token replies (Gemini free tier)
4. Stop generation
5. Reload and see message history
6. See token usage + **free** tier badge (+ optional commercial cost estimate)
7. Daily request/token quotas
8. Strict per-user thread isolation

No agents, tools, RAG, or MCP in this sprint.

## 10 zero-cost rules

1. Use **Gemini free tier** only — no OpenAI / paid LLM keys.
2. Run **Postgres + Redis locally** via Docker Compose — no cloud DB.
3. Do **not** create paid cloud accounts or anything requiring a credit card.
4. Keep daily **request/token quotas** low to protect free API limits.
5. Run automated tests against the **mock** provider — never burn quota in CI.
6. Live Gemini smoke tests are **manual and rare**.
7. Do not paste secrets, credentials, or confidential docs into free-tier chats.
8. Commercial cost figures are **estimates for learning**, not billing.
9. No cloud deployment this sprint — localhost only.
10. If free quota is exhausted, switch `LLM_PROVIDER=mock` and keep building.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 15 (App Router) + Tailwind |
| Backend | FastAPI + SQLAlchemy async + Alembic |
| DB | PostgreSQL 16 + pgvector image |
| Cache / cancel | Redis 7 |
| LLM | Gemini free tier (`google-generativeai`) |

## Prerequisites

- Node.js 20+
- Python 3.11+
- Docker Desktop / Engine (for Postgres + Redis)
- Free Gemini API key: https://ai.google.dev/

## Quick start

```bash
cd NexusAI
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=...

# Infra
make up

# Backend
make install
make migrate
make api

# Frontend (new terminal)
cp frontend/.env.example frontend/.env.local
make web
```

- API: http://localhost:8000/docs  
- App: http://localhost:3000  
- Health: http://localhost:8000/healthz

### Offline / tests without Gemini

```bash
# in .env
LLM_PROVIDER=mock
```

```bash
make test
```

## Makefile targets

| Target | Action |
|--------|--------|
| `make up` | Start Postgres + Redis |
| `make down` | Stop containers |
| `make install` | Python venv + frontend npm install |
| `make migrate` | Alembic upgrade head |
| `make api` | Run FastAPI on :8000 |
| `make web` | Run Next.js on :3000 |
| `make test` | Backend pytest (mock LLM) |

## API surface (Sprint 1)

- `POST /v1/auth/register|login|refresh|logout` · `GET /v1/auth/me`
- `GET|POST /v1/threads` · `GET|PATCH|DELETE /v1/threads/{id}` · messages list
- `POST /v1/chat/stream` (SSE over POST) · `POST /v1/chat/stop`
- `GET /healthz` · `GET /readyz`

### SSE events

```text
event: token
data: {"text":"..."}

event: done
data: {"message_id":"...","usage":{"input_tokens":N,"output_tokens":N,"tier":"free","provider":"gemini","model":"...","estimated_commercial_cost_usd":0.0}}

event: error
data: {"code":"quota_exceeded|provider_unavailable|...","message":"..."}
```

Frontend uses `fetch()` + streaming reader (not `EventSource`).

## Project layout

```text
NexusAI/
├── frontend/          # Next.js chat UI
├── backend/           # FastAPI + LLM gateway
│   ├── app/
│   ├── alembic/
│   ├── tests/
│   └── evals/         # eval placeholder
├── docker-compose.yml
├── .env.example
└── Makefile
```

## Release

Tag: **`v1.0`**

## Privacy note

Provider free tiers may use prompts to improve products. Never send confidential material through Gemini free tier.
