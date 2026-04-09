<p align="center">
  <img src="assets/social-preview.png" alt="White-Ops" width="700" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License" />
  <img src="https://img.shields.io/badge/python-3.12-green" alt="Python" />
  <img src="https://img.shields.io/badge/react-18-blue" alt="React" />
  <img src="https://img.shields.io/badge/tools-70+-orange" alt="Tools" />
  <img src="https://img.shields.io/badge/pages-36-purple" alt="Pages" />
  <img src="https://img.shields.io/badge/docker-compose-blue" alt="Docker" />
</p>

---

Enterprise AI workforce platform. Deploy AI agents on multiple PCs that handle professional tasks: email, documents, web research, data analysis, code review, DevOps, cloud ops, and 60+ more. Manage everything from a single admin panel with chat interface, live execution terminal, marketplace, and full RBAC.

## Key Features

| Feature | Description |
|---------|-------------|
| **70+ Tools** | Excel, Word, PDF, browser, email, Slack, GitHub, Jira, Docker, Terraform, AWS, and more |
| **Agent Chat** | ChatGPT-style conversational interface to interact with agents directly |
| **Live Terminal** | Watch agent execution in real-time — tool calls, reasoning, cost tracking |
| **Code Reviews** | Visual diff viewer with approve/reject workflow for agent-generated code |
| **Marketplace** | Browse and install pre-built agent templates (16 templates across 8 categories) |
| **Autonomy Controls** | 4-level safety tiers: Autonomous, Cautious, Supervised, Read-Only |
| **Multi-LLM** | Claude, GPT, Gemini, Ollama (local) via unified interface |
| **Multi-PC Workers** | Distribute agents across multiple machines, managed from one panel |
| **36-Page Admin Panel** | Dashboard, agents, tasks, workflows, chat, terminal, settings, security, and more |
| **Setup Wizard** | 7-step onboarding with system check, worker deployment guide, and LLM setup |
| **Workflow Builder** | Visual DAG-based automation with conditions and parallel execution |
| **Cost Management** | Per-agent, per-provider cost tracking with budget alerts and forecasting |
| **Secrets Vault** | AES-256 encrypted secret storage with rotation and audit logging |
| **Circuit Breakers** | Distributed fault tolerance for external services (Redis-backed) |
| **Approval Workflows** | Configurable approval chains for sensitive operations |
| **Notifications** | Multi-channel delivery: Slack, email, Telegram, webhook |
| **10-Tab Settings** | General, LLM, Email, Storage, Security, Notifications, Integrations, Backups, Feature Flags, Danger Zone |
| **Security** | JWT + refresh tokens, MFA/TOTP, account lockout, RBAC (40+ permissions), rate limiting |
| **CI/CD** | GitHub Actions: lint, test, security scan, Docker build/push to GHCR |
| **Kubernetes** | Helm charts with HPA, NetworkPolicy, Ingress (TLS), resource limits |
| **Dark Mode** | Full dark/light/system theme support across all pages |

## Architecture

```
React SPA (36 pages) → FastAPI Server (29 API modules) → PostgreSQL + Redis + MinIO
                          ↕ WebSocket                        ↕ Redis Pub/Sub
                        Celery Workers                     Worker Nodes (70+ tools)
                        (celery-worker, celery-beat)
```

**10 Docker services**: PostgreSQL, Redis, MinIO, FastAPI server, Agent worker, Celery worker, Celery beat, Nginx frontend, Mail server, Monitoring (Prometheus + Grafana)

## Quick Start

### Prerequisites

- Docker 24+ and Docker Compose v2
- 4 CPU cores, 8 GB RAM minimum
- An LLM API key (Anthropic, OpenAI, Google, or local Ollama)

### Setup

```bash
# Clone
git clone https://github.com/Hesper-Labs/white-ops.git
cd white-ops

# Configure
cp .env.example .env
# Edit .env — set SECRET_KEY, JWT_SECRET_KEY, POSTGRES_PASSWORD, and your LLM API key

# Start all services
docker compose up -d

# Open admin panel
open http://localhost:3000
```

The Setup Wizard will guide you through initial configuration on first visit.

### Development

```bash
make dev          # Start with hot reload
make test         # Run all tests
make lint         # Lint Python + TypeScript
make build        # Build Docker images
make logs         # Tail service logs
```

## Tool Categories (70+)

| Category | Tools |
|----------|-------|
| **Office** | Excel, Word, PowerPoint, PDF, Forms, Notes |
| **Communication** | Email, Slack, Teams, Discord, SMS, Calendar, Telegram |
| **Research** | Browser, Search, Web Scraper, RSS, Summarizer, Translator |
| **Data** | Analysis, Database, Cleaning, Visualization, Converter |
| **Technical** | Shell, Git, Docker, Claude Code Bridge, Code Execution, API Caller, SSH |
| **DevOps** | Terraform, Kubernetes, CI/CD, Ansible |
| **Cloud** | AWS (EC2/S3/Lambda), Azure, GCP |
| **Business** | CRM, Invoice, Expense Reports, Project Tracker, Time Tracker |
| **Finance** | Bookkeeping, Currency, Tax Calculator |
| **HR** | Payroll, Employee Directory, Leave Manager |
| **Monitoring** | Health Checker, Prometheus, Log Analyzer |
| **Security** | Vulnerability Scanner, Secret Scanner, Port Scanner |
| **Integrations** | GitHub, Jira, Notion, PagerDuty, Sentry, Linear |

## Security

- JWT with refresh token rotation (access: 30min, refresh: 7d)
- MFA/TOTP with backup codes
- Account lockout after configurable failed attempts
- Password complexity (12+ chars, mixed case, digits, symbols) + history
- Redis-backed distributed rate limiting (per-IP, per-user, per-endpoint)
- AES-256 encrypted secrets vault
- RBAC with 40+ granular permissions (admin, operator, viewer)
- Security headers (HSTS, CSP, X-Frame-Options)
- Request body size limits and input validation
- Non-root Docker containers with multi-stage builds
- Startup config validation — refuses to boot with default secrets in production

## Deployment

### Docker Compose (Production)

```bash
docker compose up -d
```

### Kubernetes (Helm)

```bash
cd deploy/helm
helm install whiteops ./white-ops -f values.yaml
```

Features: HPA (auto-scaling), NetworkPolicy, Ingress with TLS, resource limits, PVC for data services.

### Adding Remote Workers

```bash
# On each remote machine:
docker compose up worker -d
# Or see Setup Wizard for detailed multi-PC deployment instructions
```

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery, Redis, MinIO |
| **Worker** | LiteLLM, Playwright, pandas, boto3, openpyxl, python-docx |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Zustand, TanStack Query, Recharts |
| **Database** | PostgreSQL 16, Redis 7 |
| **Infra** | Docker Compose, Helm/Kubernetes, Prometheus, Grafana, Nginx |
| **CI/CD** | GitHub Actions (lint, test, security scan, Docker build) |

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
