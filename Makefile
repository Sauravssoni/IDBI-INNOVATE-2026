.PHONY: demo-up demo-reset verify demo-down

demo-up:
	@echo "Validating environment configuration..."
	@docker compose --env-file .env config -q || (echo "Error: Invalid docker compose configuration or missing required variables." && exit 1)
	@echo "Starting PostgreSQL..."
	@docker compose up -d db
	@echo "Waiting for PostgreSQL..."
	@sleep 5
	@echo "Running migrations inside backend container..."
	@docker compose run --rm backend alembic upgrade head
	@echo "Running clean four-persona reset inside backend container..."
	@docker compose run --rm backend python -m app.seed.run_demo_reset
	@echo "Starting backend and frontend..."
	@docker compose up -d backend frontend
	@echo "Waiting for backend health check..."
	@for i in $$(seq 1 30); do \
		if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then \
			break; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "Timeout waiting for backend. Logs:"; \
			docker compose logs backend; \
			exit 1; \
		fi; \
		sleep 2; \
	done
	@echo "Waiting for frontend..."
	@for i in $$(seq 1 30); do \
		if curl -s -f http://localhost:3005 > /dev/null; then \
			break; \
		fi; \
		if [ $$i -eq 30 ]; then \
			echo "Timeout waiting for frontend. Logs:"; \
			docker compose logs frontend; \
			exit 1; \
		fi; \
		sleep 2; \
	done
	@echo "Testing backend login endpoint..."
	@curl -s -f -X POST http://localhost:8000/api/auth/demo/session -H "Content-Type: application/json" -d '{"role": "CREDIT_ANALYST"}' > /dev/null || (echo "Error: Demo session endpoint failed" && exit 1)
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
	@echo "=================================================="

demo-reset:
	@docker compose --env-file .env config -q || (echo "Error: Invalid docker compose configuration" && exit 1)
	@echo "Running demo reset..."
	@docker compose run --rm backend python -m app.seed.run_demo_reset

verify:
	@./scripts/all_tests.sh

demo-down:
	@echo "Stopping services..."
	@docker compose down
