# White-Ops Architecture

White-Ops is an enterprise AI workforce platform that deploys LLM-driven agents across multiple machines to handle professional tasks. It uses a master-worker architecture: a FastAPI server orchestrates task assignment, worker nodes execute tasks via LLM function-calling loops with 83+ tools, and a React admin panel provides the management UI.

## System Topology

```
React SPA (37 pages) --> Nginx --> FastAPI Server (29 API modules) --> PostgreSQL + Redis + MinIO
                                        |  WebSocket                       |  Redis Pub/Sub
                                      Celery Workers                    Worker Nodes (83+ tools)
                                      (celery-worker, celery-beat)
```

## Docker Services (12)

| Service | Technology | Purpose |
|---|---|---|
| PostgreSQL | PostgreSQL 16 | Primary data store |
| Redis | Redis 7 (AOF + RDB persistence) | Cache, pub/sub, rate limiting, circuit breakers, Celery broker |
| MinIO | S3-compatible object storage | File storage for agent uploads and outputs |
| Server | FastAPI (Python 3.12) | API backend, WebSocket, orchestration |
| Worker | Python 3.12 + LiteLLM | Agent execution with LLM function-calling |
| Celery Worker | Celery 5 | Background task processing |
| Celery Beat | Celery Beat | Scheduled task execution (triggers, cleanup) |
| Nginx | nginx | Reverse proxy, TLS termination, static frontend |
| Mail | aiosmtpd | Internal SMTP for inter-agent email |
| Prometheus | Prometheus | Metrics collection and alerting |
| Grafana | Grafana | Dashboards and visualization |
| Exporters | redis-exporter, postgres-exporter | Metrics export for Redis and PostgreSQL |

## Components

### API Server (`server/`)

**Framework**: FastAPI with async SQLAlchemy 2.0, Pydantic v2 schemas, and Alembic migrations.

**29 API Modules** under `app/api/v1/`: agents, tasks, workers, workflows, messages, files, users, auth, settings, dashboard, analytics, audit, secrets, ssh, approvals, webhooks, notifications, budgets, triggers, cost, circuit_breakers, agent_memory, agent_skills, dead_letter, health, websocket, api_keys, mfa, sessions.

**Services Layer**:

| Service | Responsibility |
|---|---|
| Orchestrator | Agent scoring (capacity, tools, worker load), task assignment |
| Storage | MinIO file operations, upload/download management |
| Queue | Redis pub/sub, Celery task dispatch |
| Audit | Structured logging of all security-relevant actions |
| Vault | AES-256 encrypted secrets with rotation and expiry |
| Workflow | Multi-step DAG execution engine |
| Notifications | Multi-channel alerts (email, webhook, in-app) |
| Cost Tracker | Per-agent, per-task, per-provider cost tracking with budget alerts |
| Triggers | Cron-based and event-based task automation |
| Circuit Breakers | Redis-backed resilience for external services |

**WebSocket**: Real-time event broadcasting to the admin panel for task updates, agent status changes, and system notifications.

### Agent Worker (`worker/`)

**LLM Support**: LiteLLM provides a unified interface to multiple providers:
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- Ollama (local models)

**Tool System**: 83 tools organized into 14 categories, auto-discovered by `ToolRegistry`:

| Category | Examples |
|---|---|
| Office | Excel, Word, PowerPoint, PDF |
| Communication | Email, internal messaging |
| Research | Web search, web scraping, Playwright browser |
| Data | Data analysis, visualization, pandas |
| Filesystem | File read/write/manage, directory operations |
| Business | CRM, project management |
| Technical | Code execution, shell, git |
| Finance | Invoice, reporting |
| HR | Scheduling, document generation |
| Integrations | REST APIs, webhooks |
| DevOps | Docker, CI/CD |
| Monitoring | System health, metrics |
| Cloud | AWS (S3, EC2), cloud storage |
| Security Tools | Vulnerability scanning, credential management |

**Execution Model**:
- LLM function-calling loop with a maximum of 50 iterations per task
- Parallel tool execution via semaphore (concurrency limit: 5)
- Retry logic with exponential backoff for transient failures
- Each tool extends `BaseTool` (abstract class in `worker/agent/tools/base.py`)
- Tool definitions are sent to the LLM as JSON schema for function calling
- Dangerous operations require human approval before execution

### Admin Panel (`web/`)

**Framework**: React 18, TypeScript, Vite, Tailwind CSS with dark mode support.

**37 Pages** including: Dashboard, Agents, Agent Detail, Tasks, Task Detail, Workflows, Workflow Builder, Messages, Files, Workers, Worker Detail, Analytics, Knowledge, Collaboration, Settings, Login, Register, Profile, Notifications, Secrets Vault, SSH Connections, Approvals, Triggers, Budgets, Audit Logs, API Keys, and more.

**State Management**:
- Zustand stores for auth state, theme, and UI preferences
- TanStack Query for server data fetching and cache management

**UI Components**:
- Shared component library under `components/ui/`
- ErrorBoundary for graceful error handling
- DemoBanner for demo environment indication
- QueryError for standardized API error display
- Recharts for data visualization
- i18next for internationalization
- cmdk for command palette

### Internal Mail Server (`mail/`)

- aiosmtpd-based SMTP server for inter-agent communication
- Redis-backed mailbox storage with a limit of 1,000 messages per mailbox
- Pub/sub notifications when new mail arrives
- Agents use `internal_email` and `check_inbox` tools to send and receive

### Monitoring (`monitoring/`)

- **Prometheus**: Metrics collection with 7 alert rules covering service health, resource usage, and error rates
- **Grafana**: Pre-configured dashboards for system overview, agent performance, and cost tracking
- **redis-exporter**: Redis metrics (memory, connections, commands)
- **postgres-exporter**: PostgreSQL metrics (connections, queries, replication)

### Deployment (`deploy/`)

Helm chart for Kubernetes with:

| Resource | Purpose |
|---|---|
| Deployments | Server, worker, Celery, Nginx, mail |
| StatefulSets | PostgreSQL, Redis, MinIO |
| Services | Internal networking and load balancing |
| HPA | Horizontal Pod Autoscaler for server and workers |
| PDB | Pod Disruption Budgets for availability |
| NetworkPolicy | Service-to-service traffic restrictions |
| Ingress | External HTTP/HTTPS routing |
| ConfigMap | Environment configuration |
| ServiceAccount | RBAC for pod identity |

## Key Patterns

### Task Flow

1. User creates a task via the web panel or API
2. Server stores the task in PostgreSQL with status `pending`
3. Orchestrator scores available agents based on capacity, required tools, and worker load
4. Task is assigned to the best-scoring agent
5. Worker picks up the task and starts the LLM function-calling loop (max 50 iterations)
6. Agent calls tools as needed; results feed back into the LLM context
7. Worker reports the final result via `PATCH /tasks/{id}`
8. WebSocket broadcasts the completion event to the admin panel

### Tool System

- `BaseTool` abstract class defines the interface: `name`, `description`, `parameters` (JSON schema), and `execute()`
- `ToolRegistry` auto-discovers tools from subdirectories under `worker/agent/tools/`
- Tool parameter schemas are sent to the LLM for function calling
- Tools marked as dangerous require human approval via the approvals system
- Parallel execution with a semaphore limits concurrent tool calls to 5

### Authentication and Authorization

- JWT access tokens (30 min) with refresh token rotation (7 days)
- MFA/TOTP with backup codes and QR enrollment
- 40+ granular permissions mapped to 3 roles (admin, operator, viewer)
- Account lockout after repeated failed login attempts

### Secrets Vault

- AES-256 Fernet encryption at rest
- Mandatory master key in production (server refuses to start without it)
- Secret rotation with version history
- Full audit logging on all vault operations

### Circuit Breakers

- Redis-backed state machine: closed (normal) --> open (failing) --> half-open (testing recovery)
- Configurable failure thresholds, timeout duration, and recovery attempts
- Applied to external services: LLM APIs, MinIO, Redis

### Cost Tracking

- Token usage recorded per agent, per task, and per LLM provider
- Budget system with configurable limits and alert thresholds
- Cost rate configuration per provider and model
- Dashboard visualization of spend over time

### Rate Limiting

- Redis sliding-window algorithm for accurate rate counting
- Per-IP (120/min), per-user (300/min), and per-endpoint overrides
- In-memory fallback (bounded at 10K keys) when Redis is unavailable

## Data Model

### Core Entities

| Model | Key Fields |
|---|---|
| User | email, role, MFA status, lockout state |
| Agent | name, LLM config, enabled tools, stats, cost totals |
| Task | status lifecycle, assigned agent, progress, cost, result |
| Worker | hostname, host metrics, capabilities, GPU info |
| Message | sender/recipient agents, subject, body |
| File | filename, MinIO path, size, content type |
| Workflow | name, steps (DAG), status, execution history |
| Settings | key-value application configuration |
| AuditLog | action, user, resource, IP, timestamp |

### Enterprise Entities

| Model | Purpose |
|---|---|
| Secret | Encrypted vault entries with rotation and expiry |
| SSHConnection | Remote server connection profiles |
| ApprovalRule / ApprovalRequest | Dangerous operation approval workflow |
| AgentMemory / AgentSkill | Persistent agent knowledge and learned capabilities |
| Trigger / TriggerExecution | Cron and event-based task automation |
| WebhookEndpoint | External webhook integrations |
| NotificationChannel / NotificationRule / Notification | Multi-channel alerting system |
| TokenUsage / Budget / CostRate | Cost tracking and budget management |
| DeadLetterTask / TaskCheckpoint / CircuitBreakerState | Resilience and recovery infrastructure |
| UserMFA / APIKey / UserSession / LoginAttempt | Authentication and session management |

### Model Conventions

All models inherit from a shared base providing:
- UUID primary key
- `created_at` timestamp (auto-set)
- `updated_at` timestamp (auto-updated)
- `deleted_at` timestamp for soft deletes

## Scalability

- **Horizontal scaling**: Add worker nodes on separate machines; the orchestrator automatically distributes tasks
- **Database**: Async connection pooling via asyncpg (pool_size=20, max_overflow=10)
- **Cache**: Redis for hot data, session state, rate limiting, and pub/sub messaging
- **Storage**: MinIO supports federation for large-scale file storage
- **Background jobs**: Celery with Redis broker for async task processing
- **Kubernetes**: HPA scales server and worker pods based on CPU/memory; PDBs ensure availability during rollouts
- **Monitoring**: Prometheus metrics and Grafana dashboards provide visibility into all services
