.PHONY: demo-up demo-reset verify demo-down

demo-up:
	@echo "Validating .env file..."
	@test -f .env || (echo "Error: .env file missing" && exit 1)
	@echo "Starting PostgreSQL..."
	docker compose up -d db
	@echo "Waiting for PostgreSQL..."
	@sleep 5
	@echo "Running migrations inside backend container..."
	docker compose run --rm backend alembic upgrade head
	@echo "Running clean four-persona reset inside backend container..."
	docker compose run --rm -e DEMO_USER_PASSWORD=$$(grep DEMO_USER_PASSWORD .env | cut -d '=' -f2) backend python -m app.seed.run_demo_reset
	@echo "Starting backend and frontend..."
	docker compose up -d backend frontend
	@echo "Waiting for backend health check..."
	@while ! curl -s http://localhost:8000/health > /dev/null; do sleep 2; done
	@echo "Waiting for frontend..."
	@while ! curl -s http://localhost:3005 > /dev/null; do sleep 2; done
	@echo "=================================================="
	@echo "DEMO ENVIRONMENT READY"
	@echo "Frontend URL: http://localhost:3005"
	@echo "Backend API:  http://localhost:8000/docs"
	@echo ""
	@echo "Demo Accounts:"
	@echo "  Analyst:    credit@bank.example"
	@echo "  Sanctioner: sa@bank.example"
	@echo "  RM:         rm@bank.example"
	@echo "  Auditor:    auditor@bank.example"
	@echo "  SysAdmin:   system@bank.example"
	@echo "=================================================="

demo-reset:
	@test -f .env || (echo "Error: .env file missing" && exit 1)
	@echo "Running demo reset..."
	docker compose run --rm -e DEMO_USER_PASSWORD=$$(grep DEMO_USER_PASSWORD .env | cut -d '=' -f2) backend python -m app.seed.run_demo_reset

verify:
	@./scripts/all_tests.sh

demo-down:
	@echo "Stopping services..."
	docker compose down
