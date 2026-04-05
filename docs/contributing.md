# Contributing to White-Ops

## Development Setup

```bash
git clone https://github.com/your-org/white-ops.git
cd white-ops
cp .env.example .env
# Edit .env with your API keys

# Start in dev mode (hot reload)
make dev
```

## Project Structure

- `server/` - FastAPI backend (Python 3.12)
- `worker/` - Agent worker with tools (Python 3.12)
- `web/` - React admin panel (TypeScript)
- `mail/` - Internal SMTP server
- `docs/` - Documentation
- `scripts/` - Setup and deployment scripts
- `monitoring/` - Prometheus/Grafana configs

## Code Standards

### Python (server + worker)
- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `mypy --strict`
- Tests: `pytest`
- Python 3.12+ features encouraged (type hints, match statements, etc.)

### TypeScript (web)
- Strict mode enabled
- ESLint for linting
- Functional components with hooks
- Zustand for state, TanStack Query for server state

## Adding a New Tool

See [tools-guide.md](tools-guide.md) for detailed instructions.

Quick summary:
1. Create a file in `worker/agent/tools/<category>/`
2. Extend `BaseTool` with `name`, `description`, `parameters`, `execute()`
3. Auto-discovered at startup - no registration needed
4. Add tests in `worker/tests/`

## Adding a New API Endpoint

1. Create route file in `server/app/api/v1/`
2. Add Pydantic schemas in `server/app/schemas/`
3. Register router in `server/app/main.py`
4. Add audit logging for important actions
5. Add tests in `server/tests/`

## Pull Request Process

1. Fork the repo and create a feature branch
2. Write code following the standards above
3. Add tests for new functionality
4. Run `make lint` and `make test` locally
5. Submit PR with clear description
6. CI must pass before merge

## Commit Messages

Use conventional commits:
```
feat: add new Excel chart types
fix: resolve WebSocket reconnection issue
docs: update deployment guide
test: add auth endpoint tests
refactor: simplify task orchestrator
```
