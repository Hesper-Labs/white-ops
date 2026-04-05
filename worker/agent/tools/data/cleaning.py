"""Data cleaning tool - clean and normalize datasets using pandas."""

import io
import json
from typing import Any

from agent.tools.base import BaseTool


class DataCleaningTool(BaseTool):
    name = "data_cleaning"
    description = (
        "Clean and normalize data: remove duplicates, fill missing values, "
        "normalize text, detect outliers, and standardize date formats. "
        "Accepts CSV or JSON data as input."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "remove_duplicates",
                    "fill_missing",
                    "normalize",
                    "detect_outliers",
                    "standardize_dates",
                ],
                "description": "Cleaning action to perform.",
            },
            "data": {
                "type": "string",
                "description": "Input data as CSV string or JSON array string.",
            },
            "file_path": {
                "type": "string",
                "description": "Path to CSV or JSON file (alternative to data).",
            },
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns to operate on. If empty, applies to all.",
            },
            "fill_value": {
                "description": "Value to use for filling missing data.",
            },
            "fill_method": {
                "type": "string",
                "enum": ["value", "mean", "median", "mode", "ffill", "bfill"],
                "description": "Method for filling missing values.",
            },
            "date_format": {
                "type": "string",
                "description": "Target date format (e.g., '%Y-%m-%d').",
            },
            "output_path": {
                "type": "string",
                "description": "Path to save cleaned data.",
            },
        },
        "required": ["action"],
    }

    def _load_dataframe(self, kwargs: dict):
        import pandas as pd

        if kwargs.get("file_path"):
            path = kwargs["file_path"]
            if path.endswith(".json"):
                return pd.read_json(path)
            return pd.read_csv(path)
        elif kwargs.get("data"):
            data_str = kwargs["data"]
            try:
                parsed = json.loads(data_str)
                if isinstance(parsed, list):
                    return pd.DataFrame(parsed)
            except (json.JSONDecodeError, ValueError):
                pass
            return pd.read_csv(io.StringIO(data_str))
        return None

    def _save_or_return(self, df, kwargs: dict) -> dict:
        output_path = kwargs.get("output_path")
        if output_path:
            if output_path.endswith(".json"):
                df.to_json(output_path, orient="records", force_ascii=False, indent=2)
            else:
                df.to_csv(output_path, index=False)
            return {"message": f"Saved to {output_path}", "rows": len(df), "columns": list(df.columns)}

        # Return preview
        preview = df.head(20).to_dict(orient="records")
        return {"rows": len(df), "columns": list(df.columns), "preview": preview}

    async def execute(self, **kwargs: Any) -> Any:
        import pandas as pd
        import numpy as np

        action = kwargs["action"]
        df = self._load_dataframe(kwargs)
        if df is None:
            return {"error": "Provide data (as string) or file_path."}

        columns = kwargs.get("columns")

        if action == "remove_duplicates":
            before = len(df)
            subset = columns if columns else None
            df = df.drop_duplicates(subset=subset)
            after = len(df)
            result = self._save_or_return(df, kwargs)
            result["duplicates_removed"] = before - after
            return result

        elif action == "fill_missing":
            method = kwargs.get("fill_method", "value")
            cols = columns if columns else df.columns.tolist()

            missing_before = int(df[cols].isna().sum().sum())

            if method == "value":
                fill_val = kwargs.get("fill_value", 0)
                df[cols] = df[cols].fillna(fill_val)
            elif method == "mean":
                numeric = df[cols].select_dtypes(include=[np.number]).columns
                df[numeric] = df[numeric].fillna(df[numeric].mean())
            elif method == "median":
                numeric = df[cols].select_dtypes(include=[np.number]).columns
                df[numeric] = df[numeric].fillna(df[numeric].median())
            elif method == "mode":
                for col in cols:
                    if not df[col].mode().empty:
                        df[col] = df[col].fillna(df[col].mode()[0])
            elif method == "ffill":
                df[cols] = df[cols].ffill()
            elif method == "bfill":
                df[cols] = df[cols].bfill()

            missing_after = int(df[cols].isna().sum().sum())
            result = self._save_or_return(df, kwargs)
            result["missing_filled"] = missing_before - missing_after
            return result

        elif action == "normalize":
            cols = columns if columns else df.select_dtypes(include=["object"]).columns.tolist()
            for col in cols:
                if df[col].dtype == "object":
                    df[col] = df[col].str.strip()
                    df[col] = df[col].str.lower()
                    # Remove extra whitespace
                    df[col] = df[col].str.replace(r"\s+", " ", regex=True)
            result = self._save_or_return(df, kwargs)
            result["normalized_columns"] = cols
            return result

        elif action == "detect_outliers":
            cols = columns if columns else df.select_dtypes(include=[np.number]).columns.tolist()
            outliers_info = {}
            for col in cols:
                if col not in df.columns:
                    continue
                series = df[col].dropna()
                if len(series) < 4:
                    continue
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                mask = (series < lower) | (series > upper)
                outlier_indices = series[mask].index.tolist()
                if outlier_indices:
                    outliers_info[col] = {
                        "count": len(outlier_indices),
                        "lower_bound": round(float(lower), 4),
                        "upper_bound": round(float(upper), 4),
                        "outlier_values": [round(float(v), 4) for v in series[mask].tolist()[:20]],
                    }
            return {"outliers": outliers_info, "total_rows": len(df)}

        elif action == "standardize_dates":
            target_fmt = kwargs.get("date_format", "%Y-%m-%d")
            cols = columns if columns else []
            if not cols:
                return {"error": "Specify columns containing dates."}

            converted = 0
            errors_list = []
            for col in cols:
                if col not in df.columns:
                    continue
                try:
                    df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")
                    null_count = int(df[col].isna().sum())
                    df[col] = df[col].dt.strftime(target_fmt)
                    converted += 1
                    if null_count:
                        errors_list.append(f"{col}: {null_count} unparseable values set to NaT")
                except Exception as e:
                    errors_list.append(f"{col}: {e}")

            result = self._save_or_return(df, kwargs)
            result["columns_converted"] = converted
            if errors_list:
                result["warnings"] = errors_list
            return result

        return {"error": f"Unknown action: {action}"}
