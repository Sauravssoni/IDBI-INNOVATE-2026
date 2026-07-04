.PHONY: setup dev seed test lint typecheck security build demo-reset

setup:
	@echo "Setting up Vyapar Pulse AI..."
	cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
	@echo "Backend dependencies installed."
	cd frontend && npm install
	@echo "Frontend dependencies installed."
	@echo "Setup complete. Copy .env.example to .env and run 'make dev'."

dev:
	@echo "Starting development environment..."
	docker-compose up -d db
	@echo "Waiting for database to be ready..."
	sleep 5
	cd backend && source .venv/bin/activate && alembic upgrade head
	docker-compose up backend frontend

seed:
	@echo "Seeding deterministic data..."
	cd backend && source .venv/bin/activate && python -m app.seed.seed_all

test:
	@echo "Running backend tests..."
	cd backend && source .venv/bin/activate && pytest -v

lint:
	@echo "Linting backend..."
	cd backend && source .venv/bin/activate && ruff check .
	@echo "Linting frontend..."
	cd frontend && npm run lint

typecheck:
	@echo "Typechecking backend..."
	cd backend && source .venv/bin/activate && mypy app/
	@echo "Typechecking frontend..."
	cd frontend && npm run type-check

security:
	@echo "Running security scans..."
	cd backend && source .venv/bin/activate && bandit -r app/

build:
	@echo "Building frontend for production..."
	cd frontend && npm run build
	@echo "Building backend container..."
	docker-compose build backend

demo-reset:
	@echo "Resetting demo environment..."
	docker-compose down -v
	make dev
	make seed
