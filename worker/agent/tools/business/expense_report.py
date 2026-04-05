"""Expense report tool - track and report expenses."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_expenses.json"


class ExpenseReportTool(BaseTool):
    name = "expense_report"
    description = (
        "Track expenses, generate expense reports and PDF summaries. "
        "Supports categorization and summary analytics."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add_expense", "list_expenses", "generate_report", "summary_by_category"],
                "description": "Action to perform.",
            },
            "amount": {
                "type": "number",
                "description": "Expense amount.",
            },
            "category": {
                "type": "string",
                "description": "Expense category (e.g., travel, meals, office, supplies).",
            },
            "description": {
                "type": "string",
                "description": "Expense description.",
            },
            "date": {
                "type": "string",
                "description": "Expense date (YYYY-MM-DD). Defaults to today.",
            },
            "currency": {
                "type": "string",
                "description": "Currency code. Default: TRY.",
            },
            "employee_name": {
                "type": "string",
                "description": "Name of the employee submitting.",
            },
            "receipt_ref": {
                "type": "string",
                "description": "Receipt or invoice reference number.",
            },
            "start_date": {
                "type": "string",
                "description": "Start date filter (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "End date filter (YYYY-MM-DD).",
            },
            "output_path": {
                "type": "string",
                "description": "Output path for PDF report (for generate_report).",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> list[dict]:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save(self, expenses: list[dict]) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(expenses, indent=2, ensure_ascii=False))

    def _filter(self, expenses: list[dict], kwargs: dict) -> list[dict]:
        result = expenses
        if kwargs.get("start_date"):
            result = [e for e in result if e["date"] >= kwargs["start_date"]]
        if kwargs.get("end_date"):
            result = [e for e in result if e["date"] <= kwargs["end_date"]]
        if kwargs.get("category"):
            result = [e for e in result if e["category"] == kwargs["category"]]
        if kwargs.get("employee_name"):
            result = [e for e in result if e.get("employee_name") == kwargs["employee_name"]]
        return result

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        expenses = self._load()

        if action == "add_expense":
            amount = kwargs.get("amount")
            if amount is None:
                return {"error": "amount is required."}
            expense = {
                "id": uuid4().hex[:8],
                "amount": float(amount),
                "category": kwargs.get("category", "uncategorized"),
                "description": kwargs.get("description", ""),
                "date": kwargs.get("date", datetime.now().strftime("%Y-%m-%d")),
                "currency": kwargs.get("currency", "TRY"),
                "employee_name": kwargs.get("employee_name", ""),
                "receipt_ref": kwargs.get("receipt_ref", ""),
                "created_at": datetime.now().isoformat(),
            }
            expenses.append(expense)
            self._save(expenses)
            return {"message": "Expense added.", "expense": expense}

        elif action == "list_expenses":
            filtered = self._filter(expenses, kwargs)
            total = sum(e["amount"] for e in filtered)
            return {
                "expenses": filtered,
                "count": len(filtered),
                "total": round(total, 2),
            }

        elif action == "summary_by_category":
            filtered = self._filter(expenses, kwargs)
            categories: dict[str, dict] = {}
            for e in filtered:
                cat = e["category"]
                if cat not in categories:
                    categories[cat] = {"total": 0, "count": 0}
                categories[cat]["total"] = round(categories[cat]["total"] + e["amount"], 2)
                categories[cat]["count"] += 1

            grand_total = sum(c["total"] for c in categories.values())
            # Add percentage
            for cat_data in categories.values():
                cat_data["percentage"] = round((cat_data["total"] / grand_total) * 100, 1) if grand_total else 0

            return {
                "categories": categories,
                "grand_total": round(grand_total, 2),
                "total_expenses": len(filtered),
            }

        elif action == "generate_report":
            output_path = kwargs.get("output_path")
            if not output_path:
                return {"error": "output_path is required for generate_report."}

            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors

            filtered = self._filter(expenses, kwargs)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc = SimpleDocTemplate(output_path, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            # Title
            period = ""
            if kwargs.get("start_date") or kwargs.get("end_date"):
                period = f" ({kwargs.get('start_date', 'start')} - {kwargs.get('end_date', 'end')})"
            story.append(Paragraph(f"Expense Report{period}", styles["Title"]))
            if kwargs.get("employee_name"):
                story.append(Paragraph(f"Employee: {kwargs['employee_name']}", styles["Normal"]))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
            story.append(Spacer(1, 20))

            # Expense table
            table_data = [["#", "Date", "Category", "Description", "Amount"]]
            total = 0.0
            for i, exp in enumerate(filtered, 1):
                cur = exp.get("currency", "TRY")
                table_data.append([
                    str(i),
                    exp["date"],
                    exp["category"],
                    exp.get("description", "")[:40],
                    f"{cur} {exp['amount']:,.2f}",
                ])
                total += exp["amount"]

            table_data.append(["", "", "", "TOTAL:", f"{filtered[0].get('currency', 'TRY') if filtered else 'TRY'} {total:,.2f}"])

            t = Table(table_data, colWidths=[30, 80, 80, 180, 100])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
                ("FONTNAME", (-2, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]))
            story.append(t)
            story.append(Spacer(1, 20))

            # Category summary
            categories: dict[str, float] = {}
            for e in filtered:
                categories[e["category"]] = categories.get(e["category"], 0) + e["amount"]

            if categories:
                story.append(Paragraph("Summary by Category", styles["Heading3"]))
                cat_data = [["Category", "Total", "%"]]
                for cat, cat_total in sorted(categories.items(), key=lambda x: -x[1]):
                    pct = round((cat_total / total) * 100, 1) if total else 0
                    cat_data.append([cat, f"{cat_total:,.2f}", f"{pct}%"])

                ct = Table(cat_data, colWidths=[150, 100, 60])
                ct.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#34495e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (-2, 0), (-1, -1), "RIGHT"),
                ]))
                story.append(ct)

            try:
                doc.build(story)
                return {
                    "message": f"Expense report generated: {output_path}",
                    "total_expenses": len(filtered),
                    "grand_total": round(total, 2),
                    "categories": len(categories),
                }
            except Exception as e:
                return {"error": f"PDF generation failed: {e}"}

        return {"error": f"Unknown action: {action}"}
