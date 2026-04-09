# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

White-Ops is an enterprise-grade AI workforce platform that deploys AI agents on multiple PCs to handle professional tasks. It uses a master-worker architecture: a FastAPI server orchestrates tasks, multiple worker nodes execute them via LLM-driven agent loops with 70+ tools, and a React admin panel provides the UI. The platform includes enterprise security (MFA, RBAC, secrets vault, audit logging), cost management, workflow automation, and full CI/CD pipeline.

## Common Commands

### Development
```bash
make dev                # Start all services with hot reload
make build              # Build all Docker images
make up                 # Start production services
make logs               # Tail all service logs
make logs-server        # Tail server logs only
make status             # docker compose ps
```

### Testing & Linting
```bash
make test               # Run pytest on server and worker
make test-server        # pytest in server container only
make test-worker        # pytest in worker container only
make lint               # ruff + mypy on Python code
cd web && npx vitest    # Frontend tests
cd web && npx tsc --noEmit  # TypeScript check
```

### Database
```bash
make migrate                      # Run Alembic migrations
make migrate-create MSG="desc"    # Create new migration
make seed                         # Seed demo data
make shell-db                     # psql into database
```

### Utilities
```bash
make shell-server       # bash into server container
make check              # Pre-deployment validation
make backup             # Backup PostgreSQL
make restore FILE=...   # Restore from backup
```

## Architecture

### System Topology

```
React SPA (web/) → FastAPI Server (server/) → PostgreSQL + Redis + MinIO
                     ↕ WebSocket                 ↕ Redis Pub/Sub
                   Celery Workers              Worker Nodes (worker/) with LLM + 70 tools
                   (celery-worker, celery-beat)
```

### Component Layout

- **`server/`** — FastAPI backend (Python 3.12). SQLAlchemy async models, Pydantic schemas, 27 API modules under `app/api/v1/`, services layer for orchestration/storage/queue/audit/vault/workflow/notifications/cost/triggers/circuit-breakers.
- **`worker/`** — Agent executor (Python 3.12). LiteLLM for multi-provider LLM support (Claude/GPT/Gemini/Ollama). Tool plugins in `agent/tools/` organized by category (office, communication, research, data, filesystem, business, technical, finance, hr, integrations, devops, monitoring, cloud, security_tools). Auto-discovered via `ToolRegistry`.
- **`web/`** — React 18 + TypeScript + Vite. Zustand for auth/theme state, TanStack Query for data fetching, Tailwind CSS with dark mode, shared component library under `components/ui/`. 26 page components under `src/pages/`.
- **`mail/`** — Internal SMTP server (aiosmtpd) for inter-agent email, stores in Redis.
- **`monitoring/`** — Prometheus + Grafana dashboards, Loki log aggregation.
- **`deploy/`** — Helm charts for Kubernetes deployment with HPA, NetworkPolicy, Ingress.

### Key Patterns

**Task Flow**: User creates task → server stores as pending → orchestrator scores agents (capacity, tools, worker load) → assigns to best agent → worker polls and executes via LLM function-calling loop (max 50 iterations) → results posted back via PATCH → WebSocket broadcasts to UI.

**Tool System**: Each tool extends `BaseTool` in `worker/agent/tools/base.py`. Tools are auto-discovered from subdirectories by `ToolRegistry`. Tool definitions are sent to the LLM as JSON schema for function calling. Dangerous operations require human approval.

**Auth/RBAC**: JWT tokens with refresh rotation via `server/app/core/security.py`, RBAC with 40+ permissions in `server/app/core/permissions.py`. MFA/TOTP support, account lockout, session management.

**Secrets**: AES-256 (Fernet) encrypted vault in `server/app/services/vault.py`. Secrets encrypted at rest, access audit logged.

**Circuit Breakers**: Redis-backed circuit breakers for external services (LLM APIs, MinIO, Redis). States: closed → open → half-open with configurable thresholds.

**Cost Tracking**: Per-agent, per-task, per-provider cost tracking with budget alerts in `server/app/services/cost_tracker.py`.

**All I/O is async**: FastAPI with asyncpg, aiosmtpd, async Redis, aiofiles throughout.

### Data Model (server/app/models/)

Core entities: User (roles, MFA, lockout), Agent (LLM config, enabled tools, stats, cost tracking), Task (lifecycle states with indexes and constraints, progress, cost), Worker (host metrics, capabilities, GPU info), Message (inter-agent), File (MinIO refs), Workflow (multi-step DAG), Settings, AuditLog.

Enterprise entities: Secret (encrypted vault), SSHConnection, ApprovalRule/ApprovalRequest, AgentMemory/AgentSkill, Trigger/TriggerExecution, WebhookEndpoint, NotificationChannel/NotificationRule/Notification, TokenUsage/Budget/CostRate, DeadLetterTask/TaskCheckpoint/CircuitBreakerState, UserMFA/APIKey/UserSession/LoginAttempt.

All models inherit from a UUID-PK base with created_at/updated_at/deleted_at (soft delete).

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Redis, Celery, MinIO, Pydantic v2, structlog, pyotp, cryptography, croniter
- **Worker**: LiteLLM, Playwright, openpyxl, python-docx, python-pptx, pandas, BeautifulSoup4, boto3, asyncpg, Pillow, matplotlib, seaborn
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS (dark mode), Zustand, TanStack Query, Recharts, React Router v6, i18next, cmdk
- **Infra**: Docker Compose (10 services), PostgreSQL 16, Redis 7, nginx, Prometheus/Grafana, Loki, Jaeger, Helm/Kubernetes
- **CI/CD**: GitHub Actions (lint, test, security scan, Docker build/push to GHCR)

## Security Features

- JWT with refresh token rotation (access: 30min, refresh: 7d)
- MFA/TOTP support with backup codes
- Account lockout after N failed attempts
- Password complexity validation (12+ chars, mixed case, digits, symbols)
- Redis-backed distributed rate limiting (per-IP, per-user, per-endpoint)
- AES-256 encrypted secrets vault with audit logging
- RBAC with 40+ granular permissions
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Input validation and request body size limits
- Circuit breakers for external service resilience
- Helm NetworkPolicies for Kubernetes isolation
- Non-root Docker containers with multi-stage builds
- Trivy/pip-audit/npm-audit security scanning in CI

## CI

GitHub Actions (`.github/workflows/ci.yml`): ESLint + TypeScript check (frontend), Ruff lint (backend), pip-audit + npm audit + Trivy (security), pytest with PostgreSQL/Redis (backend tests), Vitest (frontend tests), multi-service Docker build & push to GHCR. Triggers on push to main/develop and PRs to main.
