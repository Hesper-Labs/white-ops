# Contributing to White-Ops

Thanks for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
git clone https://github.com/Hesper-Labs/white-ops.git
cd white-ops
cp .env.example .env
make dev
```

## Code Standards

### Python (server + worker)
- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `mypy --strict`
- Tests: `pytest`

### TypeScript (web)
- Strict mode, ESLint, functional components

## Commands

```bash
make dev          # Start with hot reload
make test         # Run all tests
make lint         # Run linters
make build        # Build Docker images
```

## Adding a New Tool

1. Create file in `worker/agent/tools/<category>/`
2. Extend `BaseTool` with `name`, `description`, `parameters`, `execute()`
3. Auto-discovered at startup

See [docs/tools-guide.md](docs/tools-guide.md) for details.

## Pull Requests

1. Fork and create a feature branch
2. Follow code standards
3. Run `make lint` and `make test`
4. Submit PR with clear description

Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`
