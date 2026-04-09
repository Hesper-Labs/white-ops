# Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose v2
- Minimum 4 CPU cores / 8 GB RAM (16 GB recommended for production)
- 20 GB+ disk space
- At least one LLM API key (Anthropic, OpenAI, Google, or local Ollama)
- Open ports: 3000 (web), 8000 (API), 9000-9001 (MinIO)

## Quick Start (Single Machine)

```bash
git clone https://github.com/your-org/white-ops.git
cd white-ops
./scripts/setup.sh
```

This automatically:
1. Generates cryptographically secure secrets in `.env`
2. Builds all Docker images
3. Starts all services
4. Creates the admin account

Access: `http://localhost:3000`

## Manual Setup

```bash
cp .env.example .env
# Edit .env - set all passwords and at least one LLM API key
make build
make up
```

## Environment Variables

### General

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_NAME` | No | Application name (default: `white-ops`) |
| `APP_ENV` | No | Environment: `development`, `staging`, `production` |
| `SECRET_KEY` | Yes | App secret key, >= 32 characters |
| `DEBUG` | No | Enable debug mode (default: `false`) |

### Database (PostgreSQL)

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_HOST` | Yes | Database hostname (default: `postgres`) |
| `POSTGRES_PORT` | No | Database port (default: `5432`) |
| `POSTGRES_DB` | Yes | Database name (default: `whiteops`) |
| `POSTGRES_USER` | Yes | Database user (default: `whiteops`) |
| `POSTGRES_PASSWORD` | Yes | Database password |

### Redis

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_HOST` | Yes | Redis hostname (default: `redis`) |
| `REDIS_PORT` | No | Redis port (default: `6379`) |
| `REDIS_PASSWORD` | Yes | Redis password |

### MinIO (Object Storage)

| Variable | Required | Description |
|----------|----------|-------------|
| `MINIO_ENDPOINT` | Yes | MinIO endpoint (default: `minio:9000`) |
| `MINIO_ROOT_USER` | Yes | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | Yes | MinIO admin password (min 8 chars) |
| `MINIO_BUCKET` | No | Default bucket name (default: `whiteops`) |
| `MINIO_USE_SSL` | No | Use SSL for MinIO connections (default: `false`) |

### Authentication

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | Yes | JWT signing key, >= 32 chars, must differ from `SECRET_KEY` |
| `JWT_ALGORITHM` | No | JWT algorithm (default: `HS256`) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | Access token TTL (default: `30`) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | No | Refresh token TTL (default: `7`) |
| `ADMIN_EMAIL` | Yes | Initial admin account email |
| `ADMIN_PASSWORD` | Yes | Initial admin account password |

### Security

| Variable | Required | Description |
|----------|----------|-------------|
| `PASSWORD_MIN_LENGTH` | No | Minimum password length (default: `12`) |
| `MAX_LOGIN_ATTEMPTS` | No | Failed attempts before lockout (default: `5`) |
| `LOCKOUT_DURATION_MINUTES` | No | Lockout duration in minutes (default: `30`) |
| `MFA_ENABLED` | No | Enable MFA/TOTP support (default: `false`) |
| `ALLOWED_IPS` | No | Comma-separated IP allowlist (empty = all allowed) |
| `REQUEST_BODY_MAX_SIZE_MB` | No | Max request body size in MB (default: `10`) |

### Rate Limiting

| Variable | Required | Description |
|----------|----------|-------------|
| `RATE_LIMIT_PER_IP` | No | Max requests per IP per window (default: `100`) |
| `RATE_LIMIT_PER_USER` | No | Max requests per user per window (default: `200`) |
| `RATE_LIMIT_WINDOW_SECONDS` | No | Rate limit window in seconds (default: `60`) |

### Vault (Secrets Encryption)

| Variable | Required | Description |
|----------|----------|-------------|
| `VAULT_MASTER_KEY` | **Yes (prod)** | AES-256 Fernet key, >= 32 chars. **Required in production.** Generate with: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` |

### Mail

| Variable | Required | Description |
|----------|----------|-------------|
| `MAIL_SERVER_HOST` | No | Internal mail server host (default: `mail`) |
| `MAIL_SERVER_PORT` | No | Internal mail server port (default: `8025`) |
| `MAIL_DOMAIN` | No | Mail domain for inter-agent email |
| `SMTP_HOST` | No | External SMTP host for notifications |
| `SMTP_PORT` | No | External SMTP port (default: `587`) |
| `SMTP_USER` | No | External SMTP username |
| `SMTP_PASSWORD` | No | External SMTP password |
| `SMTP_FROM` | No | Sender address for outbound email |
| `SMTP_USE_TLS` | No | Use TLS for SMTP (default: `true`) |

### CORS

| Variable | Required | Description |
|----------|----------|-------------|
| `CORS_ORIGINS` | Yes (prod) | Comma-separated allowed origins (default: `http://localhost:3000`) |

### Integrations

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook for notifications |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for notifications |

### Cost Management

| Variable | Required | Description |
|----------|----------|-------------|
| `MONTHLY_BUDGET_USD` | No | Monthly budget cap in USD (default: unlimited) |
| `BUDGET_ALERT_THRESHOLDS` | No | Comma-separated alert thresholds, e.g. `50,80,95` |

### LLM Providers

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | At least one | Claude API key |
| `OPENAI_API_KEY` | At least one | OpenAI API key |
| `GOOGLE_API_KEY` | At least one | Google AI (Gemini) API key |
| `OLLAMA_BASE_URL` | At least one | Ollama endpoint for local models |
| `DEFAULT_LLM_PROVIDER` | No | Default provider: `anthropic`, `openai`, `google`, `ollama` |
| `DEFAULT_LLM_MODEL` | No | Default model name (e.g. `claude-sonnet-4-20250514`) |

### Workers

| Variable | Required | Description |
|----------|----------|-------------|
| `WORKER_NAME` | No | Worker node name (auto-generated if empty) |
| `WORKER_MAX_AGENTS` | No | Max concurrent agents per worker (default: `5`) |

### Monitoring

| Variable | Required | Description |
|----------|----------|-------------|
| `GRAFANA_ADMIN_PASSWORD` | Yes (monitoring) | Grafana admin password |

## Docker Compose Setup

The platform runs 12 services orchestrated via Docker Compose:

| Service | Description | Port |
|---------|-------------|------|
| `postgres` | PostgreSQL 16 database | 5432 |
| `redis` | Redis 7 (cache, queues, pub/sub) | 6379 |
| `minio` | MinIO object storage | 9000, 9001 |
| `server` | FastAPI backend | 8000 |
| `worker` | Agent executor node | - |
| `celery-worker` | Celery task worker | - |
| `celery-beat` | Celery periodic scheduler | - |
| `web` | React SPA (nginx) | 3000 |
| `mail` | Internal SMTP server | 8025 |
| `prometheus` | Metrics collection (monitoring profile) | 9090 |
| `grafana` | Dashboards (monitoring profile) | 3001 |
| `exporters` | Redis + Postgres exporters (monitoring profile) | 9121, 9187 |

### Key Configuration Details

- **Redis persistence**: AOF (appendonly) + RDB snapshots are both enabled for durability.
- **Monitoring is optional**: Start monitoring services with `docker compose --profile monitoring up -d`.
- **Resource limits**: All containers have CPU and memory limits defined. Adjust in `docker-compose.yml` if needed.
- **Health checks**: Every service includes a health check. Use `make status` to verify.

### Starting Services

```bash
# All core services
make up

# Core + monitoring
docker compose --profile monitoring up -d

# View status
make status

# View logs
make logs
make logs-server
```

## Adding Worker Nodes

On each additional PC:

```bash
# Option 1: Script
./scripts/add-worker.sh <MASTER_IP>

# Option 2: Manual
# Copy docker-compose.worker.yml to remote PC
# Set MASTER_URL, REDIS_PASSWORD, MINIO_ROOT_PASSWORD
# docker compose up -d
```

Then approve the worker in Admin Panel > Workers.

## Kubernetes / Helm Deployment

The Helm chart is located at `deploy/helm/white-ops/`.

### Templates

The chart includes the following Kubernetes resources:

- **Deployments (6)**: server, worker, celery-worker, celery-beat, web, mail
- **Services (7)**: One per deployment plus internal headless services
- **StatefulSets (3)**: postgres, redis, minio (with PVCs)
- **ConfigMap**: Application configuration
- **PodDisruptionBudgets (PDB)**: Ensures minimum availability during rollouts
- **ServiceAccount**: Dedicated service account with RBAC
- **HorizontalPodAutoscaler (HPA)**: Auto-scales server and worker pods
- **NetworkPolicy**: Restricts inter-pod traffic to required paths only
- **Ingress**: TLS-terminated ingress for web and API

### Required Secrets

Create these Kubernetes secrets before installing the chart:

```bash
kubectl create secret generic whiteops-postgres-secret \
  --from-literal=POSTGRES_PASSWORD=<password>

kubectl create secret generic whiteops-redis-secret \
  --from-literal=REDIS_PASSWORD=<password>

kubectl create secret generic whiteops-minio-secret \
  --from-literal=MINIO_ROOT_USER=<user> \
  --from-literal=MINIO_ROOT_PASSWORD=<password>

kubectl create secret generic whiteops-llm-secret \
  --from-literal=ANTHROPIC_API_KEY=<key> \
  --from-literal=OPENAI_API_KEY=<key>
```

### Install

```bash
cd deploy/helm
helm install white-ops ./white-ops -n whiteops --create-namespace \
  -f white-ops/values-production.yaml
```

### Security Features

- **HPA**: Automatic horizontal scaling based on CPU/memory
- **PDB**: Pod disruption budgets prevent excessive downtime
- **NetworkPolicy**: Only allows required ingress/egress between pods
- **Ingress TLS**: TLS termination at the ingress controller
- **runAsNonRoot**: All containers run as non-root users
- **readOnlyRootFilesystem**: Containers use read-only root filesystems where possible

## Production Checklist

1. [ ] All passwords and API keys set to strong, unique random values
2. [ ] `SECRET_KEY` is >= 32 characters and not the default
3. [ ] `JWT_SECRET_KEY` is >= 32 characters and **different** from `SECRET_KEY`
4. [ ] `VAULT_MASTER_KEY` is >= 32 characters (generate with: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`)
5. [ ] `CORS_ORIGINS` set to your production domain (not localhost)
6. [ ] `MFA_ENABLED=true`
7. [ ] `GRAFANA_ADMIN_PASSWORD` set to a strong password
8. [ ] Run `make check` to validate configuration
9. [ ] Review Nginx security headers (HSTS, CSP, X-Frame-Options, etc.)
10. [ ] Set up monitoring (`docker compose --profile monitoring up -d`)
11. [ ] Configure backup schedule (see Backup section below)
12. [ ] Test disaster recovery procedure

## Monitoring Setup

### Enabling Monitoring

```bash
docker compose --profile monitoring up -d
```

### Endpoints

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (login: `admin` / `GRAFANA_ADMIN_PASSWORD`)

### Exporters

The monitoring profile includes:
- **redis-exporter**: Exports Redis metrics (connections, memory, commands)
- **postgres-exporter**: Exports PostgreSQL metrics (connections, transactions, locks)

### Alert Rules

Seven preconfigured alert rules are included:

| Alert | Condition |
|-------|-----------|
| `HighErrorRate` | HTTP 5xx error rate exceeds threshold |
| `WorkerOffline` | Worker node stops sending heartbeats |
| `HighMemory` | Container memory usage above limit |
| `TaskQueueBacklog` | Pending task queue grows beyond threshold |
| `DiskSpaceLow` | Disk usage exceeds safe limit |
| `RedisMemoryHigh` | Redis memory usage above configured max |
| `SlowResponses` | API response latency exceeds threshold |

## Backup and Restore

### Database Backup

```bash
# Using make
make backup

# Manual
docker compose exec postgres pg_dump -U whiteops whiteops > backup_$(date +%Y%m%d).sql
```

### Database Restore

```bash
# Using make
make restore FILE=backup_20260409.sql

# Manual
docker compose exec -i postgres psql -U whiteops whiteops < backup_20260409.sql
```

### File Storage Backup (MinIO)

```bash
docker compose exec minio mc mirror /data /backup
```

### Recommended Schedule

- Database: daily automated backups with 30-day retention
- MinIO files: daily sync to external storage
- Configuration (`.env`): version-controlled or backed up separately

## Updating

```bash
git pull
make build
make up  # Rolling restart
```

## Troubleshooting

### Diagnostic Commands

```bash
make status        # Check all service health
make logs          # View all logs
make logs-server   # View server logs only
make shell-server  # Open shell in server container
make shell-db      # Open psql shell
make check         # Pre-deployment validation
```

### Common Issues

- **Port conflict**: Change ports in `.env` (`SERVER_PORT`, `WEB_PORT`)
- **Worker cannot connect**: Check firewall rules; ensure ports 8000, 6379, 9000 are accessible from the worker
- **LLM errors**: Verify the API key in Settings page; check provider status
- **Out of memory**: Increase Docker memory limit or reduce `WORKER_MAX_AGENTS`
- **Database connection refused**: Verify `POSTGRES_HOST` and `POSTGRES_PASSWORD`; check `make status` for postgres health
- **Redis connection timeout**: Verify `REDIS_HOST` and `REDIS_PASSWORD`; check Redis container logs
- **MinIO bucket not found**: The server auto-creates the bucket on startup; check MinIO credentials
- **Vault errors in production**: Ensure `VAULT_MASTER_KEY` is set; it is required for secrets encryption
- **Celery tasks not processing**: Check celery-worker logs with `docker compose logs celery-worker`; verify Redis connectivity
