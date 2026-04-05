# Tool Development Guide

## Overview

White-Ops tools are Python classes that extend `BaseTool`. The system auto-discovers all tools at startup using the registry.

## Creating a New Tool

### 1. Choose a Category

Place your tool in the appropriate directory:

```
worker/agent/tools/
  office/           # Excel, Word, PDF, PowerPoint
  communication/    # Email, calendar, messaging
  research/         # Browser, search, scraping
  data/             # Analysis, visualization, reporting
  filesystem/       # Files, images, backup
  business/         # CRM, invoicing, time tracking
  technical/        # Code, API, git
  finance/          # Bookkeeping, currency
  hr/               # Leave, directory, performance
  integrations/     # Slack, Jira, webhooks
```

### 2. Implement the Tool

```python
"""Description of what this tool does."""

from typing import Any
from agent.tools.base import BaseTool


class MyNewTool(BaseTool):
    # Required: unique identifier (used in LLM function calling)
    name = "my_tool"

    # Required: description shown to the LLM
    description = (
        "What this tool does and when to use it. "
        "Be specific about capabilities."
    )

    # Required: JSON Schema for parameters
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
            return self._create(kwargs)
        elif action == "read":
            return self._read(kwargs)

        return f"Unknown action: {action}"

    def _create(self, kwargs: dict) -> str:
        # Implementation
        return "Created successfully"

    def _read(self, kwargs: dict) -> str:
        # Implementation
        return "Read result"
```

### 3. Auto-Discovery

The tool is automatically discovered at startup. No registration needed. Just ensure:
- The file is in a category directory under `worker/agent/tools/`
- The directory has an `__init__.py` file
- The class inherits from `BaseTool`
- The class has `name`, `description`, and `parameters` attributes

### 4. Testing

```python
# worker/tests/test_my_tool.py
import pytest
from agent.tools.my_category.my_tool import MyNewTool


@pytest.mark.asyncio
async def test_create():
    tool = MyNewTool()
    result = await tool.execute(action="create", input_data="test")
    assert "Created" in result
```

## Best Practices

1. **Return strings or JSON**: LLM reads the output, so make it clear
2. **Handle errors gracefully**: Return error messages, don't raise exceptions
3. **Limit output size**: Truncate large outputs to avoid token limits
4. **Use descriptive names**: The LLM chooses tools by name + description
5. **Document parameters well**: The LLM uses parameter descriptions to fill args
6. **Make actions atomic**: Each action should do one thing well
7. **Clean up resources**: Close files, connections, browser instances

## Existing Tools Reference

| Tool | Category | Actions |
|------|----------|---------|
| excel | office | create, read, add_data, add_formula, add_chart, format_cells, add_sheet, auto_width |
| word | office | create, read, add_heading, add_paragraph, add_table, add_image, add_list, add_page_break |
| powerpoint | office | create, read, add_title_slide, add_content_slide, add_image_slide, add_table_slide |
| pdf | office | read, create, merge, split, metadata |
| browser | research | navigate, read, click, fill, screenshot, extract_links, extract_tables |
| web_search | research | search query |
| web_scraper | research | scrape with extract types (tables, links, text, images, metadata) |
| translator | research | translate text between languages |
| internal_email | communication | send, check_inbox, read_message |
| external_email | communication | send, check_inbox, read, search |
| calendar | communication | create, list, today, upcoming, delete, check_conflicts |
| data_analysis | data | load, describe, filter, groupby, sort, correlate, query |
| data_visualization | data | bar, line, pie, scatter, histogram charts |
| report_generator | data | generate PDF or DOCX reports with sections |
| file_manager | filesystem | read, write, copy, move, delete, list, mkdir, zip, info |
| image_processing | filesystem | resize, crop, rotate, convert, thumbnail, info, watermark |
| invoice | business | create professional PDF invoices |
| crm | business | add_contact, search, update, log_interaction, list, get |
| time_tracker | business | start, stop, log, report, list |
| code_exec | technical | execute Python or shell code (sandboxed) |
| api_caller | technical | HTTP requests (GET, POST, PUT, PATCH, DELETE) |
| webhook | integrations | send webhooks to external services |
