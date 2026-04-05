"""Payroll tool - calculate Turkish payroll with tax and SGK deductions."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_payroll.json"

# SGK rates (2024)
SGK_EMPLOYEE_RATE = 0.14  # 14%
SGK_UNEMPLOYMENT_EMPLOYEE = 0.01  # 1%
SGK_EMPLOYER_RATE = 0.205  # 20.5%
SGK_UNEMPLOYMENT_EMPLOYER = 0.02  # 2%
STAMP_TAX_RATE = 0.00759  # Damga vergisi

# Income tax brackets
GELIR_VERGISI_DILIMLERI = [
    (110_000, 0.15),
    (230_000, 0.20),
    (580_000, 0.27),
    (3_000_000, 0.35),
    (float("inf"), 0.40),
]


class PayrollTool(BaseTool):
    name = "payroll"
    description = (
        "Calculate employee salaries with Turkish tax and SGK deductions. "
        "Generate payslips and list payroll records. Handles gelir vergisi, "
        "SGK primi, issizlik sigortasi, and damga vergisi."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["calculate_salary", "generate_payslip", "list_payroll"],
                "description": "Action to perform.",
            },
            "employee_id": {
                "type": "string",
                "description": "Employee identifier.",
            },
            "employee_name": {
                "type": "string",
                "description": "Employee name.",
            },
            "gross_salary": {
                "type": "number",
                "description": "Monthly gross salary in TRY.",
            },
            "cumulative_income": {
                "type": "number",
                "description": "Cumulative taxable income so far this year (for bracket accuracy).",
            },
            "month": {
                "type": "string",
                "description": "Payroll month (YYYY-MM).",
            },
            "asg_exemption": {
                "type": "boolean",
                "description": "Whether AGI (minimum living allowance) exemption applies.",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> list[dict]:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save(self, records: list[dict]) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(records, indent=2, ensure_ascii=False))

    def _calculate(self, gross: float, cumulative: float = 0) -> dict:
        # SGK employee deductions
        sgk_employee = round(gross * SGK_EMPLOYEE_RATE, 2)
        unemployment_employee = round(gross * SGK_UNEMPLOYMENT_EMPLOYEE, 2)
        total_sgk_employee = sgk_employee + unemployment_employee

        # Taxable income
        taxable = gross - total_sgk_employee

        # Income tax (progressive)
        tax = 0.0
        prev_limit = 0.0
        for limit, rate in GELIR_VERGISI_DILIMLERI:
            if cumulative >= limit:
                prev_limit = limit
                continue
            bracket_start = max(cumulative, prev_limit)
            bracket_end = min(cumulative + taxable, limit)
            if bracket_start >= bracket_end:
                prev_limit = limit
                continue
            bracket_tax = (bracket_end - bracket_start) * rate
            tax += bracket_tax
            prev_limit = limit
            if cumulative + taxable <= limit:
                break

        income_tax = round(tax, 2)

        # Stamp tax
        stamp_tax = round(gross * STAMP_TAX_RATE, 2)

        # Total deductions
        total_deductions = total_sgk_employee + income_tax + stamp_tax

        # Net salary
        net = round(gross - total_deductions, 2)

        # Employer costs
        sgk_employer = round(gross * SGK_EMPLOYER_RATE, 2)
        unemployment_employer = round(gross * SGK_UNEMPLOYMENT_EMPLOYER, 2)
        total_employer_cost = round(gross + sgk_employer + unemployment_employer, 2)

        return {
            "gross_salary": gross,
            "sgk_employee": sgk_employee,
            "unemployment_employee": unemployment_employee,
            "total_sgk_employee": total_sgk_employee,
            "taxable_income": round(taxable, 2),
            "income_tax": income_tax,
            "stamp_tax": stamp_tax,
            "total_deductions": round(total_deductions, 2),
            "net_salary": net,
            "sgk_employer": sgk_employer,
            "unemployment_employer": unemployment_employer,
            "total_employer_cost": total_employer_cost,
        }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        if action == "calculate_salary":
            gross = kwargs.get("gross_salary")
            if not gross:
                return {"error": "gross_salary is required."}
            cumulative = kwargs.get("cumulative_income", 0)
            result = self._calculate(gross, cumulative)
            return result

        elif action == "generate_payslip":
            gross = kwargs.get("gross_salary")
            emp_id = kwargs.get("employee_id")
            if not gross or not emp_id:
                return {"error": "gross_salary and employee_id are required."}

            cumulative = kwargs.get("cumulative_income", 0)
            calc = self._calculate(gross, cumulative)
            month = kwargs.get("month", datetime.now().strftime("%Y-%m"))

            payslip = {
                "id": uuid4().hex[:8],
                "employee_id": emp_id,
                "employee_name": kwargs.get("employee_name", ""),
                "month": month,
                **calc,
                "created_at": datetime.now().isoformat(),
            }

            records = self._load()
            records.append(payslip)
            self._save(records)

            return {"message": "Payslip generated.", "payslip": payslip}

        elif action == "list_payroll":
            records = self._load()
            emp_id = kwargs.get("employee_id")
            month = kwargs.get("month")
            if emp_id:
                records = [r for r in records if r["employee_id"] == emp_id]
            if month:
                records = [r for r in records if r["month"] == month]
            return {"records": records, "count": len(records)}

        return {"error": f"Unknown action: {action}"}
