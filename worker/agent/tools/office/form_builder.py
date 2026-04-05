"""Form builder tool - create HTML forms, manage fields, and collect responses."""

import json
import os
import time
import uuid
from typing import Any

from agent.tools.base import BaseTool

FORMS_FILE = "/tmp/whiteops_forms.json"


class FormBuilderTool(BaseTool):
    name = "form_builder"
    description = (
        "Build HTML forms dynamically. Create forms, add fields, "
        "generate HTML output, and list collected responses."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_form", "add_field", "generate_html", "list_responses"],
                "description": "The form builder action to perform",
            },
            "form_id": {
                "type": "string",
                "description": "Form ID (required for add_field, generate_html, list_responses)",
            },
            "title": {
                "type": "string",
                "description": "Form title (for create_form)",
            },
            "description": {
                "type": "string",
                "description": "Form description",
            },
            "field_name": {
                "type": "string",
                "description": "Field name/label (for add_field)",
            },
            "field_type": {
                "type": "string",
                "enum": ["text", "email", "number", "textarea", "select", "checkbox", "radio", "date", "file", "password", "tel", "url"],
                "description": "Field input type (for add_field)",
            },
            "required": {
                "type": "boolean",
                "description": "Whether the field is required (default true)",
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Options for select/radio fields",
            },
            "placeholder": {
                "type": "string",
                "description": "Placeholder text for the field",
            },
            "submit_url": {
                "type": "string",
                "description": "Form action URL for generate_html (default: #)",
            },
        },
        "required": ["action"],
    }

    def _load_forms(self) -> dict:
        if os.path.isfile(FORMS_FILE):
            try:
                with open(FORMS_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"forms": {}, "responses": {}}

    def _save_forms(self, data: dict) -> None:
        with open(FORMS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        if action == "create_form":
            return self._create_form(kwargs)
        elif action == "add_field":
            return self._add_field(kwargs)
        elif action == "generate_html":
            return self._generate_html(kwargs)
        elif action == "list_responses":
            return self._list_responses(kwargs)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})

    def _create_form(self, kwargs: dict) -> str:
        title = kwargs.get("title", "Untitled Form")
        description = kwargs.get("description", "")

        form_id = str(uuid.uuid4())[:8]
        data = self._load_forms()
        data["forms"][form_id] = {
            "id": form_id,
            "title": title,
            "description": description,
            "fields": [],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        data["responses"].setdefault(form_id, [])
        self._save_forms(data)

        return json.dumps({"success": True, "form_id": form_id, "title": title})

    def _add_field(self, kwargs: dict) -> str:
        form_id = kwargs.get("form_id")
        if not form_id:
            return json.dumps({"error": "form_id is required"})

        field_name = kwargs.get("field_name")
        field_type = kwargs.get("field_type", "text")
        if not field_name:
            return json.dumps({"error": "field_name is required"})

        data = self._load_forms()
        form = data["forms"].get(form_id)
        if not form:
            return json.dumps({"error": f"Form '{form_id}' not found"})

        field_id = field_name.lower().replace(" ", "_").replace("-", "_")
        field = {
            "id": field_id,
            "name": field_name,
            "type": field_type,
            "required": kwargs.get("required", True),
        }
        if kwargs.get("options"):
            field["options"] = kwargs["options"]
        if kwargs.get("placeholder"):
            field["placeholder"] = kwargs["placeholder"]

        form["fields"].append(field)
        self._save_forms(data)

        return json.dumps({
            "success": True,
            "form_id": form_id,
            "field_id": field_id,
            "total_fields": len(form["fields"]),
        })

    def _generate_html(self, kwargs: dict) -> str:
        form_id = kwargs.get("form_id")
        if not form_id:
            return json.dumps({"error": "form_id is required"})

        data = self._load_forms()
        form = data["forms"].get(form_id)
        if not form:
            return json.dumps({"error": f"Form '{form_id}' not found"})

        submit_url = kwargs.get("submit_url", "#")
        fields_html = []

        for field in form["fields"]:
            required = ' required' if field.get("required") else ''
            placeholder = f' placeholder="{field.get("placeholder", "")}"' if field.get("placeholder") else ''
            fid = field["id"]
            label = field["name"]
            ftype = field["type"]

            if ftype == "textarea":
                input_html = f'<textarea id="{fid}" name="{fid}"{required}{placeholder} rows="4"></textarea>'
            elif ftype == "select":
                options_html = '<option value="">-- Select --</option>'
                for opt in field.get("options", []):
                    options_html += f'\n            <option value="{opt}">{opt}</option>'
                input_html = f'<select id="{fid}" name="{fid}"{required}>{options_html}\n          </select>'
            elif ftype == "radio":
                radios = []
                for opt in field.get("options", []):
                    opt_id = f"{fid}_{opt.lower().replace(' ', '_')}"
                    radios.append(
                        f'<label><input type="radio" name="{fid}" value="{opt}"{required}> {opt}</label>'
                    )
                input_html = "\n            ".join(radios)
            elif ftype == "checkbox":
                input_html = f'<input type="checkbox" id="{fid}" name="{fid}" value="true">'
            else:
                input_html = f'<input type="{ftype}" id="{fid}" name="{fid}"{required}{placeholder}>'

            fields_html.append(
                f'      <div class="form-group">\n'
                f'        <label for="{fid}">{label}{"*" if field.get("required") else ""}</label>\n'
                f'        {input_html}\n'
                f'      </div>'
            )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{form["title"]}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
    .form-container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    h1 {{ margin-top: 0; color: #333; }}
    .description {{ color: #666; margin-bottom: 24px; }}
    .form-group {{ margin-bottom: 16px; }}
    label {{ display: block; margin-bottom: 4px; font-weight: 600; color: #444; }}
    input, textarea, select {{ width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box; }}
    input[type="checkbox"] {{ width: auto; }}
    button {{ background: #0066ff; color: white; border: none; padding: 12px 24px; border-radius: 4px; cursor: pointer; font-size: 16px; }}
    button:hover {{ background: #0052cc; }}
  </style>
</head>
<body>
  <div class="form-container">
    <h1>{form["title"]}</h1>
    {"<p class='description'>" + form["description"] + "</p>" if form["description"] else ""}
    <form action="{submit_url}" method="POST">
{chr(10).join(fields_html)}
      <div class="form-group">
        <button type="submit">Submit</button>
      </div>
    </form>
  </div>
</body>
</html>"""

        return json.dumps({
            "success": True,
            "form_id": form_id,
            "html": html,
            "field_count": len(form["fields"]),
        })

    def _list_responses(self, kwargs: dict) -> str:
        form_id = kwargs.get("form_id")
        if not form_id:
            return json.dumps({"error": "form_id is required"})

        data = self._load_forms()
        if form_id not in data["forms"]:
            return json.dumps({"error": f"Form '{form_id}' not found"})

        responses = data["responses"].get(form_id, [])
        return json.dumps({
            "form_id": form_id,
            "form_title": data["forms"][form_id]["title"],
            "responses": responses,
            "count": len(responses),
        })
