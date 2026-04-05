"""Contract generator tool - create PDF contracts from template data."""

from datetime import datetime
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool


class ContractGeneratorTool(BaseTool):
    name = "contract_generator"
    description = (
        "Generate professional PDF contracts with parties, terms, clauses, "
        "and signature sections. Supports customizable contract templates."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["generate"],
                "description": "Action to perform.",
            },
            "output_path": {
                "type": "string",
                "description": "Path for the output PDF file.",
            },
            "contract_title": {
                "type": "string",
                "description": "Title of the contract.",
            },
            "contract_number": {
                "type": "string",
                "description": "Contract reference number.",
            },
            "date": {
                "type": "string",
                "description": "Contract date (YYYY-MM-DD). Defaults to today.",
            },
            "party_a": {
                "type": "object",
                "description": "First party details: {name, title, address, tax_id}.",
            },
            "party_b": {
                "type": "object",
                "description": "Second party details: {name, title, address, tax_id}.",
            },
            "terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of contract terms/clauses.",
            },
            "scope": {
                "type": "string",
                "description": "Scope of work or contract subject.",
            },
            "payment_terms": {
                "type": "string",
                "description": "Payment terms and conditions.",
            },
            "duration": {
                "type": "string",
                "description": "Contract duration (e.g., '12 months').",
            },
            "governing_law": {
                "type": "string",
                "description": "Governing law jurisdiction. Default: 'Turkiye Cumhuriyeti Kanunlari'.",
            },
        },
        "required": ["action", "output_path"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm

        output_path = kwargs["output_path"]
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        contract_title = kwargs.get("contract_title", "HIZMET SOZLESMESI")
        contract_number = kwargs.get("contract_number", "")
        contract_date = kwargs.get("date", datetime.now().strftime("%Y-%m-%d"))
        party_a = kwargs.get("party_a", {})
        party_b = kwargs.get("party_b", {})
        terms = kwargs.get("terms", [])
        scope = kwargs.get("scope", "")
        payment_terms = kwargs.get("payment_terms", "")
        duration = kwargs.get("duration", "")
        governing_law = kwargs.get("governing_law", "Turkiye Cumhuriyeti Kanunlari")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ContractTitle",
            parent=styles["Title"],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
        )
        heading_style = ParagraphStyle(
            "ContractHeading",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "ContractBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
        )
        clause_style = ParagraphStyle(
            "ClauseStyle",
            parent=body_style,
            leftIndent=20,
            spaceBefore=4,
            spaceAfter=4,
        )

        story = []

        # Title
        story.append(Paragraph(contract_title.upper(), title_style))
        if contract_number:
            story.append(Paragraph(f"Sozlesme No: {contract_number}", body_style))
        story.append(Paragraph(f"Tarih: {contract_date}", body_style))
        story.append(Spacer(1, 20))

        # Parties
        story.append(Paragraph("TARAFLAR", heading_style))

        if party_a:
            lines = [f"<b>Taraf A:</b> {party_a.get('name', '')}"]
            if party_a.get("title"):
                lines.append(f"Unvan: {party_a['title']}")
            if party_a.get("address"):
                lines.append(f"Adres: {party_a['address']}")
            if party_a.get("tax_id"):
                lines.append(f"Vergi No: {party_a['tax_id']}")
            story.append(Paragraph("<br/>".join(lines), body_style))
            story.append(Spacer(1, 10))

        if party_b:
            lines = [f"<b>Taraf B:</b> {party_b.get('name', '')}"]
            if party_b.get("title"):
                lines.append(f"Unvan: {party_b['title']}")
            if party_b.get("address"):
                lines.append(f"Adres: {party_b['address']}")
            if party_b.get("tax_id"):
                lines.append(f"Vergi No: {party_b['tax_id']}")
            story.append(Paragraph("<br/>".join(lines), body_style))
            story.append(Spacer(1, 15))

        # Scope
        if scope:
            story.append(Paragraph("SOZLESMENIN KONUSU", heading_style))
            story.append(Paragraph(scope, body_style))
            story.append(Spacer(1, 10))

        # Duration
        if duration:
            story.append(Paragraph("SOZLESME SURESI", heading_style))
            story.append(Paragraph(f"Bu sozlesme {duration} surelidir.", body_style))
            story.append(Spacer(1, 10))

        # Terms
        if terms:
            story.append(Paragraph("SOZLESME MADDELERI", heading_style))
            for i, term in enumerate(terms, 1):
                story.append(Paragraph(f"<b>Madde {i}.</b> {term}", clause_style))
            story.append(Spacer(1, 10))

        # Payment
        if payment_terms:
            story.append(Paragraph("ODEME KOSULLARI", heading_style))
            story.append(Paragraph(payment_terms, body_style))
            story.append(Spacer(1, 10))

        # Governing law
        story.append(Paragraph("UYGULANACAK HUKUK", heading_style))
        story.append(Paragraph(
            f"Bu sozlesme {governing_law} kapsaminda duzenlenmistir. "
            "Uyusmazliklarda yetkili mahkemeler gorevlidir.",
            body_style,
        ))
        story.append(Spacer(1, 30))

        # Signatures
        story.append(Paragraph("IMZALAR", heading_style))
        story.append(Spacer(1, 10))

        sig_data = [
            ["Taraf A", "Taraf B"],
            [party_a.get("name", "_______________"), party_b.get("name", "_______________")],
            ["", ""],
            ["Imza: _______________", "Imza: _______________"],
            [f"Tarih: {contract_date}", f"Tarih: {contract_date}"],
        ]
        sig_table = Table(sig_data, colWidths=[230, 230])
        sig_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 2), (-1, 2), 30),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ]))
        story.append(sig_table)

        try:
            doc.build(story)
            return {
                "message": f"Contract generated: {output_path}",
                "contract_number": contract_number,
                "parties": [party_a.get("name", ""), party_b.get("name", "")],
                "terms_count": len(terms),
            }
        except Exception as e:
            return {"error": f"PDF generation failed: {e}"}
