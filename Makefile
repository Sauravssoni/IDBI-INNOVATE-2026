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
	@echo "Waiting for database to be ready and running migrations..."
	@cd backend && for i in 1 2 3 4 5 6; do \
		source .venv/bin/activate && alembic upgrade head && break || (echo "Retrying..." && sleep 5); \
	done
	docker-compose up backend frontend

dev-detached:
	@echo "Starting development environment in background..."
	docker-compose up -d db
	@echo "Waiting for database to be ready and running migrations..."
	@cd backend && for i in 1 2 3 4 5 6; do \
		source .venv/bin/activate && alembic upgrade head && break || (echo "Retrying..." && sleep 5); \
	done
	docker-compose up -d backend frontend

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

demo-up:
	@echo "Starting PostgreSQL..."
	docker-compose up -d db
	@echo "Waiting for PostgreSQL..."
	@sleep 5
	@echo "Running migrations inside backend container..."
	docker-compose run --rm backend alembic upgrade head
	@echo "Running demo reset inside backend container..."
	docker-compose run --rm -e DEMO_USER_PASSWORD="$${DEMO_USER_PASSWORD:-demopassword}" backend python -m app.seed.run_demo_reset
	@echo "Starting backend and frontend..."
	docker-compose up -d backend
	@echo "Waiting for backend health check..."
	@for i in {1..15}; do \
		curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q 200 && break || sleep 2; \
		if [ $$i -eq 15 ]; then echo "Backend failed to start"; exit 1; fi \
	done
	docker-compose up -d frontend
	@echo "=========================================="
	@echo "🚀 VYAPAR PULSE AI DEMO IS RUNNING!"
	@echo "=========================================="
	@echo "Frontend URL: http://localhost:3005"
	@echo "Backend API:  http://localhost:8000/docs"
	@echo ""
	@echo "Demo Credentials (Password: demopassword):"
	@echo "  RM:      rm@bank.example"
	@echo "  Analyst: credit@bank.example"
	@echo "  SA:      sa@bank.example"
	@echo "  Auditor: auditor@bank.example"
	@echo "  Admin:   admin@bank.example"
	@echo "=========================================="

demo-reset:
	@echo "Resetting demo environment..."
	docker-compose exec -e DEMO_USER_PASSWORD="$${DEMO_USER_PASSWORD:-demopassword}" backend python -m app.seed.run_demo_reset

verify:
	@echo "Running decision assurance verification..."
	docker-compose exec -e DEMO_USER_PASSWORD="$${DEMO_USER_PASSWORD:-demopassword}" backend python scripts/run_decision_assurance.py

demo-down:
	@echo "Stopping demo environment and destroying volumes..."
	docker-compose down -v

clean-room:
	@echo "Starting isolated clean-room verification..."
	COMPOSE_PROJECT_NAME=vyapar_pulse_cleanroom docker-compose up -d db
	@echo "Waiting for clean-room database..."
	@cd backend && for i in 1 2 3 4 5 6; do \
		source .venv/bin/activate && alembic upgrade head && break || (echo "Retrying..." && sleep 5); \
	done
	COMPOSE_PROJECT_NAME=vyapar_pulse_cleanroom docker-compose up -d backend frontend
	@echo "Clean-room verification started. Run 'COMPOSE_PROJECT_NAME=vyapar_pulse_cleanroom docker-compose down -v' when done."

down:
	@echo "Stopping services and preserving volumes..."
	docker-compose down

purge:
	@if [ "$(CONFIRM)" != "YES" ]; then \
		echo "ERROR: You must pass CONFIRM=YES to execute purge."; \
		exit 1; \
	fi
	@echo "Purging all project resources..."
	docker-compose down -v --rmi all --remove-orphans

docs-check:
	@echo "Running documentation quality gates..."
	./scripts/docs_check.sh

