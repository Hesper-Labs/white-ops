# Getting Started

## What is White-Ops?

White-Ops is an enterprise AI workforce platform that deploys AI agents across multiple PCs to handle professional tasks. Each agent is powered by an LLM (Claude, GPT, Gemini, or Ollama) and has access to 83 tools across 14 categories -- from creating Excel reports and sending emails to managing cloud infrastructure and running CI/CD pipelines. A 37-page admin panel provides full control over agents, tasks, workflows, cost tracking, security, and more.

## How It Works

1. **Create an agent** -- Pick a role, choose an LLM provider, and enable the tools the agent needs
2. **Assign a task** -- Describe what you need done in plain language (or let the orchestrator auto-assign)
3. **LLM reasoning loop** -- The agent reasons through the task using LLM function calling, up to 50 iterations
4. **Tools execute** -- The agent calls tools (browser, Excel, email, database, shell, etc.) to get work done
5. **Results delivered** -- Output files, data, and status are posted back and visible in the admin panel

## 5-Minute Setup

### Step 1: Clone and Configure

```bash
git clone https://github.com/hesperus/white-ops.git
cd white-ops
cp .env.example .env
```

Edit `.env` and set the required variables:

```
# At least one LLM provider key
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Database
POSTGRES_PASSWORD=<choose a strong password>

# Admin account
ADMIN_EMAIL=admin@whiteops.local
ADMIN_PASSWORD=<choose a strong password>

# Security
SECRET_KEY=<random 64-char hex string>
ENCRYPTION_KEY=<Fernet key for secrets vault>

# Optional
REDIS_PASSWORD=<password>
MINIO_ACCESS_KEY=<key>
MINIO_SECRET_KEY=<secret>
```

### Step 2: Validate and Start

```bash
make check          # Pre-deployment validation
docker compose up -d
```

This starts all 10 services: server, worker, web, database, Redis, MinIO, mail, Celery worker, Celery beat, and nginx.

### Step 3: Open the Admin Panel

Open http://localhost:3000 in your browser.

Log in with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your `.env` file.

## First Steps

### Run the Setup Wizard

On first login, the Setup Wizard guides you through initial configuration: LLM provider keys, email settings, and security options.

### Create Your First Agent

1. Go to **Agents** and click **+ New Agent**
2. Name: "Research Assistant"
3. Role: Researcher
4. LLM: Anthropic (Claude)
5. Enable tools: browser, search, web_scraper, excel
6. Click **Create**

Or go to **Marketplace** and deploy a pre-configured agent preset with one click.

### Assign a Task

1. Go to **Tasks** and click **+ New Task**
2. Title: "Research competitor pricing"
3. Instructions: "Search the web for our top 3 competitors and create an Excel comparison of their pricing tiers"
4. Assign to: Research Assistant
5. Click **Create**

The agent will execute the task and post results back to the task detail page.

### View Results

Open the task to see the result summary, output files (downloadable), tool call log, and any errors encountered.

## Key Features to Explore

- **Agent Chat** -- Chat directly with agents in a conversational interface
- **Marketplace** -- Browse and deploy community agent presets with pre-configured tools
- **Schedules** -- Set up cron-based recurring tasks (daily reports, weekly summaries)
- **Knowledge Base** -- Upload documents that agents can reference during task execution
- **Cost Dashboard** -- Track LLM token costs per agent, per task, and per provider with budget alerts
- **Workflows** -- Build multi-step DAG workflows with conditional logic and parallel execution

## Adding More PCs

On each additional PC:

```bash
./scripts/add-worker.sh 192.168.1.100  # Replace with master server IP
```

Then approve the new worker in **DevOps > Workers** in the admin panel.

## Next Steps

- [Admin Panel Guide](admin-panel.md) -- Full tour of all 37 pages
- [Tool Development Guide](tools-guide.md) -- Browse all 83 tools or add custom ones
- [Architecture Overview](architecture.md) -- Understand the master-worker system
- [Contributing](contributing.md) -- Development setup and code standards
- [API Reference](api-reference.md) -- Integrate with external systems
- [Deployment Guide](deployment.md) -- Production deployment with Kubernetes
