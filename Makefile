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



seed:
	@echo "Seeding deterministic data..."
	cd backend && source .venv/bin/activate && python -m app.seed.seed_all

build:
	@echo "Building frontend for production..."
	cd frontend && npm run build
	@echo "Building backend container..."
	docker-compose build backend

demo-up:
	@if [ ! -f .env ] || ! grep -q "^DEMO_USER_PASSWORD=" .env; then echo "ERROR: DEMO_USER_PASSWORD must be set in .env"; exit 1; fi
	@echo "Starting PostgreSQL..."
	docker-compose up -d db || exit 1
	@echo "Waiting for PostgreSQL..."
	@sleep 5
	@echo "Running migrations inside backend container..."
	docker-compose run --rm backend alembic upgrade head || exit 1
	@echo "Running demo reset inside backend container..."
	export $$(grep -v '^#' .env | xargs) && docker-compose run --rm -e DEMO_USER_PASSWORD backend python -m app.seed.run_demo_reset || exit 1
	@echo "Starting backend and frontend..."
	docker-compose up -d backend || exit 1
	@echo "Waiting for backend health check..."
	@for i in {1..15}; do \
		curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health | grep -q 200 && break || sleep 2; \
		if [ $$i -eq 15 ]; then echo "Backend failed to start"; exit 1; fi \
	done
	docker-compose up -d frontend || exit 1
	@echo "Waiting for frontend to start..."
	@for i in {1..15}; do \
		curl -s -o /dev/null -w "%{http_code}" http://localhost:3005 | grep -q 200 && break || sleep 2; \
		if [ $$i -eq 15 ]; then echo "Frontend failed to start"; exit 1; fi \
	done
	@echo "=========================================="
	@echo "🚀 VYAPAR PULSE AI DEMO IS RUNNING!"
	@echo "=========================================="
	@echo "Frontend URL: http://localhost:3005"
	@echo "Backend API:  http://localhost:8000/docs"
	@echo ""
	@echo "Demo Credentials (Password: $$DEMO_USER_PASSWORD):"
	@echo "  RM:      rm@bank.example"
	@echo "  Analyst: credit@bank.example"
	@echo "  SA:      sa@bank.example"
	@echo "  Auditor: auditor@bank.example"
	@echo "  Admin:   admin@bank.example"
	@echo "=========================================="

demo-reset:
	@if [ ! -f .env ] || ! grep -q "^DEMO_USER_PASSWORD=" .env; then echo "ERROR: DEMO_USER_PASSWORD must be set in .env"; exit 1; fi
	@echo "Resetting demo environment..."
	export $$(grep -v '^#' .env | xargs) && docker-compose exec -e DEMO_USER_PASSWORD backend python -m app.seed.run_demo_reset || exit 1

verify:
	@if [ ! -f .env ] || ! grep -q "^DEMO_USER_PASSWORD=" .env; then echo "ERROR: DEMO_USER_PASSWORD must be set in .env"; exit 1; fi
	@echo "Running canonical tests (Ensure Node 20 and Python 3.12 are available)..."
	./scripts/all_tests.sh

demo-down:
	@echo "Stopping demo environment and destroying volumes..."
	docker-compose down -v

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

