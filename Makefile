.PHONY: help install dev test lint run docker-up docker-down migrate seed clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

dev: ## Start development server
	uvicorn app.main:app --reload --port 8000

test: ## Run tests
	pytest -v --tb=short

test-cov: ## Run tests with coverage
	pytest --cov=app --cov-report=html --cov-report=term -v

lint: ## Run linting
	flake8 app/ --max-line-length=120 --exclude=__pycache__

run: ## Start production server
	uvicorn app.main:app --host 0.0.0.0 --port 8000

docker-up: ## Start Docker services
	docker-compose up --build -d

docker-down: ## Stop Docker services
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f api

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create msg="description")
	alembic revision --autogenerate -m "$(msg)"

seed: ## Seed database with initial data
	python -m app.scripts.seed_data

clean: ## Clean up cached files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type f -name "*.pyc" -delete 2>/dev/null; \
	rm -rf .pytest_cache htmlcov .coverage test.db
