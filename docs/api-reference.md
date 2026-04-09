# API Reference

Base URL: `http://localhost:8000/api/v1`

All endpoints require a JWT token in the `Authorization: Bearer <token>` header unless noted otherwise.

---

## Authentication

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/auth/login` | Login with email/password, returns access + refresh tokens | No |
| POST | `/auth/register` | Register a new user account | No |
| POST | `/auth/refresh` | Refresh access token using refresh token | No |
| GET | `/auth/me` | Get current user profile | Yes |
| PUT | `/auth/me` | Update current user profile | Yes |
| POST | `/auth/change-password` | Change current user password | Yes |
| POST | `/auth/mfa/setup` | Initialize MFA/TOTP setup, returns QR code | Yes |
| POST | `/auth/mfa/verify` | Verify MFA token and activate MFA | Yes |
| POST | `/auth/mfa/disable` | Disable MFA for current user | Yes |
| POST | `/auth/logout` | Invalidate current session | Yes |

---

## Agents

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/agents/` | List all agents. Query: `status_filter`, `role` | Yes |
| POST | `/agents/` | Create agent. Body: name, description, role, llm_provider, llm_model, system_prompt, enabled_tools, worker_id | Yes |
| GET | `/agents/{id}` | Get agent details | Yes |
| PATCH | `/agents/{id}` | Update agent (partial update) | Yes |
| DELETE | `/agents/{id}` | Delete agent (soft delete) | Yes |
| POST | `/agents/{id}/start` | Activate agent (status -> idle) | Yes |
| POST | `/agents/{id}/stop` | Deactivate agent (status -> offline) | Yes |

---

## Tasks

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/tasks/` | List tasks. Query: `status_filter`, `priority`, `agent_id`, `limit`, `offset` | Yes |
| POST | `/tasks/` | Create task. Body: title, description, instructions, priority, agent_id, deadline, required_tools | Yes |
| GET | `/tasks/stats` | Task statistics by status and priority | Yes |
| GET | `/tasks/{id}` | Get task details including result | Yes |
| PATCH | `/tasks/{id}` | Update task fields | Yes |
| POST | `/tasks/{id}/cancel` | Cancel a running task | Yes |

---

## Workflows

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/workflows/` | List workflows | Yes |
| POST | `/workflows/` | Create workflow. Body: name, description, is_template, config | Yes |
| GET | `/workflows/{id}` | Get workflow with all steps | Yes |
| POST | `/workflows/{id}/steps` | Add step. Body: name, step_type, order, config, agent_id, depends_on | Yes |
| DELETE | `/workflows/{id}` | Delete workflow | Yes |

---

## Messages

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/messages/` | List messages. Query: `agent_id`, `channel`, `limit`, `offset` | Yes |
| POST | `/messages/send` | Send message. Body: sender_agent_id, recipient_agent_id, channel, subject, body | Yes |
| PATCH | `/messages/{id}/read` | Mark message as read | Yes |

---

## Files

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/files/` | List files. Query: `task_id`, `limit` | Yes |
| POST | `/files/upload` | Upload file (multipart/form-data). Query: `task_id` | Yes |
| GET | `/files/{id}` | Get file metadata | Yes |
| GET | `/files/{id}/download` | Download file content | Yes |
| GET | `/files/{id}/url` | Get presigned download URL (expires in 1 hour) | Yes |
| DELETE | `/files/{id}` | Delete file from storage and database | Yes |

---

## Workers

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/workers/register` | Register worker node. Body: name, hostname, ip_address, max_agents, cpu_cores, memory_total_mb, os_info | Yes |
| POST | `/workers/{id}/heartbeat` | Send heartbeat. Body: cpu_usage_percent, memory_usage_percent, disk_usage_percent | Yes |
| GET | `/workers/{id}/tasks` | Get pending tasks for this worker's agents | Yes |
| GET | `/workers/overview` | Fleet overview statistics | Yes |

---

## Admin

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/users` | List all users (admin only) | Admin |
| POST | `/admin/users` | Create user. Body: email, password, full_name, role | Admin |
| GET | `/admin/workers` | List all workers with metrics | Admin |
| PATCH | `/admin/workers/{id}/approve` | Approve/reject worker. Body: is_approved, group | Admin |
| GET | `/admin/audit` | Audit log. Query: `limit`, `offset` | Admin |

---

## Settings

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/settings/` | Get all settings grouped by category | Admin |
| PUT | `/settings/{category}/{key}` | Update single setting. Body: `{value}` | Admin |
| PUT | `/settings/bulk` | Update multiple settings. Body: `{settings: {"category.key": "value"}}` | Admin |
| GET | `/settings/health` | System health check (database, Redis, MinIO, mail) | Admin |

---

## Analytics

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/analytics/overview` | Platform analytics. Query: `days` (default: 7) | Yes |
| GET | `/analytics/agents` | Per-agent performance metrics | Yes |
| GET | `/analytics/tasks/timeline` | Task creation timeline for charts. Query: `days` | Yes |
| GET | `/analytics/workers/utilization` | Live worker resource utilization | Yes |

---

## Knowledge Base

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/knowledge/` | List entries. Query: `category`, `search`, `limit` | Yes |
| POST | `/knowledge/` | Create entry. Body: title, content, category, tags, source | Yes |
| GET | `/knowledge/{id}` | Get full entry | Yes |
| DELETE | `/knowledge/{id}` | Delete entry | Yes |

---

## Collaboration

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/collaboration/` | List sessions. Query: `status` | Yes |
| POST | `/collaboration/` | Create session. Body: name, description, participants, initial_context | Yes |
| GET | `/collaboration/{id}` | Get session with messages | Yes |
| POST | `/collaboration/{id}/messages` | Add message. Body: agent_id, message, message_type | Yes |
| POST | `/collaboration/{id}/context` | Update shared context. Body: `{key: value}` | Yes |
| POST | `/collaboration/{id}/close` | Close collaboration session | Yes |

---

## Chat

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/chat/conversations` | List conversations for current user | Yes |
| POST | `/chat/conversations` | Create a new conversation | Yes |
| GET | `/chat/conversations/{id}/messages` | Get messages in a conversation | Yes |
| POST | `/chat/conversations/{id}/messages` | Send a message in a conversation | Yes |
| DELETE | `/chat/conversations/{id}` | Delete a conversation | Yes |

---

## Cost Management

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/cost/summary` | Overall cost summary (total spend, period breakdown) | Yes |
| GET | `/cost/daily` | Daily cost breakdown. Query: `days` | Yes |
| GET | `/cost/by-agent` | Cost breakdown per agent | Yes |
| GET | `/cost/by-provider` | Cost breakdown per LLM provider | Yes |
| GET | `/cost/budget` | Get current budget configuration and usage | Yes |
| PUT | `/cost/budget` | Update budget settings. Body: monthly_limit, alert_thresholds | Admin |

---

## Circuit Breakers

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/circuit-breakers` | List all circuit breakers and their states | Admin |
| POST | `/circuit-breakers` | Create or update a circuit breaker configuration | Admin |
| POST | `/circuit-breakers/{name}/force-open` | Force a circuit breaker to open state | Admin |
| POST | `/circuit-breakers/{name}/force-close` | Force a circuit breaker to closed state | Admin |
| POST | `/circuit-breakers/{name}/reset` | Reset circuit breaker to default closed state | Admin |

---

## Dead Letter Queue

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/dead-letter` | List dead letter tasks. Query: `limit`, `offset` | Admin |
| POST | `/dead-letter` | Manually add a task to the dead letter queue | Admin |
| POST | `/dead-letter/{id}/retry` | Retry a single dead letter task | Admin |
| POST | `/dead-letter/retry-all` | Retry all dead letter tasks | Admin |
| DELETE | `/dead-letter/{id}` | Remove a dead letter task | Admin |
| GET | `/dead-letter/stats` | Dead letter queue statistics | Admin |

---

## Security

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/security` | Get current security configuration | Admin |
| PUT | `/security` | Update security settings | Admin |
| GET | `/security/password-policy` | Get password policy rules | Admin |
| PUT | `/security/password-policy` | Update password policy | Admin |
| GET | `/security/sessions` | List active user sessions | Admin |
| GET | `/security/ip-rules` | List IP allowlist/blocklist rules | Admin |
| PUT | `/security/ip-rules` | Update IP rules | Admin |
| GET | `/security/api-keys` | List API keys | Yes |
| POST | `/security/api-keys` | Create a new API key | Yes |
| DELETE | `/security/api-keys/{id}` | Revoke an API key | Yes |

---

## Agent Memory

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/agents/{id}/memories` | List memories for an agent. Query: `category`, `limit` | Yes |
| POST | `/agents/{id}/memories` | Create a memory entry for an agent | Yes |
| PUT | `/agents/memories/{id}` | Update a memory entry | Yes |
| DELETE | `/agents/memories/{id}` | Delete a memory entry | Yes |
| GET | `/agents/{id}/memory-stats` | Memory usage statistics for an agent | Yes |

---

## Triggers

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/triggers` | List all triggers | Yes |
| POST | `/triggers` | Create a trigger. Body: name, type, config, action | Yes |
| GET | `/triggers/{id}` | Get trigger details | Yes |
| PUT | `/triggers/{id}` | Update a trigger | Yes |
| DELETE | `/triggers/{id}` | Delete a trigger | Yes |
| POST | `/triggers/{id}/toggle` | Enable or disable a trigger | Yes |
| GET | `/triggers/{id}/history` | Get trigger execution history | Yes |

---

## Notifications

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/notifications` | List notifications for current user. Query: `limit`, `offset` | Yes |
| GET | `/notifications/unread-count` | Get count of unread notifications | Yes |
| PUT | `/notifications/{id}/read` | Mark a notification as read | Yes |
| PUT | `/notifications/read-all` | Mark all notifications as read | Yes |
| GET | `/notifications/channels` | List notification channels (email, Slack, Telegram) | Admin |
| POST | `/notifications/channels` | Create a notification channel | Admin |
| PUT | `/notifications/channels/{id}` | Update a notification channel | Admin |
| DELETE | `/notifications/channels/{id}` | Delete a notification channel | Admin |
| GET | `/notifications/rules` | List notification rules | Admin |
| POST | `/notifications/rules` | Create a notification rule | Admin |
| PUT | `/notifications/rules/{id}` | Update a notification rule | Admin |
| DELETE | `/notifications/rules/{id}` | Delete a notification rule | Admin |

---

## Webhooks

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/webhooks` | List registered webhooks | Yes |
| POST | `/webhooks` | Create a webhook. Body: url, events, secret | Yes |
| GET | `/webhooks/{id}` | Get webhook details | Yes |
| PUT | `/webhooks/{id}` | Update a webhook | Yes |
| DELETE | `/webhooks/{id}` | Delete a webhook | Yes |
| POST | `/webhooks/{id}/test` | Send a test payload to a webhook | Yes |

---

## Approvals

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/approvals` | Create an approval request | Yes |
| GET | `/approvals` | List pending approval requests | Yes |
| GET | `/approvals/{id}` | Get approval request details | Yes |
| POST | `/approvals/{id}/approve` | Approve a request | Yes |
| POST | `/approvals/{id}/reject` | Reject a request | Yes |

---

## SSH Connections

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/ssh-connections` | List SSH connections | Admin |
| POST | `/ssh-connections` | Create SSH connection. Body: name, hostname, port, username, auth_method | Admin |
| GET | `/ssh-connections/{id}` | Get SSH connection details | Admin |
| PUT | `/ssh-connections/{id}` | Update an SSH connection | Admin |
| DELETE | `/ssh-connections/{id}` | Delete an SSH connection | Admin |
| POST | `/ssh-connections/{id}/test` | Test SSH connectivity | Admin |
| POST | `/ssh-connections/{id}/execute` | Execute a command via SSH | Admin |

---

## Secrets Vault

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/secrets` | List secrets (metadata only, values are masked) | Admin |
| POST | `/secrets` | Create a secret. Body: name, value, category, expires_at | Admin |
| GET | `/secrets/{id}` | Get secret details (value requires explicit reveal) | Admin |
| PUT | `/secrets/{id}` | Update a secret | Admin |
| DELETE | `/secrets/{id}` | Delete a secret | Admin |
| POST | `/secrets/{id}/rotate` | Rotate a secret value | Admin |
| GET | `/secrets/expiring` | List secrets expiring within a given timeframe. Query: `days` | Admin |

---

## Code Reviews

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/code-reviews` | List code reviews. Query: `status`, `agent_id` | Yes |
| GET | `/code-reviews/{id}` | Get code review details with comments | Yes |
| POST | `/code-reviews/{id}/approve` | Approve a code review | Yes |
| POST | `/code-reviews/{id}/reject` | Reject a code review | Yes |
| POST | `/code-reviews/{id}/comment` | Add a comment to a code review | Yes |

---

## Marketplace

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/marketplace/templates` | List available templates. Query: `category`, `search` | Yes |
| GET | `/marketplace/templates/{id}` | Get template details | Yes |
| POST | `/marketplace/templates/{id}/install` | Install a template (creates agents/workflows from template) | Yes |

---

## Exports

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/exports/{format}` | Export platform data. Format: `json`, `csv`, `xlsx`. Query: `type` (tasks, agents, analytics) | Yes |

---

## WebSocket

### WS `/ws`

Real-time event stream. Requires JWT token as query parameter or in first message.

Send `{"type": "ping"}` for keepalive.

Subscribe to events:
```json
{"type": "subscribe", "event": "task.completed"}
```

Event types: `agent.status`, `task.created`, `task.updated`, `task.completed`, `task.failed`, `worker.online`, `worker.offline`, `message.new`, `notification`, `system.alert`

---

## Health

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Basic health check. Returns status, service name, version | No |
| GET | `/metrics` | Prometheus metrics endpoint | No |
