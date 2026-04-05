"""OCR tool - extract text from images and PDFs using Tesseract."""

import asyncio
import shutil
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool


class OCRTool(BaseTool):
    name = "ocr"
    description = (
        "Extract text from images and PDF files using Tesseract OCR. "
        "Supports common image formats (PNG, JPG, TIFF, BMP) and PDFs."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["extract_text", "extract_from_pdf"],
                "description": "Action to perform.",
            },
            "file_path": {
                "type": "string",
                "description": "Path to the image or PDF file.",
            },
            "language": {
                "type": "string",
                "description": "OCR language (e.g., 'eng', 'tur', 'eng+tur'). Default: 'eng'.",
            },
            "output_path": {
                "type": "string",
                "description": "Optional path to save extracted text.",
            },
            "pages": {
                "type": "string",
                "description": "Page range for PDF (e.g., '1-3', '1,3,5'). Default: all pages.",
            },
            "dpi": {
                "type": "integer",
                "description": "DPI for PDF rendering. Default: 300.",
            },
        },
        "required": ["action", "file_path"],
    }

    def _check_tesseract(self) -> str | None:
        """Check if tesseract is available."""
        path = shutil.which("tesseract")
        if not path:
            return "Tesseract is not installed. Install with: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)."
        return None

    async def _run_tesseract(self, image_path: str, language: str) -> str:
        """Run tesseract on an image file."""
        cmd = ["tesseract", image_path, "stdout", "-l", language, "--psm", "3"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            error_msg = stderr.decode().strip()
            raise RuntimeError(f"Tesseract failed: {error_msg}")
        return stdout.decode().strip()

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        file_path = kwargs["file_path"]
        language = kwargs.get("language", "eng")

        # Check tesseract availability
        error = self._check_tesseract()
        if error:
            return {"error": error}

        if not Path(file_path).exists():
            return {"error": f"File not found: {file_path}"}

        if action == "extract_text":
            try:
                text = await self._run_tesseract(file_path, language)

                output_path = kwargs.get("output_path")
                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_text(text, encoding="utf-8")

                return {
                    "text": text,
                    "file": file_path,
                    "language": language,
                    "char_count": len(text),
                    "line_count": text.count("\n") + 1 if text else 0,
                    **({"saved_to": output_path} if output_path else {}),
                }
            except RuntimeError as e:
                return {"error": str(e)}

        elif action == "extract_from_pdf":
            import tempfile

            dpi = kwargs.get("dpi", 300)
            pages_arg = kwargs.get("pages")

            # Check for pdftoppm (from poppler)
            if not shutil.which("pdftoppm"):
                return {"error": "pdftoppm not found. Install poppler: brew install poppler (macOS) or apt-get install poppler-utils (Linux)."}

            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Convert PDF pages to images using pdftoppm
                    cmd = ["pdftoppm", "-png", "-r", str(dpi)]
                    if pages_arg:
                        if "-" in pages_arg:
                            first, last = pages_arg.split("-", 1)
                            cmd.extend(["-f", first.strip(), "-l", last.strip()])
                        else:
                            # Single page or comma-separated
                            page_nums = [p.strip() for p in pages_arg.split(",")]
                            cmd.extend(["-f", page_nums[0], "-l", page_nums[-1]])
                    cmd.extend([file_path, f"{tmpdir}/page"])

                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    _, stderr = await proc.communicate()
                    if proc.returncode != 0:
                        return {"error": f"pdftoppm failed: {stderr.decode().strip()}"}

                    # OCR each page image
                    image_files = sorted(Path(tmpdir).glob("*.png"))
                    if not image_files:
                        return {"error": "No pages generated from PDF."}

                    all_text = []
                    for i, img in enumerate(image_files, 1):
                        page_text = await self._run_tesseract(str(img), language)
                        all_text.append(f"--- Page {i} ---\n{page_text}")

                    full_text = "\n\n".join(all_text)

                    output_path = kwargs.get("output_path")
                    if output_path:
                        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                        Path(output_path).write_text(full_text, encoding="utf-8")

                    return {
                        "text": full_text,
                        "file": file_path,
                        "pages_processed": len(image_files),
                        "language": language,
                        "char_count": len(full_text),
                        **({"saved_to": output_path} if output_path else {}),
                    }
            except RuntimeError as e:
                return {"error": str(e)}

        return {"error": f"Unknown action: {action}"}
