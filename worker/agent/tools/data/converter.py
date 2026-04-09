"""Format converter tool - convert between data formats using pandas."""

import json
import os
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

SUPPORTED_FORMATS = {"csv", "json", "xlsx", "xml", "parquet", "yaml"}

# Map extensions to read functions
FORMAT_EXTENSIONS = {
    ".csv": "csv",
    ".json": "json",
    ".xlsx": "xlsx",
    ".xls": "xlsx",
    ".xml": "xml",
    ".parquet": "parquet",
    ".pq": "parquet",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class DataConverterTool(BaseTool):
    name = "data_converter"
    description = (
        "Convert data files between formats: CSV, JSON, Excel (xlsx), XML, "
        "Parquet, and YAML. Also supports previewing file contents. Max 100MB."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["convert", "preview"],
                "description": "Action to perform.",
            },
            "input_path": {
                "type": "string",
                "description": "Path to the input file.",
            },
            "output_format": {
                "type": "string",
                "enum": ["csv", "json", "xlsx", "xml", "parquet", "yaml"],
                "description": "Target output format (for convert action).",
            },
            "output_path": {
                "type": "string",
                "description": "Custom output path. If omitted, uses input name with new extension.",
            },
            "rows": {
                "type": "integer",
                "description": "Number of rows to preview (for preview action). Default: 10.",
            },
            "sheet_name": {
                "type": "string",
                "description": "Sheet name for Excel files. Default: first sheet.",
            },
        },
        "required": ["action", "input_path"],
    }

    def _detect_format(self, path: str) -> str | None:
        ext = Path(path).suffix.lower()
        return FORMAT_EXTENSIONS.get(ext)

    def _check_file_size(self, path: str) -> tuple[bool, str]:
        size = os.path.getsize(path)
        if size > MAX_FILE_SIZE:
            return False, f"File too large: {size / 1024 / 1024:.1f}MB (max 100MB)"
        return True, ""

    def _read_dataframe(self, path: str, fmt: str, sheet_name: str | None = None) -> Any:
        import pandas as pd

        if fmt == "csv":
            return pd.read_csv(path)
        elif fmt == "json":
            return pd.read_json(path)
        elif fmt == "xlsx":
            return pd.read_excel(path, sheet_name=sheet_name or 0)
        elif fmt == "xml":
            return pd.read_xml(path)
        elif fmt == "parquet":
            return pd.read_parquet(path)
        elif fmt == "yaml":
            import yaml
            with open(path) as f:
                data = yaml.safe_load(f)
            if isinstance(data, list):
                return pd.DataFrame(data)
            elif isinstance(data, dict):
                # Try to find a list of records in the dict
                for v in data.values():
                    if isinstance(v, list):
                        return pd.DataFrame(v)
                return pd.DataFrame([data])
            raise ValueError("YAML must contain a list of records or a dict with a list value")
        else:
            raise ValueError(f"Unsupported input format: {fmt}")

    def _write_dataframe(self, df: Any, path: str, fmt: str) -> None:
        if fmt == "csv":
            df.to_csv(path, index=False)
        elif fmt == "json":
            df.to_json(path, orient="records", indent=2, force_ascii=False)
        elif fmt == "xlsx":
            df.to_excel(path, index=False)
        elif fmt == "xml":
            df.to_xml(path, index=False)
        elif fmt == "parquet":
            df.to_parquet(path, index=False)
        elif fmt == "yaml":
            import yaml
            records = df.to_dict(orient="records")
            # Convert non-serializable types
            for row in records:
                for k, v in row.items():
                    if not isinstance(v, (str, int, float, bool, type(None))):
                        row[k] = str(v)
            with open(path, "w") as f:
                yaml.dump(records, f, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported output format: {fmt}")

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        input_path = kwargs.get("input_path", "")
        logger.info("converter_execute", action=action, input_path=input_path)

        if not input_path:
            return json.dumps({"error": "input_path is required"})

        if not Path(input_path).exists():
            return json.dumps({"error": f"Input file not found: {input_path}"})

        ok, err = self._check_file_size(input_path)
        if not ok:
            return json.dumps({"error": err})

        input_format = self._detect_format(input_path)
        if not input_format:
            return json.dumps({
                "error": f"Cannot detect format for '{Path(input_path).suffix}'. "
                         f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}",
            })

        try:
            if action == "convert":
                return await self._convert(kwargs, input_path, input_format)
            elif action == "preview":
                return await self._preview(kwargs, input_path, input_format)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ImportError as e:
            return json.dumps({"error": f"Missing dependency: {e}"})
        except Exception as e:
            logger.error("converter_error", error=str(e))
            return json.dumps({"error": f"Conversion failed: {e}"})

    async def _convert(self, kwargs: dict, input_path: str, input_format: str) -> str:
        output_format = kwargs.get("output_format")
        if not output_format:
            return json.dumps({"error": "output_format is required for convert action"})

        if output_format not in SUPPORTED_FORMATS:
            return json.dumps({"error": f"Unsupported format: {output_format}"})

        sheet_name = kwargs.get("sheet_name")
        df = self._read_dataframe(input_path, input_format, sheet_name)

        # Determine output path
        output_path = kwargs.get("output_path")
        if not output_path:
            stem = Path(input_path).stem
            parent = Path(input_path).parent
            ext = "yml" if output_format == "yaml" else output_format
            output_path = str(parent / f"{stem}.{ext}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self._write_dataframe(df, output_path, output_format)

        logger.info(
            "converter_done",
            input_format=input_format,
            output_format=output_format,
            rows=len(df),
        )
        return json.dumps({
            "success": True,
            "input_path": input_path,
            "output_path": output_path,
            "input_format": input_format,
            "output_format": output_format,
            "rows": len(df),
            "columns": list(df.columns),
        })

    async def _preview(self, kwargs: dict, input_path: str, input_format: str) -> str:
        rows = kwargs.get("rows", 10)
        sheet_name = kwargs.get("sheet_name")

        df = self._read_dataframe(input_path, input_format, sheet_name)

        preview_df = df.head(rows)
        records = preview_df.to_dict(orient="records")

        # Serialize non-JSON types
        for row in records:
            for k, v in row.items():
                if not isinstance(v, (str, int, float, bool, type(None))):
                    row[k] = str(v)

        logger.info("converter_preview", input_path=input_path, rows=len(records))
        return _truncate(json.dumps({
            "file": input_path,
            "format": input_format,
            "total_rows": len(df),
            "preview_rows": len(records),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "data": records,
        }, default=str))
