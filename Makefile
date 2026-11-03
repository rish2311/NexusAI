.PHONY: up down migrate api web test install lint

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd backend && .venv/bin/alembic upgrade head

api:
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest -q

install:
	cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

lint:
	cd backend && .venv/bin/ruff check app tests
	cd frontend && npm run lint
