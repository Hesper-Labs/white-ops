"""Database query tool - safe SQL queries via SQLite."""

import re
import sqlite3
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool

DEFAULT_DB = "/tmp/whiteops_database.db"


class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = (
        "Execute safe SQL queries on a SQLite database. "
        "Supports SELECT queries only, listing tables, and describing table schemas."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["query", "describe_table", "list_tables"],
                "description": "Action to perform.",
            },
            "sql": {
                "type": "string",
                "description": "SQL query to execute (SELECT only, for query action).",
            },
            "table_name": {
                "type": "string",
                "description": "Table name (for describe_table).",
            },
            "db_path": {
                "type": "string",
                "description": "Path to SQLite database. Defaults to temp DB.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows to return. Default 100.",
            },
        },
        "required": ["action"],
    }

    def _get_conn(self, db_path: str | None) -> sqlite3.Connection:
        path = db_path or DEFAULT_DB
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    def _is_safe_query(self, sql: str) -> bool:
        """Only allow SELECT statements."""
        normalized = sql.strip().upper()
        # Reject anything that isn't a SELECT
        if not normalized.startswith("SELECT"):
            return False
        # Reject dangerous keywords
        dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "REPLACE", "ATTACH", "DETACH"]
        # Check for these keywords at word boundaries (not in strings)
        for keyword in dangerous:
            if re.search(rf"\b{keyword}\b", normalized):
                return False
        return True

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        db_path = kwargs.get("db_path")

        if action == "query":
            sql = kwargs.get("sql", "").strip()
            if not sql:
                return {"error": "sql is required for query action."}
            if not self._is_safe_query(sql):
                return {"error": "Only SELECT queries are allowed for safety."}

            limit = kwargs.get("limit", 100)
            # Add LIMIT if not present
            if "LIMIT" not in sql.upper():
                sql = f"{sql} LIMIT {limit}"

            try:
                conn = self._get_conn(db_path)
                cursor = conn.execute(sql)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return {"columns": columns, "rows": rows, "row_count": len(rows)}
            except sqlite3.Error as e:
                return {"error": f"SQL error: {e}"}

        elif action == "list_tables":
            try:
                conn = self._get_conn(db_path)
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = [row["name"] for row in cursor.fetchall()]
                conn.close()
                return {"tables": tables, "count": len(tables)}
            except sqlite3.Error as e:
                return {"error": f"SQL error: {e}"}

        elif action == "describe_table":
            table_name = kwargs.get("table_name")
            if not table_name:
                return {"error": "table_name is required."}
            # Sanitize table name
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
                return {"error": "Invalid table name."}

            try:
                conn = self._get_conn(db_path)
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "cid": row["cid"],
                        "name": row["name"],
                        "type": row["type"],
                        "notnull": bool(row["notnull"]),
                        "default": row["dflt_value"],
                        "primary_key": bool(row["pk"]),
                    })
                conn.close()
                if not columns:
                    return {"error": f"Table '{table_name}' not found or has no columns."}
                return {"table": table_name, "columns": columns}
            except sqlite3.Error as e:
                return {"error": f"SQL error: {e}"}

        return {"error": f"Unknown action: {action}"}
