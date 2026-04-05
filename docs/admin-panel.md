# Admin Panel Guide

The White-Ops admin panel is a 21-page web application for complete platform control.

## Navigation Structure

### Main
- **Dashboard** - Real-time platform overview with KPI cards, charts, and system health
- **Agents** - Create, configure, start/stop, and monitor AI agents
- **Tasks** - Assign tasks to agents, track progress, view results
- **Workflows** - Multi-step automation builder
- **Messages** - Monitor agent-to-agent communication
- **Files** - Browse files created by agents

### Intelligence
- **Collaboration** - Multi-agent collaboration sessions
- **Knowledge Base** - Shared knowledge for agents to reference
- **Analytics** - Performance metrics, success rates, agent comparison
- **Activity Feed** - Real-time event log of all platform actions

### Operations
- **Schedules** - Cron-based recurring task automation
- **Templates** - Reusable task templates for common operations
- **Agent Presets** - Pre-configured agent profiles for one-click deployment

### System
- **Workers** - Monitor connected PC nodes (CPU, RAM, disk)
- **Users** - User management with RBAC roles
- **Audit Log** - Complete history of all actions
- **Settings** - System configuration (LLM keys, email, security, storage)

## Page Details

### Dashboard
- 4 KPI cards: Active Agents, Tasks, Workers Online, Messages
- 3 metric cards: Success Rate, Avg Completion Time, Files Created
- Weekly Task Activity bar chart (Recharts)
- Task Distribution pie chart
- System Health panel (API, PostgreSQL, Redis, MinIO, Mail, WebSocket)

### Agents
- Table view with columns: Agent, Role, Status, LLM, Completed, Failed, Created, Actions
- Status indicators: green (idle), yellow (busy), red (error), gray (offline)
- Actions: Start, Stop, Delete
- **Agent Detail** page (click agent name):
  - **Overview tab**: Stats cards, agent info, description, system prompt
  - **Configuration tab**: Edit name, role, LLM, temperature, max tokens
  - **Tools tab**: Enable/disable 55 tools by category
  - **Logs tab**: Terminal-style execution log
  - **Performance tab**: Tasks/day, avg time, token usage, cost estimate
  - Clone Agent button

### Tasks
- Status filter tabs: All, Pending, Assigned, In Progress, Review, Completed, Failed
- Table with: Title, Status, Priority, Created, Actions
- **Task Detail** page (click task):
  - Info section: agent, dates, deadline, retry count
  - Result section (completed tasks)
  - Error section (failed tasks)
  - Output files with download
  - Tool call log
  - Comments section

### Workflow Builder
- Visual step editor
- Step types: Task, If/Else (condition), Parallel, Wait, Notify
- Each step: name, type, agent assignment, instructions
- Add/remove steps, Save, Run buttons

### Agent Presets
- 12 pre-configured profiles:
  - Financial Analyst, Research Specialist, Content Writer
  - Executive Assistant, Software Developer, HR Manager
  - Marketing Analyst, Legal Assistant, Data Scientist
  - Sales Representative, Project Manager, Customer Support
- Category filters: All, Finance, Tech, Operations, Marketing
- Each shows: name, role, description, recommended LLM, included tools
- One-click "Deploy Agent" button

### Scheduled Tasks
- Cron expression, agent assignment, active/paused status
- Last run, next run timestamps
- Pause/Resume, Delete actions

### Settings
- **System Health**: Live status of Database, Redis, Storage, Mail
- **LLM Configuration**: Provider, model, API keys (masked), temperature, max tokens
- **Email Settings**: SMTP host/port/user/password, from address
- **Security**: JWT expiry, worker approval, rate limiting, sandbox toggle
- **General**: Max agents per worker, task timeout, auto-assign, log level, maintenance mode
- **Notifications**: Task complete/failed, worker offline, webhook URL
- **Storage**: Max file size, allowed types, auto cleanup days
- Bulk "Save All" button

### Audit Log
- Filterable table with: Time, Action, Resource, Actor, Details
- Action types: LOGIN_SUCCESS, LOGIN_FAILED, AGENT_CREATED, TASK_ASSIGNED, TASK_COMPLETED, TASK_FAILED, WORKER_APPROVED, SETTINGS_UPDATED, FILE_UPLOADED, AGENT_STOPPED

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Open global search |
| `N` | New task (when not in input) |
| `Esc` | Close modal/search |

## Demo Mode

When the backend is not running, the admin panel automatically enters demo mode with mock data. This allows exploring all features without any backend setup.
