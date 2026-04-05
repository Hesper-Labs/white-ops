# API Reference

Base URL: `http://localhost:8000/api/v1`

All endpoints (except auth/login and health) require a JWT token in the `Authorization: Bearer <token>` header.

## Authentication

### POST /auth/login
Login and get JWT token.
```json
Request:  {"email": "admin@whiteops.local", "password": "..."}
Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

### GET /auth/me
Get current user info. Returns: `{id, email, full_name, role}`

## Agents

### GET /agents/
List all agents. Query params: `status_filter`, `role`

### POST /agents/
Create agent. Body: `{name, description, role, llm_provider, llm_model, system_prompt, enabled_tools, worker_id}`

### GET /agents/{id}
Get agent details.

### PATCH /agents/{id}
Update agent. Partial update supported.

### DELETE /agents/{id}
Delete agent.

### POST /agents/{id}/start
Activate agent (status -> idle).

### POST /agents/{id}/stop
Deactivate agent (status -> offline).

## Tasks

### GET /tasks/
List tasks. Query params: `status_filter`, `priority`, `agent_id`, `limit`, `offset`

### POST /tasks/
Create task. Body: `{title, description, instructions, priority, agent_id, deadline, required_tools}`

### GET /tasks/stats
Task statistics by status and priority.

### GET /tasks/{id}
Get task details including result.

### PATCH /tasks/{id}
Update task. Body: `{title, description, status, priority, agent_id}`

### POST /tasks/{id}/cancel
Cancel a running task.

## Workflows

### GET /workflows/
List workflows.

### POST /workflows/
Create workflow. Body: `{name, description, is_template, config}`

### GET /workflows/{id}
Get workflow with all steps.

### POST /workflows/{id}/steps
Add step. Body: `{name, step_type, order, config, agent_id, depends_on}`

### DELETE /workflows/{id}
Delete workflow.

## Messages

### GET /messages/
List messages. Query params: `agent_id`, `channel`, `limit`, `offset`

### POST /messages/send
Send message. Body: `{sender_agent_id, recipient_agent_id, channel, subject, body}`

### PATCH /messages/{id}/read
Mark message as read.

## Files

### GET /files/
List files. Query params: `task_id`, `limit`

### POST /files/upload
Upload file (multipart/form-data). Query param: `task_id`

### GET /files/{id}
Get file metadata.

### GET /files/{id}/download
Download file content.

### GET /files/{id}/url
Get presigned download URL (expires in 1 hour).

### DELETE /files/{id}
Delete file from storage and database.

## Workers

### POST /workers/register
Register worker node. Body: `{name, hostname, ip_address, max_agents, cpu_cores, memory_total_mb, os_info}`

### POST /workers/{id}/heartbeat
Send heartbeat. Body: `{cpu_usage_percent, memory_usage_percent, disk_usage_percent}`

### GET /workers/{id}/tasks
Get pending tasks for this worker's agents.

### GET /workers/overview
Fleet overview statistics.

## Admin

### GET /admin/users
List all users (admin only).

### POST /admin/users
Create user. Body: `{email, password, full_name, role}`

### GET /admin/workers
List all workers with metrics.

### PATCH /admin/workers/{id}/approve
Approve/reject worker. Body: `{is_approved, group}`

### GET /admin/audit
Audit log. Query params: `limit`, `offset`

## Settings

### GET /settings/
Get all settings grouped by category (admin only).

### PUT /settings/{category}/{key}
Update single setting. Body: `{value: "..."}`

### PUT /settings/bulk
Update multiple settings. Body: `{settings: {"category.key": "value", ...}}`

### GET /settings/health
System health check (database, Redis, MinIO, mail server).

## Analytics

### GET /analytics/overview
Platform analytics. Query param: `days` (default: 7)

### GET /analytics/agents
Per-agent performance metrics.

### GET /analytics/tasks/timeline
Task creation timeline for charts. Query param: `days`

### GET /analytics/workers/utilization
Live worker resource utilization.

## Knowledge Base

### GET /knowledge/
List entries. Query params: `category`, `search`, `limit`

### POST /knowledge/
Create entry. Body: `{title, content, category, tags, source}`

### GET /knowledge/{id}
Get full entry.

### DELETE /knowledge/{id}
Delete entry.

## Collaboration

### GET /collaboration/
List sessions. Query param: `status`

### POST /collaboration/
Create session. Body: `{name, description, participants: [agent_ids], initial_context}`

### GET /collaboration/{id}
Get session with messages.

### POST /collaboration/{id}/messages
Add message. Body: `{agent_id, message, message_type}`

### POST /collaboration/{id}/context
Update shared context. Body: `{key: value, ...}`

### POST /collaboration/{id}/close
Close collaboration session.

## WebSocket

### WS /ws
Real-time events. Send `{"type": "ping"}` for keepalive.

Subscribe to events:
```json
{"type": "subscribe", "event": "task.completed"}
```

Event types: `agent.status`, `task.created`, `task.updated`, `task.completed`, `task.failed`, `worker.online`, `worker.offline`, `message.new`, `notification`, `system.alert`

## Health

### GET /health
Returns: `{"status": "healthy", "service": "white-ops-server", "version": "0.1.0"}`

### GET /metrics
Prometheus metrics endpoint.
