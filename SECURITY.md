# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use [GitHub's private vulnerability reporting](https://github.com/Hesper-Labs/white-ops/security/advisories/new).

### Response timeline

- **Acknowledgment:** Within 48 hours
- **Initial assessment:** Within 1 week
- **Fix and disclosure:** Coordinated with reporter

## Security Features

- JWT authentication with bcrypt
- Role-based access control (Admin, Operator, Viewer)
- Rate limiting (120 req/min per IP)
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options)
- Sandboxed code execution (memory/CPU limits)
- Audit logging on all critical actions
- CORS restricted to configured origins
