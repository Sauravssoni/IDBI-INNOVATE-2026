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

demo-reset:
	@echo "WARNING: This will DESTROY all local database volumes for this project."
	@echo "Waiting 5 seconds before proceeding... (Ctrl+C to cancel)"
	@sleep 5
	@echo "Resetting demo environment..."
	docker-compose down -v
	make dev-detached
	make seed

demo:
	@echo "Starting non-destructive demo environment..."
	make dev-detached
	@echo "Demo environment is ready."

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

