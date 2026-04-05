"""Data converter tool - convert between CSV, Excel, JSON, and XML formats."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool


class DataConverterTool(BaseTool):
    name = "data_converter"
    description = (
        "Convert data between formats: CSV to Excel, Excel to CSV, "
        "JSON to CSV, CSV to JSON, and XML to JSON."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["csv_to_excel", "excel_to_csv", "json_to_csv", "csv_to_json", "xml_to_json"],
                "description": "Conversion action to perform.",
            },
            "input_path": {
                "type": "string",
                "description": "Path to the input file.",
            },
            "output_path": {
                "type": "string",
                "description": "Path for the output file.",
            },
            "sheet_name": {
                "type": "string",
                "description": "Sheet name for Excel operations. Default: 'Sheet1'.",
            },
            "root_element": {
                "type": "string",
                "description": "Root element name for XML parsing.",
            },
        },
        "required": ["action", "input_path", "output_path"],
    }

    def _xml_to_dict(self, element: ET.Element) -> dict | str:
        """Recursively convert XML element to dict."""
        result: dict[str, Any] = {}
        if element.attrib:
            result["@attributes"] = dict(element.attrib)
        children = list(element)
        if not children:
            text = (element.text or "").strip()
            if result:
                if text:
                    result["#text"] = text
                return result
            return text

        for child in children:
            tag = child.tag
            child_data = self._xml_to_dict(child)
            if tag in result:
                if not isinstance(result[tag], list):
                    result[tag] = [result[tag]]
                result[tag].append(child_data)
            else:
                result[tag] = child_data
        return result

    async def execute(self, **kwargs: Any) -> Any:
        import pandas as pd

        action = kwargs["action"]
        input_path = kwargs["input_path"]
        output_path = kwargs["output_path"]

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            if action == "csv_to_excel":
                df = pd.read_csv(input_path)
                sheet = kwargs.get("sheet_name", "Sheet1")
                df.to_excel(output_path, index=False, sheet_name=sheet)
                return {
                    "message": f"Converted CSV to Excel: {output_path}",
                    "rows": len(df),
                    "columns": list(df.columns),
                }

            elif action == "excel_to_csv":
                sheet = kwargs.get("sheet_name")
                df = pd.read_excel(input_path, sheet_name=sheet or 0)
                df.to_csv(output_path, index=False)
                return {
                    "message": f"Converted Excel to CSV: {output_path}",
                    "rows": len(df),
                    "columns": list(df.columns),
                }

            elif action == "json_to_csv":
                with open(input_path) as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # Try to find the array within the dict
                    for v in data.values():
                        if isinstance(v, list):
                            data = v
                            break
                    else:
                        data = [data]
                df = pd.DataFrame(data)
                df.to_csv(output_path, index=False)
                return {
                    "message": f"Converted JSON to CSV: {output_path}",
                    "rows": len(df),
                    "columns": list(df.columns),
                }

            elif action == "csv_to_json":
                df = pd.read_csv(input_path)
                records = df.to_dict(orient="records")
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(records, f, indent=2, ensure_ascii=False, default=str)
                return {
                    "message": f"Converted CSV to JSON: {output_path}",
                    "rows": len(df),
                    "columns": list(df.columns),
                }

            elif action == "xml_to_json":
                tree = ET.parse(input_path)
                root = tree.getroot()

                root_tag = kwargs.get("root_element")
                if root_tag:
                    elements = root.findall(root_tag)
                    result = [self._xml_to_dict(el) for el in elements]
                else:
                    result = self._xml_to_dict(root)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)

                count = len(result) if isinstance(result, list) else 1
                return {
                    "message": f"Converted XML to JSON: {output_path}",
                    "records": count,
                }

            return {"error": f"Unknown action: {action}"}

        except FileNotFoundError:
            return {"error": f"Input file not found: {input_path}"}
        except Exception as e:
            return {"error": f"Conversion failed: {e}"}
