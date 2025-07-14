# Contributing to Global Billing Service

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or Docker)
- A Stripe test account

### Getting Started

```bash
# 1. Fork & clone
git clone https://github.com/<your-username>/global-billing-service.git
cd global-billing-service

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment
cp .env.example .env
# Edit .env with your local config

# 5. Start PostgreSQL (via Docker)
docker-compose up -d db

# 6. Run migrations
alembic upgrade head

# 7. Run tests to verify setup
pytest -v
```

## Workflow

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines below.

3. **Write or update tests** for your changes.

4. **Run the test suite** to ensure nothing is broken:
   ```bash
   make test
   ```

5. **Lint your code**:
   ```bash
   make lint
   ```

6. **Commit** with a descriptive message:
   ```bash
   git commit -m "feat: add payment retry logic"
   ```

7. **Push** and open a Pull Request.

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Purpose |
|:-------|:--------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation changes |
| `test:` | Adding or updating tests |
| `refactor:` | Code changes that don't fix bugs or add features |
| `chore:` | Maintenance tasks |

## Code Style

- Follow **PEP 8** with a max line length of **120 characters**
- Use **type hints** for function signatures
- Keep functions focused — one function, one responsibility
- Service layer handles business logic; endpoints handle HTTP concerns
- Use the existing exception hierarchy in `app/core/exceptions.py`

## Project Structure

When adding new features:

- **New endpoint?** → Add to `app/api/v1/endpoints/` and register in `router.py`
- **New model?** → Add to `app/models/` and create an Alembic migration
- **New schema?** → Add to `app/schemas/`
- **New service?** → Add to `app/services/`
- **New test?** → Add to `tests/` following existing patterns

## Testing

- All tests use an in-memory SQLite database (no external services needed)
- Stripe API calls are mocked via fixtures in `conftest.py`
- Aim for meaningful tests that cover happy paths and edge cases
- Run with coverage: `make test-cov`

## Questions?

Open an issue with the `question` label, or reach out directly.
