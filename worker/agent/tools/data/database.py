"""Database operations tool - safe PostgreSQL queries via asyncpg."""

import csv
import io
import json
import re
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
MAX_ROWS = 10000
QUERY_TIMEOUT = 30  # seconds

# Dangerous SQL keywords that are blocked by default
DANGEROUS_KEYWORDS = frozenset({
    "DROP", "DELETE", "TRUNCATE", "ALTER", "INSERT", "UPDATE",
    "CREATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
})


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class DatabaseTool(BaseTool):
    name = "database"
    description = (
        "Execute safe SQL queries on PostgreSQL databases. Supports SELECT queries, "
        "table listing, schema description, and CSV/JSON export. "
        "DROP, DELETE, TRUNCATE, and ALTER are blocked by default."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["query", "describe_table", "list_tables", "export_query"],
                "description": "Database action to perform.",
            },
            "connection_string": {
                "type": "string",
                "description": "PostgreSQL connection string (e.g. postgresql://user:pass@host:5432/db).",
            },
            "sql": {
                "type": "string",
                "description": "SQL query (for query and export_query actions).",
            },
            "params": {
                "type": "array",
                "items": {},
                "description": "Parameterized query values (positional $1, $2, ...).",
            },
            "table_name": {
                "type": "string",
                "description": "Table name (for describe_table action).",
            },
            "format": {
                "type": "string",
                "enum": ["csv", "json"],
                "description": "Export format (for export_query action). Default: json.",
            },
            "allow_mutations": {
                "type": "boolean",
                "description": "If true, allow non-SELECT queries. USE WITH EXTREME CAUTION.",
            },
        },
        "required": ["action", "connection_string"],
    }

    def _is_safe_query(self, sql: str, allow_mutations: bool = False) -> tuple[bool, str]:
        """Validate SQL query safety."""
        normalized = sql.strip().upper()

        if not normalized:
            return False, "Empty SQL query"

        if allow_mutations:
            return True, ""

        # Must start with SELECT, WITH (for CTEs), or EXPLAIN
        if not any(normalized.startswith(kw) for kw in ("SELECT", "WITH", "EXPLAIN")):
            return False, "Only SELECT, WITH (CTE), and EXPLAIN queries are allowed"

        # Check for dangerous keywords (outside of string literals)
        # Simple check: remove quoted strings first
        cleaned = re.sub(r"'[^']*'", "", normalized)
        cleaned = re.sub(r'"[^"]*"', "", cleaned)

        for keyword in DANGEROUS_KEYWORDS:
            if re.search(rf"\b{keyword}\b", cleaned):
                return False, f"Dangerous keyword '{keyword}' detected. Set allow_mutations=true to override."

        return True, ""

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        connection_string = kwargs.get("connection_string", "")
        logger.info("database_execute", action=action)

        if not connection_string:
            return json.dumps({"error": "connection_string is required"})

        try:
            import asyncpg
        except ImportError:
            return json.dumps({"error": "asyncpg is not installed. Run: pip install asyncpg"})

        try:
            if action == "query":
                return await self._query(kwargs, connection_string)
            elif action == "describe_table":
                return await self._describe_table(kwargs, connection_string)
            elif action == "list_tables":
                return await self._list_tables(connection_string)
            elif action == "export_query":
                return await self._export_query(kwargs, connection_string)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            logger.error("database_error", error=str(e), action=action)
            return json.dumps({"error": f"Database operation failed: {e}"})

    async def _get_connection(self, connection_string: str) -> Any:
        import asyncpg

        return await asyncpg.connect(
            connection_string,
            timeout=QUERY_TIMEOUT,
            statement_cache_size=0,
        )

    async def _query(self, kwargs: dict, conn_str: str) -> str:
        import asyncio

        sql = kwargs.get("sql", "").strip()
        params = kwargs.get("params", [])
        allow_mutations = kwargs.get("allow_mutations", False)

        if not sql:
            return json.dumps({"error": "sql is required for query action"})

        safe, reason = self._is_safe_query(sql, allow_mutations)
        if not safe:
            return json.dumps({"error": reason})

        conn = await self._get_connection(conn_str)
        try:
            # Apply row limit if not present
            upper_sql = sql.upper()
            if "LIMIT" not in upper_sql:
                sql = f"{sql} LIMIT {MAX_ROWS}"

            rows = await asyncio.wait_for(
                conn.fetch(sql, *params),
                timeout=QUERY_TIMEOUT,
            )

            columns = list(rows[0].keys()) if rows else []
            result_rows = [dict(row) for row in rows]

            # Serialize dates/datetimes/etc.
            for row in result_rows:
                for k, v in row.items():
                    if not isinstance(v, (str, int, float, bool, type(None))):
                        row[k] = str(v)

            logger.info("database_query_done", row_count=len(result_rows))
            return _truncate(json.dumps({
                "columns": columns,
                "rows": result_rows,
                "row_count": len(result_rows),
            }, default=str))
        except asyncio.TimeoutError:
            return json.dumps({"error": f"Query timed out after {QUERY_TIMEOUT}s"})
        finally:
            await conn.close()

    async def _describe_table(self, kwargs: dict, conn_str: str) -> str:
        table_name = kwargs.get("table_name", "")
        if not table_name:
            return json.dumps({"error": "table_name is required"})

        # Validate table name to prevent injection
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", table_name):
            return json.dumps({"error": "Invalid table name"})

        conn = await self._get_connection(conn_str)
        try:
            # Split schema.table if provided
            parts = table_name.split(".", 1)
            if len(parts) == 2:
                schema, table = parts
            else:
                schema, table = "public", parts[0]

            rows = await conn.fetch(
                """
                SELECT column_name, data_type, character_maximum_length,
                       is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2
                ORDER BY ordinal_position
                """,
                schema, table,
            )

            if not rows:
                return json.dumps({"error": f"Table '{table_name}' not found or has no columns"})

            columns = [
                {
                    "name": row["column_name"],
                    "type": row["data_type"],
                    "max_length": row["character_maximum_length"],
                    "nullable": row["is_nullable"] == "YES",
                    "default": row["column_default"],
                }
                for row in rows
            ]

            logger.info("database_describe_done", table=table_name, columns=len(columns))
            return json.dumps({"table": table_name, "columns": columns})
        finally:
            await conn.close()

    async def _list_tables(self, conn_str: str) -> str:
        conn = await self._get_connection(conn_str)
        try:
            rows = await conn.fetch(
                """
                SELECT table_schema, table_name, table_type
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                """
            )

            tables = [
                {
                    "schema": row["table_schema"],
                    "name": row["table_name"],
                    "type": row["table_type"],
                }
                for row in rows
            ]

            logger.info("database_list_tables_done", count=len(tables))
            return _truncate(json.dumps({"tables": tables, "count": len(tables)}))
        finally:
            await conn.close()

    async def _export_query(self, kwargs: dict, conn_str: str) -> str:
        import asyncio

        sql = kwargs.get("sql", "").strip()
        params = kwargs.get("params", [])
        fmt = kwargs.get("format", "json")

        if not sql:
            return json.dumps({"error": "sql is required for export_query"})

        safe, reason = self._is_safe_query(sql)
        if not safe:
            return json.dumps({"error": reason})

        conn = await self._get_connection(conn_str)
        try:
            upper_sql = sql.upper()
            if "LIMIT" not in upper_sql:
                sql = f"{sql} LIMIT {MAX_ROWS}"

            rows = await asyncio.wait_for(
                conn.fetch(sql, *params),
                timeout=QUERY_TIMEOUT,
            )

            if not rows:
                return json.dumps({"data": "", "row_count": 0, "format": fmt})

            columns = list(rows[0].keys())
            result_rows = [dict(row) for row in rows]

            # Serialize non-JSON types
            for row in result_rows:
                for k, v in row.items():
                    if not isinstance(v, (str, int, float, bool, type(None))):
                        row[k] = str(v)

            if fmt == "csv":
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerows(result_rows)
                data = output.getvalue()
            else:
                data = json.dumps(result_rows, default=str, indent=2)

            logger.info("database_export_done", format=fmt, row_count=len(result_rows))
            return _truncate(json.dumps({
                "data": data,
                "row_count": len(result_rows),
                "format": fmt,
                "columns": columns,
            }))
        except asyncio.TimeoutError:
            return json.dumps({"error": f"Query timed out after {QUERY_TIMEOUT}s"})
        finally:
            await conn.close()
