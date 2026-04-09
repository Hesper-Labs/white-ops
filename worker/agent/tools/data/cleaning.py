"""Data cleaning tool - clean and normalize datasets using pandas."""

import io
import json
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class DataCleaningTool(BaseTool):
    name = "data_cleaning"
    description = (
        "Clean and normalize datasets: remove duplicates, trim whitespace, normalize case, "
        "fill null values, remove empty rows, deduplicate by columns, fill missing values "
        "with various strategies, and detect outliers using IQR or Z-score methods. "
        "Supports CSV and JSON files."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["clean", "deduplicate", "fill_missing", "detect_outliers"],
                "description": "Cleaning action to perform.",
            },
            "file_path": {
                "type": "string",
                "description": "Path to CSV or JSON data file.",
            },
            "operations": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "remove_duplicates",
                        "trim_whitespace",
                        "normalize_case",
                        "fill_nulls",
                        "remove_empty_rows",
                    ],
                },
                "description": "List of cleaning operations to apply (for clean action).",
            },
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns to operate on (for deduplicate).",
            },
            "strategy": {
                "type": "string",
                "enum": ["mean", "median", "mode", "drop", "value"],
                "description": "Strategy for fill_missing.",
            },
            "column": {
                "type": "string",
                "description": "Target column (for fill_missing with specific column, detect_outliers).",
            },
            "value": {
                "description": "Fill value when strategy is 'value'.",
            },
            "method": {
                "type": "string",
                "enum": ["iqr", "zscore"],
                "description": "Outlier detection method (default: iqr).",
            },
            "output_path": {
                "type": "string",
                "description": "Path to save cleaned output file.",
            },
        },
        "required": ["action", "file_path"],
    }

    def _load_dataframe(self, file_path: str):
        """Load data from CSV or JSON file into a pandas DataFrame."""
        import pandas as pd

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".json":
            return pd.read_json(file_path)
        elif path.suffix.lower() in (".csv", ".tsv"):
            sep = "\t" if path.suffix.lower() == ".tsv" else ","
            return pd.read_csv(file_path, sep=sep)
        else:
            # Try CSV as default
            return pd.read_csv(file_path)

    def _save_result(self, df, file_path: str, output_path: str | None) -> dict:
        """Save DataFrame and return summary."""
        dest = output_path or file_path
        path = Path(dest)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.suffix.lower() == ".json":
            df.to_json(dest, orient="records", force_ascii=False, indent=2)
        else:
            df.to_csv(dest, index=False)

        preview = df.head(20).to_dict(orient="records")
        return {
            "output_file": dest,
            "rows": len(df),
            "columns": list(df.columns),
            "preview": preview,
        }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        file_path = kwargs.get("file_path", "")
        logger.info("data_cleaning_execute", action=action, file=file_path)

        if not file_path:
            return _truncate(json.dumps({"error": "'file_path' is required"}))

        try:
            import pandas as pd
            import numpy as np
        except ImportError as e:
            return _truncate(json.dumps({"error": f"Required library not available: {e}"}))

        try:
            df = self._load_dataframe(file_path)
        except FileNotFoundError as e:
            return _truncate(json.dumps({"error": str(e)}))
        except Exception as e:
            return _truncate(json.dumps({"error": f"Failed to load file: {e}"}))

        output_path = kwargs.get("output_path")

        try:
            if action == "clean":
                return await self._clean(df, kwargs, file_path, output_path)
            elif action == "deduplicate":
                return await self._deduplicate(df, kwargs, file_path, output_path)
            elif action == "fill_missing":
                return await self._fill_missing(df, kwargs, file_path, output_path, pd, np)
            elif action == "detect_outliers":
                return await self._detect_outliers(df, kwargs, np)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("data_cleaning_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Cleaning operation failed: {e}"}))

    async def _clean(self, df, kwargs: dict, file_path: str, output_path: str | None) -> str:
        operations = kwargs.get("operations", [])
        if not operations:
            return _truncate(json.dumps({"error": "'operations' list is required for clean action"}))

        original_rows = len(df)
        applied = []

        for op in operations:
            if op == "remove_duplicates":
                before = len(df)
                df = df.drop_duplicates()
                applied.append({"operation": op, "rows_removed": before - len(df)})

            elif op == "trim_whitespace":
                str_cols = df.select_dtypes(include=["object"]).columns
                for col in str_cols:
                    df[col] = df[col].str.strip()
                applied.append({"operation": op, "columns_processed": len(str_cols)})

            elif op == "normalize_case":
                str_cols = df.select_dtypes(include=["object"]).columns
                for col in str_cols:
                    df[col] = df[col].str.lower()
                applied.append({"operation": op, "columns_processed": len(str_cols)})

            elif op == "fill_nulls":
                missing_before = int(df.isna().sum().sum())
                # Fill numeric with 0, string with empty string
                for col in df.columns:
                    if df[col].dtype in ("float64", "int64"):
                        df[col] = df[col].fillna(0)
                    else:
                        df[col] = df[col].fillna("")
                missing_after = int(df.isna().sum().sum())
                applied.append({"operation": op, "values_filled": missing_before - missing_after})

            elif op == "remove_empty_rows":
                before = len(df)
                df = df.dropna(how="all")
                applied.append({"operation": op, "rows_removed": before - len(df)})

        result = self._save_result(df, file_path, output_path)
        result["operations_applied"] = applied
        result["original_rows"] = original_rows
        logger.info("data_cleaning_clean", operations=len(applied), rows_before=original_rows, rows_after=len(df))
        return _truncate(json.dumps(result))

    async def _deduplicate(self, df, kwargs: dict, file_path: str, output_path: str | None) -> str:
        columns = kwargs.get("columns", [])

        before = len(df)
        subset = columns if columns else None
        df = df.drop_duplicates(subset=subset)
        after = len(df)

        result = self._save_result(df, file_path, output_path)
        result["duplicates_removed"] = before - after
        result["original_rows"] = before
        logger.info("data_cleaning_deduplicate", removed=before - after)
        return _truncate(json.dumps(result))

    async def _fill_missing(self, df, kwargs: dict, file_path: str, output_path: str | None, pd, np) -> str:
        strategy = kwargs.get("strategy", "mean")
        column = kwargs.get("column")
        fill_value = kwargs.get("value")

        cols = [column] if column else df.columns.tolist()
        missing_before = int(df[cols].isna().sum().sum())

        if strategy == "mean":
            numeric = df[cols].select_dtypes(include=[np.number]).columns
            df[numeric] = df[numeric].fillna(df[numeric].mean())

        elif strategy == "median":
            numeric = df[cols].select_dtypes(include=[np.number]).columns
            df[numeric] = df[numeric].fillna(df[numeric].median())

        elif strategy == "mode":
            for col in cols:
                if col in df.columns and not df[col].mode().empty:
                    df[col] = df[col].fillna(df[col].mode()[0])

        elif strategy == "drop":
            df = df.dropna(subset=cols if column else None)

        elif strategy == "value":
            if fill_value is None:
                return _truncate(json.dumps({"error": "'value' is required when strategy is 'value'"}))
            df[cols] = df[cols].fillna(fill_value)

        missing_after = int(df[cols].isna().sum().sum()) if strategy != "drop" else 0

        result = self._save_result(df, file_path, output_path)
        result["strategy"] = strategy
        result["missing_before"] = missing_before
        result["missing_after"] = missing_after
        result["values_handled"] = missing_before - missing_after
        logger.info("data_cleaning_fill_missing", strategy=strategy, handled=missing_before - missing_after)
        return _truncate(json.dumps(result))

    async def _detect_outliers(self, df, kwargs: dict, np) -> str:
        column = kwargs.get("column", "")
        method = kwargs.get("method", "iqr")

        if not column:
            return _truncate(json.dumps({"error": "'column' is required for detect_outliers"}))

        if column not in df.columns:
            return _truncate(json.dumps({"error": f"Column '{column}' not found in data"}))

        series = df[column].dropna()
        if len(series) < 4:
            return _truncate(json.dumps({"error": "Not enough data points for outlier detection (minimum 4)"}))

        if method == "iqr":
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            mask = (series < lower_bound) | (series > upper_bound)

        elif method == "zscore":
            mean = float(series.mean())
            std = float(series.std())
            if std == 0:
                return _truncate(json.dumps({"error": "Standard deviation is 0, cannot compute z-scores"}))
            z_scores = (series - mean) / std
            mask = z_scores.abs() > 3
            lower_bound = mean - 3 * std
            upper_bound = mean + 3 * std

        else:
            return _truncate(json.dumps({"error": f"Unknown method: {method}"}))

        outlier_indices = series[mask].index.tolist()
        outlier_values = [round(float(v), 4) for v in series[mask].tolist()[:50]]

        result = {
            "column": column,
            "method": method,
            "total_rows": len(series),
            "outlier_count": len(outlier_indices),
            "lower_bound": round(lower_bound, 4),
            "upper_bound": round(upper_bound, 4),
            "outlier_values": outlier_values,
            "outlier_indices": outlier_indices[:50],
            "outlier_percentage": round(len(outlier_indices) / len(series) * 100, 2),
        }

        logger.info("data_cleaning_outliers", column=column, method=method, count=len(outlier_indices))
        return _truncate(json.dumps(result))
