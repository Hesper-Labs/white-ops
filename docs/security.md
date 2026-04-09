# Security Guide

White-Ops implements defense-in-depth security across authentication, authorization, encryption, sandboxing, and infrastructure hardening.

## Authentication

### JWT Tokens

- Access tokens expire after 30 minutes; refresh tokens after 7 days
- Refresh token rotation: each refresh issues a new token pair and invalidates the old refresh token
- Audience validation (`whiteops-api`) and issuer validation (`whiteops`) on every request
- Fail-closed revocation: when Redis is unavailable for token blacklist checks, requests are **denied with 503** rather than allowed through
- Bcrypt password hashing via passlib

### MFA / TOTP

- TOTP enrollment with QR code generation using pyotp
- Backup codes for account recovery
- 1-window drift tolerance for clock skew
- Redis-backed MFA verification state tracks pending enrollments

### Account Security

- Account lockout after configurable failed attempts (default: 5 failures within 15 minutes)
- Login attempt recording with IP address tracking
- Password complexity requirements: minimum 12 characters, must include uppercase, lowercase, digit, and special character
- Password history enforcement: reuse of the last 5 passwords is blocked

### API Keys

- Bcrypt hashing for all new API keys (migrated from SHA-256)
- Backward-compatible verification: legacy SHA-256 hashes are still accepted during the transition period
- Keys generated via `secrets.token_urlsafe(32)`

## Authorization (RBAC)

Three built-in roles with 40+ granular permissions:

| Capability Area | Admin | Operator | Viewer |
|---|---|---|---|
| Create / Edit Agents | Yes | Yes | No |
| Delete Agents | Yes | No | No |
| Assign Tasks | Yes | Yes | No |
| View Dashboard | Yes | Yes | Yes |
| Manage Workers | Yes | No | No |
| System Settings | Yes | No | No |
| User Management | Yes | No | No |
| View Audit Logs | Yes | Yes | No |
| Manage Workflows | Yes | Yes | No |
| Manage Secrets Vault | Yes | No | No |
| Manage Webhooks | Yes | Yes | No |
| Manage Notifications | Yes | Yes | No |
| View Analytics / Costs | Yes | Yes | Yes |
| Manage Budgets | Yes | No | No |
| Manage Triggers | Yes | Yes | No |
| Approve Dangerous Tools | Yes | Yes | No |
| SSH Connections | Yes | No | No |

Permissions are enforced via FastAPI dependency injection: each endpoint declares required permissions, and the dependency validates the current user's role before the handler executes.

## Rate Limiting

### Redis Sliding Window

- Per-IP limit: 120 requests/minute
- Per-user limit: 300 requests/minute
- Per-endpoint overrides for sensitive routes:
  - Login: 20 requests/minute
  - Register: 10 requests/minute
  - Forgot password: 5 requests/minute

### In-Memory Fallback

When Redis is unavailable, rate limiting falls back to an in-memory store bounded at 10,000 keys to prevent unbounded memory growth.

## Secrets Vault

### Encryption

- AES-256 encryption using Fernet (symmetric, authenticated encryption)
- Mandatory `VAULT_MASTER_KEY` environment variable in production
- Server refuses to start in production if the master key is missing or shorter than 32 characters

### Lifecycle Management

- Secret rotation with version tracking (old versions retained for audit)
- Expiry monitoring via `check_expiring` to flag secrets nearing their expiration date
- Full audit trail on every operation: create, access, rotate, delete

## Middleware Security

### Security Headers

All responses include the following headers:

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | Configured per environment |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |
| `X-Permitted-Cross-Domain-Policies` | `none` |

### Request Controls

- Request ID (`X-Request-ID`) attached to every response for traceability
- Request body size limit: 10 MB (default)
- Response time header included for performance monitoring

## Tool Sandbox (Worker)

The worker executes LLM-chosen tools in a restricted environment. Each tool category has its own security controls.

### Shell Tool

- Regex-based pattern matching blocks dangerous commands: `rm -rf /`, `mkfs`, fork bombs (`:(){ :|:& };:`), piped installs (`curl | bash`, `wget | sh`)
- Malformed or unparseable commands are blocked (fail-closed, not allowed through)
- Chained commands are inspected: `&&`, `||`, `;`, and pipe chains are all analyzed for dangerous subcommands

### Code Execution

- Code is written to a separate file before execution (prevents injection into the executor process)
- Resource limits enforced: 256 MB RAM, 30 seconds CPU time, 50 file descriptors, 32 processes
- Blocked imports and constructs: `subprocess`, `socket`, `ctypes`, `importlib`, `__import__`, direct `builtins` access

### File Manager

- Symlink attack prevention: all paths are resolved to their real location before access checks
- Blocked system paths: `/etc`, `/usr`, `/bin`, `/proc`, `/sys`, and other OS directories
- Delete depth limit: maximum 5 directory levels to prevent accidental deep deletions
- Recursive symlink detection during deletion operations

### API Caller (SSRF Prevention)

- DNS resolution checks: resolved IP addresses are validated before connection
- Cloud metadata endpoint blocking: requests to `169.254.169.254` and equivalent addresses are rejected
- Redirect validation: redirects that resolve to private/internal IP addresses are blocked
- Response size limit: 1 MB maximum

### Database Tool (SQL Injection Prevention)

- Keyword-based detection of dangerous SQL operations
- Stacked query blocking (multiple statements separated by `;`)
- Comment stripping: single-line (`--`), multi-line (`/* */`), and dollar-quoted comments are removed before analysis
- String literals are removed before keyword analysis to reduce false negatives

## Nginx

- Rate limiting on auth endpoints: 5 requests/minute
- Rate limiting on general API: 30 requests/second
- Security headers (HSTS, CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy)
- Request body size limit: 10 MB
- WebSocket proxy with 24-hour connection timeout
- Hidden file access (dotfiles) denied

## Configuration Validation

### Production Startup Checks

The server refuses to start in production if any of the following are true:

- `SECRET_KEY` or `JWT_SECRET_KEY` is set to a default value or is shorter than 32 characters
- `SECRET_KEY` and `JWT_SECRET_KEY` are identical
- `POSTGRES_PASSWORD` is set to a default value
- `ADMIN_PASSWORD` is set to a default value
- `VAULT_MASTER_KEY` is missing or shorter than 32 characters
- `REDIS_PASSWORD` is set to a default value
- `CORS_ORIGINS` contains localhost

### Pre-Deployment Check Script

Run `make check` to validate all of the above plus:

- Port availability for all services
- Docker Compose configuration validity
- LLM API key presence

## Audit Logging

All security-relevant actions are recorded in the `audit_logs` table with structured logging via structlog.

### Tracked Action Types

- **Authentication**: login, logout, failed login, MFA enrollment
- **Agents**: create, update, delete
- **Tasks**: create, update, delete, assignment
- **Workflows**: create, update, delete, execution
- **Secrets Vault**: secret_created, secret_accessed, secret_rotated, secret_deleted
- **API Keys**: creation, revocation
- **Infrastructure**: circuit breaker trips, SSH connection events
- **Files**: upload, download, delete

Each log entry includes: timestamp, user ID, action type, resource type and ID, IP address, and request context.

## Docker Security

- All Python containers run as non-root user (`whiteops`)
- Multi-stage builds minimize image size and attack surface
- Health checks configured on all services
- Resource limits (CPU and memory) set on every container
- Internal Docker network isolates services from host

## Production Checklist

Before deploying to production, verify:

- [ ] All passwords and secrets changed from defaults (`make check` validates this)
- [ ] `SECRET_KEY` and `JWT_SECRET_KEY` are unique, random, and 32+ characters
- [ ] `VAULT_MASTER_KEY` is set and 32+ characters
- [ ] `POSTGRES_PASSWORD` and `REDIS_PASSWORD` are strong, non-default values
- [ ] `ADMIN_PASSWORD` is strong and non-default
- [ ] At least one LLM API key is configured
- [ ] `CORS_ORIGINS` is set to the production domain (no localhost)
- [ ] TLS/HTTPS is configured (nginx terminates TLS)
- [ ] `.env` file is not tracked by git
- [ ] Docker images are built from the production target
- [ ] Rate limiting is enabled and tested
- [ ] Monitoring (Prometheus + Grafana) is accessible
- [ ] Audit logging is writing to the database
- [ ] Backup schedule is configured for PostgreSQL
