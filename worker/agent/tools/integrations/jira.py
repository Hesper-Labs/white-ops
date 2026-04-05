"""Jira integration tool - manage issues, comments, and searches."""

import json
import os
from typing import Any

import httpx

from agent.tools.base import BaseTool


class JiraTool(BaseTool):
    name = "jira"
    description = (
        "Interact with Jira for issue tracking. Create, list, update, "
        "and search issues, and add comments."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_issue", "list_issues", "update_issue", "add_comment", "search"],
                "description": "The Jira action to perform",
            },
            "project_key": {
                "type": "string",
                "description": "Jira project key (e.g., 'PROJ')",
            },
            "issue_key": {
                "type": "string",
                "description": "Issue key (e.g., 'PROJ-123') for update/comment actions",
            },
            "summary": {
                "type": "string",
                "description": "Issue summary/title",
            },
            "description": {
                "type": "string",
                "description": "Issue description or comment body",
            },
            "issue_type": {
                "type": "string",
                "enum": ["Task", "Bug", "Story", "Epic", "Sub-task"],
                "description": "Type of issue (default: Task)",
            },
            "status": {
                "type": "string",
                "description": "Status to transition to (e.g., 'In Progress', 'Done')",
            },
            "assignee": {
                "type": "string",
                "description": "Assignee account ID or email",
            },
            "priority": {
                "type": "string",
                "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                "description": "Issue priority",
            },
            "jql": {
                "type": "string",
                "description": "JQL query string for search action",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return (default 20)",
            },
        },
        "required": ["action"],
    }

    def _get_config(self) -> tuple[str, str, str]:
        base_url = os.environ.get("JIRA_BASE_URL", "")
        email = os.environ.get("JIRA_EMAIL", "")
        api_token = os.environ.get("JIRA_API_TOKEN", "")
        if not all([base_url, email, api_token]):
            raise ValueError(
                "JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN environment variables are required"
            )
        return base_url.rstrip("/"), email, api_token

    def _client(self, base_url: str, email: str, api_token: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=f"{base_url}/rest/api/3",
            auth=(email, api_token),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=20,
        )

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            base_url, email, api_token = self._get_config()
        except ValueError as e:
            return json.dumps({"error": str(e)})

        try:
            async with self._client(base_url, email, api_token) as client:
                if action == "create_issue":
                    return await self._create_issue(client, kwargs)
                elif action == "list_issues":
                    return await self._list_issues(client, kwargs)
                elif action == "update_issue":
                    return await self._update_issue(client, kwargs)
                elif action == "add_comment":
                    return await self._add_comment(client, kwargs)
                elif action == "search":
                    return await self._search(client, kwargs)
                else:
                    return json.dumps({"error": f"Unknown action: {action}"})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"Jira API request failed: {e}"})

    async def _create_issue(self, client: httpx.AsyncClient, kwargs: dict) -> str:
        project_key = kwargs.get("project_key")
        summary = kwargs.get("summary")
        if not project_key or not summary:
            return json.dumps({"error": "project_key and summary are required"})

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": kwargs.get("issue_type", "Task")},
        }

        if kwargs.get("description"):
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": kwargs["description"]}],
                    }
                ],
            }
        if kwargs.get("assignee"):
            fields["assignee"] = {"accountId": kwargs["assignee"]}
        if kwargs.get("priority"):
            fields["priority"] = {"name": kwargs["priority"]}

        resp = await client.post("/issue", json={"fields": fields})
        if resp.status_code in (200, 201):
            data = resp.json()
            return json.dumps({
                "success": True,
                "key": data.get("key"),
                "id": data.get("id"),
                "self": data.get("self"),
            })
        return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

    async def _list_issues(self, client: httpx.AsyncClient, kwargs: dict) -> str:
        project_key = kwargs.get("project_key")
        if not project_key:
            return json.dumps({"error": "project_key is required"})

        max_results = kwargs.get("max_results", 20)
        jql = f"project = {project_key} ORDER BY updated DESC"

        resp = await client.get("/search", params={"jql": jql, "maxResults": max_results})
        if resp.status_code != 200:
            return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

        data = resp.json()
        issues = [
            {
                "key": issue["key"],
                "summary": issue["fields"]["summary"],
                "status": issue["fields"]["status"]["name"],
                "assignee": (issue["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
                "priority": (issue["fields"].get("priority") or {}).get("name", "None"),
                "updated": issue["fields"].get("updated", ""),
            }
            for issue in data.get("issues", [])
        ]
        return json.dumps({"issues": issues, "total": data.get("total", 0)})

    async def _update_issue(self, client: httpx.AsyncClient, kwargs: dict) -> str:
        issue_key = kwargs.get("issue_key")
        if not issue_key:
            return json.dumps({"error": "issue_key is required"})

        fields: dict[str, Any] = {}
        if kwargs.get("summary"):
            fields["summary"] = kwargs["summary"]
        if kwargs.get("description"):
            fields["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": kwargs["description"]}],
                    }
                ],
            }
        if kwargs.get("assignee"):
            fields["assignee"] = {"accountId": kwargs["assignee"]}
        if kwargs.get("priority"):
            fields["priority"] = {"name": kwargs["priority"]}

        if fields:
            resp = await client.put(f"/issue/{issue_key}", json={"fields": fields})
            if resp.status_code != 204:
                return json.dumps({"error": f"Update failed: {resp.status_code}", "body": resp.text[:500]})

        # Handle status transition separately
        if kwargs.get("status"):
            transitions_resp = await client.get(f"/issue/{issue_key}/transitions")
            if transitions_resp.status_code == 200:
                transitions = transitions_resp.json().get("transitions", [])
                target = kwargs["status"].lower()
                transition = next(
                    (t for t in transitions if t["name"].lower() == target), None
                )
                if transition:
                    await client.post(
                        f"/issue/{issue_key}/transitions",
                        json={"transition": {"id": transition["id"]}},
                    )
                else:
                    available = [t["name"] for t in transitions]
                    return json.dumps({
                        "warning": f"Status '{kwargs['status']}' not available",
                        "available_transitions": available,
                        "fields_updated": bool(fields),
                    })

        return json.dumps({"success": True, "issue_key": issue_key})

    async def _add_comment(self, client: httpx.AsyncClient, kwargs: dict) -> str:
        issue_key = kwargs.get("issue_key")
        body = kwargs.get("description")
        if not issue_key or not body:
            return json.dumps({"error": "issue_key and description (comment body) are required"})

        comment_body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body}],
                    }
                ],
            }
        }

        resp = await client.post(f"/issue/{issue_key}/comment", json=comment_body)
        if resp.status_code in (200, 201):
            data = resp.json()
            return json.dumps({
                "success": True,
                "comment_id": data.get("id"),
                "issue_key": issue_key,
            })
        return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

    async def _search(self, client: httpx.AsyncClient, kwargs: dict) -> str:
        jql = kwargs.get("jql")
        if not jql:
            return json.dumps({"error": "jql is required for search"})

        max_results = kwargs.get("max_results", 20)
        resp = await client.get("/search", params={"jql": jql, "maxResults": max_results})
        if resp.status_code != 200:
            return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

        data = resp.json()
        issues = [
            {
                "key": issue["key"],
                "summary": issue["fields"]["summary"],
                "status": issue["fields"]["status"]["name"],
                "assignee": (issue["fields"].get("assignee") or {}).get("displayName", "Unassigned"),
                "issue_type": issue["fields"]["issuetype"]["name"],
            }
            for issue in data.get("issues", [])
        ]
        return json.dumps({"issues": issues, "total": data.get("total", 0)})
