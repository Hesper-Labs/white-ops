"""Tax calculator tool - Turkish tax calculations."""

from typing import Any

from agent.tools.base import BaseTool

# Turkish income tax brackets for 2024 (cumulative)
GELIR_VERGISI_DILIMLERI = [
    (110_000, 0.15),
    (230_000, 0.20),
    (580_000, 0.27),
    (3_000_000, 0.35),
    (float("inf"), 0.40),
]

# Turkish VAT (KDV) rates
KDV_RATES = {
    "reduced_1": 1,
    "reduced_10": 10,
    "standard": 20,
}

# Withholding tax (stopaj) common rates
STOPAJ_RATES = {
    "rent": 20,
    "freelance": 20,
    "interest": 10,
    "dividend": 10,
    "royalty": 20,
    "salary": None,  # progressive, use income tax
}


class TaxCalculatorTool(BaseTool):
    name = "tax_calculator"
    description = (
        "Calculate Turkish taxes including KDV (VAT at 1%/10%/20%), "
        "gelir vergisi (income tax with progressive brackets), "
        "and stopaj (withholding tax). Supports Turkish tax rates and regulations."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["calculate_vat", "calculate_income_tax", "calculate_withholding"],
                "description": "Tax calculation to perform.",
            },
            "amount": {
                "type": "number",
                "description": "Base amount for the calculation.",
            },
            "vat_rate": {
                "type": "number",
                "enum": [1, 10, 20],
                "description": "KDV rate percentage (for calculate_vat).",
            },
            "includes_vat": {
                "type": "boolean",
                "description": "If true, amount already includes VAT (for calculate_vat).",
            },
            "withholding_type": {
                "type": "string",
                "enum": ["rent", "freelance", "interest", "dividend", "royalty"],
                "description": "Type of withholding (for calculate_withholding).",
            },
            "cumulative_income": {
                "type": "number",
                "description": "Cumulative income so far in the year (for accurate bracket calculation).",
            },
        },
        "required": ["action", "amount"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        amount = kwargs["amount"]

        if action == "calculate_vat":
            rate = kwargs.get("vat_rate", 20)
            includes_vat = kwargs.get("includes_vat", False)

            if includes_vat:
                base = round(amount / (1 + rate / 100), 2)
                vat = round(amount - base, 2)
                return {
                    "gross_amount": amount,
                    "base_amount": base,
                    "vat_amount": vat,
                    "vat_rate": rate,
                    "description": f"KDV (%{rate}) dahil tutardan hesaplandi.",
                }
            else:
                vat = round(amount * rate / 100, 2)
                total = round(amount + vat, 2)
                return {
                    "base_amount": amount,
                    "vat_amount": vat,
                    "gross_amount": total,
                    "vat_rate": rate,
                    "description": f"KDV (%{rate}) eklendi.",
                }

        elif action == "calculate_income_tax":
            cumulative = kwargs.get("cumulative_income", 0)
            total_income = cumulative + amount
            tax = 0.0
            prev_limit = 0.0
            breakdown = []

            for limit, rate in GELIR_VERGISI_DILIMLERI:
                if cumulative >= limit:
                    prev_limit = limit
                    continue
                taxable_start = max(cumulative, prev_limit)
                taxable_end = min(total_income, limit)
                if taxable_start >= taxable_end:
                    prev_limit = limit
                    continue
                bracket_amount = taxable_end - taxable_start
                bracket_tax = round(bracket_amount * rate, 2)
                tax += bracket_tax
                breakdown.append({
                    "bracket": f"{prev_limit:,.0f} - {limit:,.0f}" if limit != float("inf") else f"{prev_limit:,.0f}+",
                    "rate": f"%{int(rate * 100)}",
                    "taxable_amount": bracket_amount,
                    "tax": bracket_tax,
                })
                prev_limit = limit
                if total_income <= limit:
                    break

            effective_rate = round((tax / amount) * 100, 2) if amount else 0

            return {
                "gross_income": amount,
                "cumulative_before": cumulative,
                "cumulative_after": total_income,
                "income_tax": round(tax, 2),
                "effective_rate": f"%{effective_rate}",
                "brackets": breakdown,
                "description": "Gelir vergisi hesaplandi.",
            }

        elif action == "calculate_withholding":
            wh_type = kwargs.get("withholding_type", "freelance")
            rate = STOPAJ_RATES.get(wh_type)
            if rate is None:
                return {"error": f"Withholding type '{wh_type}' uses progressive rates. Use calculate_income_tax instead."}

            withholding = round(amount * rate / 100, 2)
            net = round(amount - withholding, 2)

            return {
                "gross_amount": amount,
                "withholding_type": wh_type,
                "withholding_rate": f"%{rate}",
                "withholding_amount": withholding,
                "net_amount": net,
                "description": f"Stopaj (%{rate}) hesaplandi - {wh_type}.",
            }

        return {"error": f"Unknown action: {action}"}
