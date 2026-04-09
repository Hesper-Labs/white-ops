"""Image processing tool - resize, crop, watermark, convert, and inspect images."""

import json
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
MAX_IMAGE_SIZE = 50 * 1024 * 1024  # 50MB


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class ImageTool(BaseTool):
    name = "image_processor"
    description = (
        "Process images: resize, crop, add watermarks, convert formats, "
        "and get image info. Supports PNG, JPEG, WebP, and BMP formats. "
        "Max image size: 50MB."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["resize", "crop", "watermark", "convert", "get_info"],
                "description": "Image processing action.",
            },
            "input": {
                "type": "string",
                "description": "Input image file path.",
            },
            "output": {
                "type": "string",
                "description": "Output image file path (for resize, crop, watermark, convert).",
            },
            "width": {
                "type": "integer",
                "description": "Target width in pixels.",
            },
            "height": {
                "type": "integer",
                "description": "Target height in pixels.",
            },
            "maintain_aspect": {
                "type": "boolean",
                "description": "Maintain aspect ratio when resizing (default: true).",
            },
            "x": {
                "type": "integer",
                "description": "X coordinate for crop starting point.",
            },
            "y": {
                "type": "integer",
                "description": "Y coordinate for crop starting point.",
            },
            "text": {
                "type": "string",
                "description": "Watermark text.",
            },
            "position": {
                "type": "string",
                "enum": ["top-left", "top-right", "bottom-left", "bottom-right", "center"],
                "description": "Watermark position (default: bottom-right).",
            },
            "output_format": {
                "type": "string",
                "enum": ["png", "jpg", "webp", "bmp"],
                "description": "Output format for convert action.",
            },
        },
        "required": ["action", "input"],
    }

    def _validate_input(self, input_path: str) -> str | None:
        """Validate input file exists and is within size limit. Returns error message or None."""
        if not Path(input_path).exists():
            return f"Input file not found: {input_path}"

        file_size = Path(input_path).stat().st_size
        if file_size > MAX_IMAGE_SIZE:
            return f"Image too large ({file_size / (1024*1024):.1f}MB). Maximum: 50MB."
        return None

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        input_path = kwargs.get("input", "")
        logger.info("image_processor_execute", action=action, input=input_path)

        if not input_path:
            return _truncate(json.dumps({"error": "'input' file path is required"}))

        error = self._validate_input(input_path)
        if error:
            return _truncate(json.dumps({"error": error}))

        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return _truncate(json.dumps({"error": "Pillow (PIL) library is required for image processing"}))

        try:
            if action == "get_info":
                return await self._get_info(input_path, Image)
            elif action == "resize":
                return await self._resize(kwargs, Image)
            elif action == "crop":
                return await self._crop(kwargs, Image)
            elif action == "watermark":
                return await self._watermark(kwargs, Image, ImageDraw, ImageFont)
            elif action == "convert":
                return await self._convert(kwargs, Image)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("image_processor_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Image processing failed: {e}"}))

    async def _get_info(self, input_path: str, Image) -> str:
        img = Image.open(input_path)
        info = {
            "file_path": input_path,
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "size_bytes": Path(input_path).stat().st_size,
            "size_human": f"{Path(input_path).stat().st_size / 1024:.1f}KB",
        }

        # Get EXIF data if available
        exif = img.getexif()
        if exif:
            info["has_exif"] = True
            info["exif_tags_count"] = len(exif)
        else:
            info["has_exif"] = False

        img.close()
        logger.info("image_info", path=input_path, width=info["width"], height=info["height"])
        return _truncate(json.dumps(info))

    async def _resize(self, kwargs: dict, Image) -> str:
        input_path = kwargs["input"]
        output_path = kwargs.get("output", "")
        if not output_path:
            return _truncate(json.dumps({"error": "'output' path is required for resize"}))

        width = kwargs.get("width")
        height = kwargs.get("height")
        maintain_aspect = kwargs.get("maintain_aspect", True)

        img = Image.open(input_path)
        orig_w, orig_h = img.size

        if maintain_aspect:
            if width and height:
                # Fit within the box while maintaining aspect ratio
                img.thumbnail((width, height), Image.Resampling.LANCZOS)
            elif width:
                ratio = width / orig_w
                height = int(orig_h * ratio)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            elif height:
                ratio = height / orig_h
                width = int(orig_w * ratio)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
            else:
                return _truncate(json.dumps({"error": "At least 'width' or 'height' is required"}))
        else:
            if not width or not height:
                return _truncate(json.dumps({"error": "Both 'width' and 'height' required when maintain_aspect is false"}))
            img = img.resize((width, height), Image.Resampling.LANCZOS)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fmt = Path(output_path).suffix[1:].upper() or "PNG"
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt == "JPEG" and img.mode == "RGBA":
            img = img.convert("RGB")

        img.save(output_path, format=fmt)
        img.close()

        logger.info("image_resized", output=output_path, size=f"{img.width}x{img.height}")
        return _truncate(json.dumps({
            "success": True,
            "output": output_path,
            "original_size": f"{orig_w}x{orig_h}",
            "new_size": f"{img.width}x{img.height}",
        }))

    async def _crop(self, kwargs: dict, Image) -> str:
        input_path = kwargs["input"]
        output_path = kwargs.get("output", "")
        if not output_path:
            return _truncate(json.dumps({"error": "'output' path is required for crop"}))

        x = kwargs.get("x", 0)
        y = kwargs.get("y", 0)
        width = kwargs.get("width")
        height = kwargs.get("height")

        if width is None or height is None:
            return _truncate(json.dumps({"error": "'width' and 'height' are required for crop"}))

        img = Image.open(input_path)

        # Validate crop bounds
        if x + width > img.width or y + height > img.height:
            return _truncate(json.dumps({
                "error": f"Crop region ({x},{y},{width},{height}) exceeds image bounds ({img.width}x{img.height})",
            }))

        cropped = img.crop((x, y, x + width, y + height))

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fmt = Path(output_path).suffix[1:].upper() or "PNG"
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt == "JPEG" and cropped.mode == "RGBA":
            cropped = cropped.convert("RGB")

        cropped.save(output_path, format=fmt)
        img.close()
        cropped.close()

        logger.info("image_cropped", output=output_path, region=f"{x},{y},{width},{height}")
        return _truncate(json.dumps({
            "success": True,
            "output": output_path,
            "crop_region": {"x": x, "y": y, "width": width, "height": height},
            "result_size": f"{width}x{height}",
        }))

    async def _watermark(self, kwargs: dict, Image, ImageDraw, ImageFont) -> str:
        input_path = kwargs["input"]
        output_path = kwargs.get("output", "")
        text = kwargs.get("text", "")
        position = kwargs.get("position", "bottom-right")

        if not output_path:
            return _truncate(json.dumps({"error": "'output' path is required for watermark"}))
        if not text:
            return _truncate(json.dumps({"error": "'text' is required for watermark"}))

        img = Image.open(input_path).convert("RGBA")

        # Create watermark overlay
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Try to use a reasonable font size
        font_size = max(img.width // 30, 16)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        except OSError:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except OSError:
                font = ImageFont.load_default()

        # Calculate text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        margin = 20
        positions = {
            "top-left": (margin, margin),
            "top-right": (img.width - text_w - margin, margin),
            "bottom-left": (margin, img.height - text_h - margin),
            "bottom-right": (img.width - text_w - margin, img.height - text_h - margin),
            "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
        }

        pos = positions.get(position, positions["bottom-right"])
        draw.text(pos, text, fill=(255, 255, 255, 128), font=font)

        result = Image.alpha_composite(img, overlay)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fmt = Path(output_path).suffix[1:].upper() or "PNG"
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt in ("JPEG", "BMP"):
            result = result.convert("RGB")

        result.save(output_path, format=fmt)
        img.close()
        result.close()

        logger.info("image_watermarked", output=output_path, text=text, position=position)
        return _truncate(json.dumps({
            "success": True,
            "output": output_path,
            "watermark_text": text,
            "position": position,
        }))

    async def _convert(self, kwargs: dict, Image) -> str:
        input_path = kwargs["input"]
        output_format = kwargs.get("output_format", "png")
        output_path = kwargs.get("output", "")

        if not output_path:
            # Auto-generate output path
            stem = Path(input_path).stem
            parent = Path(input_path).parent
            output_path = str(parent / f"{stem}.{output_format}")

        img = Image.open(input_path)

        fmt_map = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP", "bmp": "BMP"}
        fmt = fmt_map.get(output_format.lower(), "PNG")

        if fmt == "JPEG" and img.mode == "RGBA":
            img = img.convert("RGB")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format=fmt)

        new_size = Path(output_path).stat().st_size
        orig_size = Path(input_path).stat().st_size

        img.close()

        logger.info("image_converted", output=output_path, format=fmt)
        return _truncate(json.dumps({
            "success": True,
            "output": output_path,
            "format": fmt,
            "original_size_bytes": orig_size,
            "new_size_bytes": new_size,
        }))
