# Security Guide

## Authentication

- JWT tokens with configurable expiry (default: 24 hours)
- bcrypt password hashing (passlib)
- Token stored in localStorage with auto-redirect on expiry

## Authorization (RBAC)

| Permission | Admin | Operator | Viewer |
|------------|-------|----------|--------|
| Create/Edit Agents | Yes | Yes | No |
| Assign Tasks | Yes | Yes | No |
| View Dashboard | Yes | Yes | Yes |
| Manage Workers | Yes | No | No |
| System Settings | Yes | No | No |
| User Management | Yes | No | No |
| View Audit Logs | Yes | No | No |
| Delete Resources | Yes | No | No |

## Network Security

- CORS restricted to configured origins (not wildcard)
- Security headers on all responses:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()`
  - `Content-Security-Policy` (nginx)
- Rate limiting: 120 requests/minute per IP
- Request ID tracking on all requests

## Code Execution Sandbox

Agent code execution (`code_exec` tool) runs with:
- Memory limit: 256MB
- CPU time limit: 30 seconds
- File operations restricted to `/tmp`
- Blocked imports: subprocess, socket, os.system, etc.
- Blocked shell commands: rm -rf, mkfs, shutdown, etc.
- Restricted PATH: `/usr/bin:/bin` only
- No network access from sandbox

## Audit Logging

All critical actions are logged to the `audit_logs` table:
- Login attempts (success and failure)
- Agent CRUD operations
- Task assignments and completions
- Worker approvals
- Settings changes
- File uploads

## Secrets Management

- All passwords generated randomly by setup script (32+ characters)
- API keys stored in database as secrets (masked in API responses)
- `.env` file excluded from git (in `.gitignore`)
- Pre-deploy check script validates no default passwords

## Production Checklist

Run `make check` to validate:
- [ ] All passwords changed from defaults
- [ ] At least one LLM API key configured
- [ ] CORS origins set to production domain
- [ ] .env not tracked by git
- [ ] Docker images built
- [ ] TLS/HTTPS configured
