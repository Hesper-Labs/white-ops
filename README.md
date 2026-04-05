<p align="center">
  <img src="assets/logo.png" alt="White-Ops" width="80" />
</p>

<h1 align="center">White-Ops</h1>

<p align="center">
  <strong>Open-source AI workforce platform that replaces white-collar tasks with autonomous agents.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License" />
  <img src="https://img.shields.io/badge/python-3.12-green" alt="Python" />
  <img src="https://img.shields.io/badge/react-18-blue" alt="React" />
  <img src="https://img.shields.io/badge/tools-55-orange" alt="Tools" />
  <img src="https://img.shields.io/badge/pages-21-purple" alt="Pages" />
  <img src="https://img.shields.io/badge/docker-compose-blue" alt="Docker" />
</p>

---

Deploy AI agents on multiple PCs that handle everything a white-collar worker does: email, Excel, Word, PowerPoint, web research, data analysis, invoicing, CRM, payroll, and 45+ more tasks. Manage them all from a single admin panel.

## Key Features

| Feature | Description |
|---------|-------------|
| **55 Tools** | Excel, Word, PowerPoint, PDF, browser, email, CRM, invoicing, payroll, OCR, and more |
| **Multi-Agent** | Specialized agents: researcher, analyst, writer, developer, accountant, HR, etc. |
| **Multi-LLM** | Claude, GPT, Gemini, Ollama (local/offline) via single interface |
| **Multi-PC** | Install on multiple machines, managed from one admin panel |
| **Agent Communication** | Agents email each other, delegate tasks, share knowledge |
| **21-Page Admin Panel** | Complete control over agents, tasks, workflows, workers, users, analytics |
| **Workflow Builder** | Visual multi-step automation editor with conditions and parallel execution |
| **Agent Presets** | 12 ready-to-deploy profiles: Financial Analyst, Developer, HR Manager, etc. |
| **Scheduled Tasks** | Cron-based recurring automation (e.g., "every Monday at 9am") |
| **Knowledge Base** | Shared agent memory with search, categories, and tags |
| **Agent Collaboration** | Multi-agent sessions for complex projects |
| **Real-time Analytics** | Success rates, completion times, agent performance, worker utilization |
| **Integrations** | Slack, Jira, GitHub, Notion, Telegram, Google Workspace, webhooks |
| **RBAC** | Admin, Operator, Viewer roles with granular permissions |
| **Audit Log** | Complete trail of every action taken in the system |
| **Security** | Rate limiting, JWT auth, sandboxed code execution, security headers |
| **CI/CD** | GitHub Actions with lint, test, security scan, Docker build |
| **Monitoring** | Prometheus + Grafana dashboards |

## Screenshots

### Dashboard
Real-time overview with KPI cards, Recharts bar/pie charts, task distribution, and system health monitoring.

### Agent Management
Table view with status indicators, LLM info, completion stats. Click for detailed 5-tab view (Overview, Configuration, Tools, Logs, Performance).

### Task Board
Filter by status, assign to agents, set priorities. Each task has detailed view with results, tool call logs, and comments.

### Workflow Builder
Visual step editor with Task, If/Else, Parallel, Wait, and Notify step types. Assign agents per step.

### Agent Presets
12 pre-configured agent profiles (Financial Analyst, Research Specialist, Content Writer, etc.) with one-click deploy.

### Worker Fleet
Monitor CPU, RAM, and disk usage across all connected PCs. Approve/reject new workers.

## Quick Start

### Prerequisites
- Docker 24+ and Docker Compose v2
- 4GB+ RAM (8GB recommended)

### Installation

```bash
git clone https://github.com/hesperus/white-ops.git
cd white-ops
./scripts/setup.sh
```

This automatically:
1. Generates cryptographically secure secrets
2. Builds all Docker images (server, worker, web, mail)
3. Starts PostgreSQL, Redis, MinIO, and all services
4. Creates the admin account

Open **http://localhost:3000** and sign in.

### Add a Worker Node

On each additional PC:

```bash
./scripts/add-worker.sh <MASTER_IP>
```

Then approve the worker in **Settings > Workers**.

## Architecture

```
                    +------------------+
                    |   Admin Panel    |
                    |   (React/TS)     |
                    +--------+---------+
                             |
                    +--------v---------+
                    |   API Server     |
                    |   (FastAPI)      |
                    +--------+---------+
                             |
           +-----------------+------------------+
           |                 |                  |
    +------v------+   +-----v------+   +-------v-----+
    | PostgreSQL  |   |   Redis    |   |    MinIO     |
    | (data)      |   | (queue)    |   | (files)      |
    +-------------+   +-----+------+   +-------------+
                             |
              +--------------+--------------+
              |              |              |
       +------v------+ +----v-------+ +----v-------+
       |  Worker-01  | | Worker-02  | | Worker-N   |
       |  Agent A,B  | | Agent C,D  | | Agent E,F  |
       +-------------+ +------------+ +------------+
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | Python 3.12, FastAPI, SQLAlchemy, Celery |
| Frontend | React 18, TypeScript, Tailwind CSS, Vite, Recharts |
| Database | PostgreSQL 16 |
| Queue & Cache | Redis 7 |
| File Storage | MinIO (S3-compatible) |
| LLM | LiteLLM (Claude, GPT, Gemini, Ollama) |
| Internal Mail | aiosmtpd (SMTP) |
| Deployment | Docker Compose |
| CI/CD | GitHub Actions |
| Monitoring | Prometheus, Grafana |

## Project Structure

```
white-ops/
  server/          # FastAPI backend
    app/
      api/v1/      # 16 API modules (auth, agents, tasks, workflows, etc.)
      models/      # 12 SQLAlchemy models
      core/        # Auth, security, middleware, logging
      services/    # Business logic (orchestrator, storage, audit, task queue)
  worker/          # Agent worker
    agent/
      llm/         # LiteLLM multi-provider wrapper
      tools/       # 55 tools across 10 categories
      executor.py  # LLM agent loop with function calling
  web/             # React admin panel
    src/
      pages/       # 21 page components
      components/  # Layout, search, notifications, error boundary
      hooks/       # WebSocket, notifications, dark mode, keyboard shortcuts
      api/         # API client with mock fallback for demo mode
  mail/            # Internal SMTP server
  docs/            # Architecture, API reference, deployment, tools guide
  scripts/         # Setup, add-worker, pre-deploy check
  monitoring/      # Prometheus & Grafana configs
  .github/         # CI/CD workflows
```

## Admin Panel Pages (21)

| Section | Pages |
|---------|-------|
| **Main** | Dashboard, Agents, Tasks, Workflows, Messages, Files |
| **Intelligence** | Collaboration, Knowledge Base, Analytics, Activity Feed |
| **Operations** | Schedules, Templates, Agent Presets |
| **System** | Workers, Users, Audit Log, Settings |
| **Detail** | Agent Detail (5 tabs), Task Detail, Workflow Builder |

## Tool Categories (55 Tools)

| Category | Count | Tools |
|----------|-------|-------|
| **Office** | 6 | Excel, Word, PowerPoint, PDF, Notes, Form Builder |
| **Communication** | 5 | Internal Email, External Email, Calendar, Notifications, SMS |
| **Research** | 6 | Web Browser, Web Search, Web Scraping, RSS Reader, Translator, Summarizer |
| **Data** | 6 | Analysis, Visualization, Report Generator, Database Query, Cleaning, Converter |
| **Filesystem** | 5 | File Manager, Cloud Storage, Image Processing, OCR, Backup |
| **Business** | 8 | Invoice, CRM, Time Tracker, Inventory, Project Tracker, Contract Generator, Expense Report, Task Tracker |
| **Technical** | 6 | Code Execution, Code Review, API Caller, Git Ops, Docker Ops, Shell |
| **Finance** | 3 | Bookkeeping, Currency Converter, Tax Calculator |
| **HR** | 3 | Leave Manager, Employee Directory, Payroll |
| **Integrations** | 7 | Slack, Jira, GitHub, Notion, Telegram, Google Workspace, Webhooks |

## API Reference (16 Modules)

| Module | Endpoints | Description |
|--------|-----------|-------------|
| `/api/v1/auth` | 2 | Login, current user |
| `/api/v1/agents` | 7 | CRUD, start, stop |
| `/api/v1/tasks` | 7 | CRUD, cancel, stats |
| `/api/v1/workflows` | 5 | CRUD, steps |
| `/api/v1/messages` | 3 | Send, list, mark read |
| `/api/v1/files` | 5 | Upload, download, presigned URL |
| `/api/v1/workers` | 4 | Register, heartbeat, task dispatch |
| `/api/v1/admin` | 4 | Users, workers, audit |
| `/api/v1/dashboard` | 1 | Overview stats |
| `/api/v1/settings` | 4 | CRUD, bulk update, health check |
| `/api/v1/analytics` | 4 | Overview, agents, timeline, utilization |
| `/api/v1/knowledge` | 4 | CRUD, categories |
| `/api/v1/collaboration` | 5 | Sessions, messages, context |
| `/api/v1/schedules` | 4 | CRUD for cron tasks |
| `/api/v1/exports` | 5 | Export/import agents, settings, knowledge |
| `/ws` | 1 | WebSocket real-time events |

## Development

```bash
make dev          # Start with hot reload
make test         # Run all tests
make lint         # Run linters (ruff, mypy, eslint, tsc)
make build        # Build Docker images
make status       # Check service status
make logs         # Tail all logs
make migrate      # Run database migrations
make check        # Pre-deployment validation
make monitoring   # Start Prometheus + Grafana
make backup       # Backup database
```

## Security

- JWT authentication with bcrypt password hashing
- Role-based access control (Admin, Operator, Viewer)
- Rate limiting (120 req/min per IP)
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options, etc.)
- Sandboxed code execution (memory/CPU limits, blocked dangerous operations)
- Audit logging on all critical actions
- CORS restricted to configured origins
- Pre-deployment security validation script

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/architecture.md) | System design, data flow, security layers |
| [API Reference](docs/api-reference.md) | All endpoints with request/response examples |
| [Deployment Guide](docs/deployment.md) | Installation, configuration, production checklist |
| [Tool Development](docs/tools-guide.md) | How to create new tools |
| [Contributing](docs/contributing.md) | Code standards, PR process |

## Contributing

1. Fork the repo
2. Create a feature branch
3. Follow code standards (ruff, mypy, eslint)
4. Add tests
5. Submit PR

See [CONTRIBUTING](docs/contributing.md) for details.

## License

Apache License 2.0. See [LICENSE](LICENSE).

---

<p align="center">
  <img src="assets/logo.png" alt="White-Ops" width="40" />
  <br />
  <sub>Built with Python, React, and AI.</sub>
</p>
