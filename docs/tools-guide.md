# Tool Development Guide

## Overview

White-Ops has 83 tools across 14 categories. Tools are Python classes that extend `BaseTool` and are auto-discovered at startup by the `ToolRegistry`.

## Tool Categories

### office (6 tools)
- **excel** - Create, read, format spreadsheets, add formulas and charts
- **word** - Create and edit Word documents with headings, tables, images, lists
- **powerpoint** - Create presentations with title, content, image, and table slides
- **pdf** - Read, create, merge, split PDFs, extract metadata
- **forms** - Create and process form documents
- **notes** - Create and manage structured notes

### communication (7 tools)
- **email** - Send and receive emails (internal and external)
- **slack** - Post messages, read channels, manage threads
- **teams** - Microsoft Teams messaging and channel management
- **discord** - Discord bot messaging and channel operations
- **sms** - Send SMS messages via provider APIs
- **calendar** - Create events, check conflicts, list upcoming
- **telegram** - Telegram bot messaging

### research (6 tools)
- **browser** - Navigate, read, click, fill forms, screenshot, extract links/tables
- **search** - Web search queries
- **web_scraper** - Scrape pages for tables, links, text, images, metadata
- **rss_feed** - Read and parse RSS/Atom feeds
- **text_summarizer** - Summarize long text content
- **translator** - Translate text between languages

### data (6 tools)
- **data_analyzer** - Load, describe, filter, group, sort, correlate, query datasets
- **database** - Execute queries against PostgreSQL, MySQL, SQLite
- **data_cleaner** - Clean, deduplicate, normalize, and validate datasets
- **visualizer** - Generate bar, line, pie, scatter, histogram charts
- **converter** - Convert between data formats (JSON, CSV, XML, YAML)
- **csv_processor** - Read, write, transform, merge CSV files

### filesystem (3 tools)
- **file_manager** - Read, write, copy, move, delete, list, mkdir, zip, info
- **ocr** - Extract text from images and scanned documents
- **zip_handler** - Create, extract, list contents of zip archives

### technical (7 tools)
- **shell** - Execute shell commands (with security restrictions)
- **git_ops** - Git operations: clone, commit, push, pull, branch, merge, diff
- **docker_ops** - Docker container and image management
- **code_exec** - Execute Python code in a sandboxed environment
- **api_caller** - HTTP requests (GET, POST, PUT, PATCH, DELETE)
- **ssh_manager** - SSH into remote servers, execute commands, transfer files
- **claude_code_bridge** - Interface with Claude Code for advanced coding tasks

### devops (4 tools)
- **terraform** - Terraform plan, apply, destroy, state management
- **kubernetes** - Kubectl operations: pods, deployments, services, logs
- **ci_cd** - Trigger and monitor CI/CD pipelines
- **ansible** - Run Ansible playbooks and ad-hoc commands

### cloud (5 tools)
- **aws_ec2** - Manage EC2 instances: launch, stop, terminate, describe
- **aws_s3** - S3 bucket and object operations: upload, download, list, delete
- **aws_lambda** - Lambda function management: invoke, deploy, list, logs
- **azure** - Azure resource management
- **gcp** - Google Cloud Platform resource management

### business (5 tools)
- **crm** - Contact management, interaction logging, search, reporting
- **invoice** - Create professional PDF invoices
- **expense_reports** - Create and manage expense reports
- **project_tracker** - Track projects, milestones, and deliverables
- **time_tracker** - Start/stop timers, log hours, generate reports

### finance (3 tools)
- **bookkeeping** - Record transactions, generate ledgers and financial statements
- **currency** - Currency conversion with live exchange rates
- **tax_calculator** - Calculate taxes based on jurisdiction and income type

### hr (3 tools)
- **payroll** - Process payroll, generate pay stubs
- **employee_directory** - Manage employee records and org chart
- **leave_manager** - Track PTO, sick leave, approve/deny requests

### monitoring (3 tools)
- **health_checker** - Check service health and uptime
- **prometheus** - Query Prometheus metrics
- **log_analyzer** - Parse and analyze log files for patterns and anomalies

### security_tools (3 tools)
- **vulnerability_scanner** - Scan for known vulnerabilities in dependencies
- **secret_scanner** - Detect leaked secrets in code and files
- **port_scanner** - Scan network ports for open services

### integrations (6 tools)
- **github** - GitHub issues, PRs, repos, actions
- **jira** - Jira issue management, search, transitions
- **notion** - Notion page and database operations
- **pagerduty** - PagerDuty incident management
- **sentry** - Sentry error tracking and issue management
- **linear** - Linear issue tracking and project management

## Security Hardening

### Shell Tool
- Regex-based blocking of dangerous commands (rm -rf /, format, fdisk, etc.)
- Malformed command detection
- Chained command detection (prevents `safe_cmd; dangerous_cmd`)

### Code Execution Tool
- Runs in a separate file-based sandbox
- Resource limits (CPU time, memory, output size)
- Import blocking for dangerous modules (os, subprocess, sys, etc.)

### File Manager Tool
- Symlink protection (prevents following symlinks outside allowed paths)
- Path traversal prevention (blocks ../ sequences)
- Delete depth limits (prevents recursive deletion above a threshold)

### API Caller Tool
- SSRF prevention via DNS resolution checks
- Metadata endpoint blocking (blocks 169.254.169.254, cloud metadata URLs)
- Private IP range blocking

### Database Tool
- SQL injection prevention with parameterized queries
- Stacked query blocking (prevents multiple statements in one call)
- Comment stripping to prevent query manipulation

## Creating a New Tool

### 1. Choose a Category

Place your tool in the appropriate directory under `worker/agent/tools/`:

```
worker/agent/tools/
  office/           communication/    research/
  data/             filesystem/       technical/
  devops/           cloud/            business/
  finance/          hr/               monitoring/
  security_tools/   integrations/
```

### 2. Implement the Tool

```python
"""Description of what this tool does."""

from typing import Any
from agent.tools.base import BaseTool


class MyNewTool(BaseTool):
    name = "my_tool"

    description = (
        "What this tool does and when to use it. "
        "Be specific about capabilities."
    )

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "read", "update", "delete"],
                "description": "Action to perform",
            },
            "input_data": {
                "type": "string",
                "description": "The input data to process",
            },
        },
        "required": ["action"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool. Must be async."""
        action = kwargs["action"]

        if action == "create":
            return {"status": "success", "message": "Created successfully"}

        return {"status": "error", "message": f"Unknown action: {action}"}
```

### 3. Auto-Discovery

The tool is automatically discovered at startup. No registration needed. Ensure:
- The file is in a category directory under `worker/agent/tools/`
- The directory has an `__init__.py` file
- The class inherits from `BaseTool`
- The class has `name`, `description`, and `parameters` attributes

### 4. Add Security Checks

For tools that perform dangerous operations (file deletion, shell execution, network requests), add appropriate security checks. Flag operations that require human approval.

### 5. Testing

```python
# worker/tests/test_my_tool.py
import pytest
from agent.tools.my_category.my_tool import MyNewTool


@pytest.mark.asyncio
async def test_create():
    tool = MyNewTool()
    result = await tool.execute(action="create", input_data="test")
    assert result["status"] == "success"
```

For tools with security implications, add tests in `worker/tests/test_security_tools.py` covering bypass attempts.

## Best Practices

1. **Return structured JSON**: LLM reads the output, so use `{"status": "success/error", "message": "..."}` format
2. **Handle errors gracefully**: Return error messages, don't raise exceptions
3. **Limit output size**: Truncate large outputs to avoid token limits
4. **Use descriptive names**: The LLM chooses tools by name and description
5. **Document parameters well**: The LLM uses parameter descriptions to fill arguments
6. **Make actions atomic**: Each action should do one thing well
7. **Clean up resources**: Close files, connections, browser instances
8. **Add security checks**: Validate inputs, block dangerous operations, require approval for destructive actions
