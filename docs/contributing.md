# Contributing to White-Ops

## Development Setup

```bash
git clone https://github.com/hesperus/white-ops.git
cd white-ops
cp .env.example .env
# Edit .env with your API keys

# Validate environment before starting
make check

# Start in dev mode (hot reload for all services)
make dev
```

## Project Structure

```
white-ops/
  server/       # FastAPI backend (Python 3.12)
  worker/       # Agent worker with 83 tools (Python 3.12)
  web/          # React 18 admin panel (TypeScript)
  mail/         # Internal SMTP server (aiosmtpd)
  monitoring/   # Prometheus, Grafana, Loki configs
  deploy/       # Helm charts for Kubernetes
  docs/         # Documentation
  scripts/      # Setup and deployment scripts
```

## Code Standards

### Python (server + worker)
- Formatter: `ruff format`
- Linter: `ruff check`
- Type checker: `mypy --strict`
- Tests: `pytest`
- All I/O must be async (`async/await` throughout)
- Python 3.12+ features encouraged (type hints, match statements)

### TypeScript (web)
- Strict mode enabled (`"strict": true` in tsconfig)
- No `any` types -- use proper typing
- ESLint for linting
- Functional components with hooks
- Zustand for client state, TanStack Query for server state

### Tailwind CSS
- Always include `dark:` variants for dark mode support
- Use the shared component library under `web/src/components/ui/`
- Follow existing color token patterns

## Testing Requirements

### Backend (server)
```bash
make test-server    # pytest in server container
```

### Worker
```bash
make test-worker    # pytest in worker container
```
Security-sensitive tools must have tests in `worker/tests/test_security_tools.py` covering bypass attempts (path traversal, command injection, SSRF, SQL injection).

### Frontend
```bash
cd web && npx vitest        # Run frontend tests
cd web && npx tsc --noEmit  # TypeScript type check
```

All tests must pass before submitting a PR. Run the full suite locally:
```bash
make lint
make test
```

## CI/CD Pipeline

GitHub Actions runs on push to `main`/`develop` and PRs to `main`:

1. **Lint**: ESLint + TypeScript check (frontend), Ruff lint (backend)
2. **Security**: pip-audit, npm audit, Trivy container scanning
3. **Test**: pytest with PostgreSQL/Redis services (backend), Vitest (frontend)
4. **Build**: Multi-service Docker build and push to GHCR

All checks must pass. There are no `|| true` overrides -- failures block the merge.

## Adding a New Tool

1. Create a file in `worker/agent/tools/<category>/`
2. Extend `BaseTool` with `name`, `description`, `parameters`, and `async execute()`
3. Add security checks for any dangerous operations (file writes, shell commands, network requests)
4. Add unit tests in `worker/tests/`
5. Add security bypass tests in `worker/tests/test_security_tools.py` if applicable
6. The tool is auto-discovered at startup -- no registration needed

See [tools-guide.md](tools-guide.md) for full details and the security hardening patterns.

## Adding a New API Endpoint

1. Create route file in `server/app/api/v1/`
2. Add Pydantic schemas in `server/app/schemas/`
3. Add service logic in `server/app/services/` if needed
4. Register router in `server/app/main.py`
5. Add audit logging for important actions
6. Add tests in `server/tests/`

## Adding a New Admin Panel Page

1. Create the page component in `web/src/pages/`
2. Add the route in `web/src/App.tsx`
3. Add the sidebar entry in `web/src/components/Layout.tsx`
4. Include `dark:` Tailwind variants for dark mode
5. Use `QueryError` component for error states with retry
6. Add ARIA attributes for accessibility

## Pull Request Process

1. Branch from `main` with a descriptive branch name
2. Write code following the standards above
3. Add tests for new functionality
4. Run `make lint` and `make test` locally -- all must pass
5. Submit PR with a clear description of changes
6. CI must pass before merge
7. Changes touching auth, vault, sandbox, or security require additional review

## Commit Messages

Use conventional commits:
```
feat: add new Excel chart types
fix: resolve WebSocket reconnection issue
docs: update deployment guide
test: add auth endpoint tests
refactor: simplify task orchestrator
```
