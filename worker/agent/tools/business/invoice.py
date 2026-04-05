"""Invoice tool - create professional invoices."""

from pathlib import Path
from typing import Any
from datetime import datetime

from agent.tools.base import BaseTool


class InvoiceTool(BaseTool):
    name = "invoice"
    description = (
        "Create professional invoices in PDF format. "
        "Includes company info, line items, tax calculations, totals, and payment terms."
    )
    parameters = {
        "type": "object",
        "properties": {
            "output_path": {"type": "string"},
            "invoice_number": {"type": "string"},
            "from_company": {"type": "object", "description": "{name, address, email, phone}"},
            "to_company": {"type": "object", "description": "{name, address, email}"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_price": {"type": "number"},
                    },
                },
            },
            "tax_rate": {"type": "number", "description": "Tax rate as percentage (e.g., 18 for 18%)"},
            "currency": {"type": "string"},
            "notes": {"type": "string"},
            "due_date": {"type": "string"},
        },
        "required": ["output_path", "invoice_number", "items"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT

        output = kwargs["output_path"]
        Path(output).parent.mkdir(parents=True, exist_ok=True)

        items = kwargs["items"]
        tax_rate = kwargs.get("tax_rate", 0)
        currency = kwargs.get("currency", "USD")

        doc = SimpleDocTemplate(output, pagesize=A4)
        styles = getSampleStyleSheet()
        right_style = ParagraphStyle("right", parent=styles["Normal"], alignment=TA_RIGHT)
        story = []

        # Header
        story.append(Paragraph("INVOICE", styles["Title"]))
        story.append(Paragraph(f"Invoice #: {kwargs['invoice_number']}", styles["Normal"]))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles["Normal"]))
        if kwargs.get("due_date"):
            story.append(Paragraph(f"Due Date: {kwargs['due_date']}", styles["Normal"]))
        story.append(Spacer(1, 20))

        # From / To
        from_co = kwargs.get("from_company", {})
        to_co = kwargs.get("to_company", {})
        if from_co or to_co:
            info_data = [["From:", "To:"]]
            info_data.append([from_co.get("name", ""), to_co.get("name", "")])
            info_data.append([from_co.get("address", ""), to_co.get("address", "")])
            info_data.append([from_co.get("email", ""), to_co.get("email", "")])
            info_table = Table(info_data, colWidths=[250, 250])
            info_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 20))

        # Line items
        table_data = [["#", "Description", "Qty", "Unit Price", "Total"]]
        subtotal = 0
        for i, item in enumerate(items, 1):
            qty = item.get("quantity", 1)
            price = item.get("unit_price", 0)
            total = qty * price
            subtotal += total
            table_data.append([
                str(i),
                item.get("description", ""),
                str(qty),
                f"{currency} {price:,.2f}",
                f"{currency} {total:,.2f}",
            ])

        tax_amount = subtotal * (tax_rate / 100)
        grand_total = subtotal + tax_amount

        table_data.append(["", "", "", "Subtotal:", f"{currency} {subtotal:,.2f}"])
        if tax_rate:
            table_data.append(["", "", "", f"Tax ({tax_rate}%):", f"{currency} {tax_amount:,.2f}"])
        table_data.append(["", "", "", "TOTAL:", f"{currency} {grand_total:,.2f}"])

        t = Table(table_data, colWidths=[30, 230, 50, 90, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4c6ef5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, len(items)), 0.5, colors.grey),
            ("FONTNAME", (-2, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (-2, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(t)

        if kwargs.get("notes"):
            story.append(Spacer(1, 30))
            story.append(Paragraph("Notes:", styles["Heading4"]))
            story.append(Paragraph(kwargs["notes"], styles["Normal"]))

        doc.build(story)
        return f"Invoice created: {output} | Total: {currency} {grand_total:,.2f}"
