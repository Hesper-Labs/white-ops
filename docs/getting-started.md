# Getting Started

## What is White-Ops?

White-Ops is an open-source platform that deploys AI agents to handle white-collar office tasks. Each agent is powered by an LLM (Claude, GPT, Gemini, or Ollama) and has access to 55 tools for tasks like creating Excel reports, writing documents, browsing the web, sending emails, managing CRM, generating invoices, and more.

## How It Works

1. **You install** White-Ops on one or more PCs using Docker Compose
2. **You create agents** via the admin panel, each with a role and tool set
3. **You assign tasks** to agents (or let the system auto-assign)
4. **Agents execute** tasks using LLM reasoning + tool calling
5. **Agents communicate** with each other via internal email
6. **You monitor** everything from the admin panel

## 5-Minute Setup

### Step 1: Clone and Configure

```bash
git clone https://github.com/hesperus/white-ops.git
cd white-ops
cp .env.example .env
```

Edit `.env` and add at least one LLM API key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### Step 2: Start

```bash
./scripts/setup.sh
```

Or manually:
```bash
make build
make up
```

### Step 3: Login

Open http://localhost:3000 in your browser.

Default credentials (from `.env`):
- Email: `admin@whiteops.local`
- Password: (check `ADMIN_PASSWORD` in `.env`)

### Step 4: Create Your First Agent

1. Go to **Agents** page
2. Click **+ New Agent**
3. Name: "Research Assistant"
4. Role: Researcher
5. LLM: Anthropic (Claude)
6. Click **Create**

Or use **Agent Presets** to deploy a pre-configured agent with one click.

### Step 5: Assign a Task

1. Go to **Tasks** page
2. Click **+ New Task**
3. Title: "Research competitor pricing"
4. Instructions: "Search the web for our top 3 competitors and create an Excel comparison"
5. Assign to: Research Assistant
6. Click **Create**

The agent will execute the task using web search, browser, and Excel tools.

## Adding More PCs

On each additional PC:

```bash
./scripts/add-worker.sh 192.168.1.100  # Replace with master IP
```

Then approve the worker in **System > Workers**.

## Next Steps

- [Architecture Overview](architecture.md) - Understand how the system works
- [Tool Development Guide](tools-guide.md) - Add custom tools
- [API Reference](api-reference.md) - Integrate with external systems
- [Deployment Guide](deployment.md) - Production deployment
