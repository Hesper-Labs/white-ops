"""Data analysis tool - analyze data using pandas."""

import json
from typing import Any

import pandas as pd

from agent.tools.base import BaseTool


class DataAnalysisTool(BaseTool):
    name = "data_analysis"
    description = (
        "Analyze data using pandas. "
        "Supports: loading CSV/Excel, describe, filter, group by, "
        "aggregate, sort, pivot, and correlation analysis."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["load", "describe", "filter", "groupby", "sort", "correlate", "query"],
            },
            "filepath": {"type": "string", "description": "Path to CSV or Excel file"},
            "column": {"type": "string"},
            "columns": {"type": "array", "items": {"type": "string"}},
            "condition": {"type": "string", "description": "pandas query string"},
            "agg_func": {"type": "string", "enum": ["sum", "mean", "count", "min", "max"]},
            "ascending": {"type": "boolean"},
            "limit": {"type": "integer"},
        },
        "required": ["action"],
    }

    def __init__(self) -> None:
        super().__init__()
        self._df: pd.DataFrame | None = None

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        if action == "load":
            filepath = kwargs["filepath"]
            if filepath.endswith(".csv"):
                self._df = pd.read_csv(filepath)
            else:
                self._df = pd.read_excel(filepath)
            return json.dumps({
                "rows": len(self._df),
                "columns": list(self._df.columns),
                "dtypes": {k: str(v) for k, v in self._df.dtypes.items()},
                "head": self._df.head().to_dict(orient="records"),
            })

        if self._df is None:
            return "Error: No data loaded. Use 'load' action first."

        if action == "describe":
            return self._df.describe().to_json()

        elif action == "filter":
            condition = kwargs.get("condition", "")
            filtered = self._df.query(condition)
            limit = kwargs.get("limit", 20)
            return json.dumps({
                "rows": len(filtered),
                "data": filtered.head(limit).to_dict(orient="records"),
            })

        elif action == "groupby":
            column = kwargs.get("column", "")
            agg_func = kwargs.get("agg_func", "count")
            result = self._df.groupby(column).agg(agg_func)
            return result.to_json()

        elif action == "sort":
            column = kwargs.get("column", "")
            ascending = kwargs.get("ascending", True)
            limit = kwargs.get("limit", 20)
            sorted_df = self._df.sort_values(column, ascending=ascending).head(limit)
            return sorted_df.to_json(orient="records")

        elif action == "correlate":
            numeric_df = self._df.select_dtypes(include="number")
            return numeric_df.corr().to_json()

        elif action == "query":
            condition = kwargs.get("condition", "")
            result = self._df.query(condition)
            return json.dumps({
                "rows": len(result),
                "data": result.head(50).to_dict(orient="records"),
            })

        return f"Unknown action: {action}"
