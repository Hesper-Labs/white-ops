"""PDF tool - read, create, merge, and manipulate PDF files."""

import json
from pathlib import Path
from typing import Any

from pypdf import PdfMerger, PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from agent.tools.base import BaseTool


class PDFTool(BaseTool):
    name = "pdf"
    description = (
        "Read, create, merge, and manipulate PDF files. "
        "Supports: reading text, creating PDFs with paragraphs/tables, "
        "merging multiple PDFs, splitting pages, and getting metadata."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "create", "merge", "split", "metadata"],
            },
            "filepath": {"type": "string"},
            "content": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Content blocks: [{type: 'heading'|'paragraph'|'table', text/data: ...}]",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of PDF file paths (for merge)",
            },
            "pages": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Page numbers to extract (for split)",
            },
            "output": {"type": "string", "description": "Output file path"},
        },
        "required": ["action", "filepath"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        filepath = kwargs["filepath"]

        if action == "read":
            reader = PdfReader(filepath)
            pages = []
            for i, page in enumerate(reader.pages):
                pages.append({"page": i + 1, "text": page.extract_text() or ""})
            return json.dumps({"pages": len(pages), "content": pages})

        elif action == "create":
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []

            for block in kwargs.get("content", []):
                block_type = block.get("type", "paragraph")
                if block_type == "heading":
                    story.append(Paragraph(block.get("text", ""), styles["Heading1"]))
                    story.append(Spacer(1, 12))
                elif block_type == "paragraph":
                    story.append(Paragraph(block.get("text", ""), styles["Normal"]))
                    story.append(Spacer(1, 6))
                elif block_type == "table":
                    data = block.get("data", [])
                    if data:
                        t = Table(data)
                        t.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ]))
                        story.append(t)
                        story.append(Spacer(1, 12))

            doc.build(story)
            return f"Created PDF: {filepath}"

        elif action == "merge":
            merger = PdfMerger()
            for f in kwargs.get("files", []):
                merger.append(f)
            output = kwargs.get("output", filepath)
            merger.write(output)
            merger.close()
            return f"Merged {len(kwargs.get('files', []))} PDFs into {output}"

        elif action == "split":
            reader = PdfReader(filepath)
            writer = PdfWriter()
            pages = kwargs.get("pages", list(range(len(reader.pages))))
            for p in pages:
                writer.add_page(reader.pages[p])
            output = kwargs.get("output", filepath.replace(".pdf", "_split.pdf"))
            with open(output, "wb") as f:
                writer.write(f)
            return f"Split {len(pages)} pages to {output}"

        elif action == "metadata":
            reader = PdfReader(filepath)
            meta = reader.metadata
            return json.dumps({
                "pages": len(reader.pages),
                "title": meta.title if meta else None,
                "author": meta.author if meta else None,
            })

        return f"Unknown action: {action}"
