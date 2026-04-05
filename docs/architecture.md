# White-Ops Architecture

## System Overview

White-Ops is a distributed AI agent platform built on a master-worker architecture.

```
                        Internet / LLM APIs
                              |
                    +---------+---------+
                    |   Load Balancer   |
                    |    (nginx/web)    |
                    +---------+---------+
                              |
                 +------------+------------+
                 |                         |
          +------+------+          +------+------+
          | Admin Panel |          |  API Server |
          | (React SPA) |  <--->  |  (FastAPI)  |
          +-------------+          +------+------+
                                          |
                    +---------------------+---------------------+
                    |                     |                     |
             +------+------+      +------+------+      +------+------+
             | PostgreSQL  |      |    Redis     |      |    MinIO    |
             | (data)      |      | (queue/cache)|      | (files)    |
             +-------------+      +------+------+      +-------------+
                                         |
                    +--------------------+--------------------+
                    |                    |                    |
             +------+------+     +------+------+     +------+------+
             |  Worker-01  |     |  Worker-02  |     |  Worker-N   |
             | Agent A,B,C |     | Agent D,E   |     | Agent F,G   |
             +-------------+     +-------------+     +-------------+
```

## Components

### API Server (server/)
- **Framework**: FastAPI with async SQLAlchemy
- **Auth**: JWT tokens with RBAC (admin/operator/viewer)
- **Middleware**: Rate limiting, request logging, security headers
- **Database**: PostgreSQL 16 with Alembic migrations
- **Cache/Queue**: Redis 7 for pub/sub and Celery task queue
- **File Storage**: MinIO (S3-compatible)
- **WebSocket**: Real-time event broadcasting

### Agent Worker (worker/)
- **Entry point**: Registers with master, sends heartbeats, polls for tasks
- **LLM Provider**: LiteLLM for multi-provider support (Claude, GPT, Gemini, Ollama)
- **Tool System**: Auto-discovery registry with 22+ tools across 10 categories
- **Executor**: Agent loop with function calling (tool use)
- **Sandbox**: Resource-limited code execution

### Admin Panel (web/)
- **Framework**: React 18 + TypeScript + Vite
- **State**: Zustand + TanStack Query
- **Styling**: Tailwind CSS
- **Pages**: 12 pages (Dashboard, Agents, Tasks, Workflows, Messages, Files, Workers, Analytics, Knowledge, Collaboration, Settings, Login)

### Internal Mail Server (mail/)
- **Protocol**: SMTP via aiosmtpd
- **Storage**: Redis-backed mailboxes
- **Purpose**: Agent-to-agent email communication

## Data Flow

### Task Execution
1. Admin creates task via web panel
2. Server stores task in PostgreSQL (status: pending)
3. Worker polls `/workers/{id}/tasks` endpoint
4. Server assigns task to an idle agent on that worker
5. Worker's executor runs LLM agent loop with tools
6. Agent calls tools (Excel, browser, etc.) as needed
7. Worker reports result back via `PATCH /tasks/{id}`
8. WebSocket broadcasts task completion to admin panel

### Agent Communication
1. Agent A calls `internal_email` tool to send message
2. Message stored via `/messages/send` API
3. Redis pub/sub notifies recipient agent
4. WebSocket broadcasts to admin panel
5. Agent B retrieves via `check_inbox`

## Security Layers

1. **Network**: HTTPS/TLS (nginx terminates), internal Docker network
2. **Auth**: JWT tokens, bcrypt password hashing
3. **RBAC**: Role-based access control on all API endpoints
4. **Rate Limiting**: Per-IP rate limiting (120 req/min)
5. **Input Validation**: Pydantic schemas on all inputs
6. **CORS**: Restricted origins
7. **Headers**: X-Content-Type-Options, X-Frame-Options, CSP, etc.
8. **Sandbox**: Resource-limited code execution, blocked dangerous operations
9. **Audit**: All actions logged to audit_logs table

## Scalability

- **Horizontal**: Add worker nodes on separate PCs
- **Database**: Connection pooling (pool_size=20, max_overflow=10)
- **Cache**: Redis for hot data and pub/sub
- **Storage**: MinIO supports federation for large deployments
- **Monitoring**: Prometheus metrics + Grafana dashboards
