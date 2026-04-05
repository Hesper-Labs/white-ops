"""Image processing tool - resize, crop, convert, and manipulate images."""

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from agent.tools.base import BaseTool


class ImageTool(BaseTool):
    name = "image_processing"
    description = (
        "Process images: resize, crop, rotate, convert format, add watermark, "
        "create thumbnails, get info, and combine images."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["resize", "crop", "rotate", "convert", "thumbnail", "info", "watermark"],
            },
            "input_path": {"type": "string"},
            "output_path": {"type": "string"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "format": {"type": "string", "enum": ["PNG", "JPEG", "WEBP", "BMP"]},
            "angle": {"type": "number", "description": "Rotation angle in degrees"},
            "crop_box": {"type": "array", "items": {"type": "integer"}, "description": "[left, top, right, bottom]"},
            "watermark_text": {"type": "string"},
        },
        "required": ["action", "input_path"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        input_path = kwargs["input_path"]

        if action == "info":
            img = Image.open(input_path)
            return json.dumps({
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": Path(input_path).stat().st_size,
            })

        img = Image.open(input_path)
        output = kwargs.get("output_path", input_path)
        Path(output).parent.mkdir(parents=True, exist_ok=True)

        if action == "resize":
            w = kwargs.get("width", img.width)
            h = kwargs.get("height", img.height)
            img = img.resize((w, h), Image.Resampling.LANCZOS)

        elif action == "crop":
            box = kwargs.get("crop_box", [0, 0, img.width, img.height])
            img = img.crop(tuple(box))

        elif action == "rotate":
            angle = kwargs.get("angle", 0)
            img = img.rotate(angle, expand=True)

        elif action == "thumbnail":
            size = (kwargs.get("width", 200), kwargs.get("height", 200))
            img.thumbnail(size, Image.Resampling.LANCZOS)

        elif action == "watermark":
            text = kwargs.get("watermark_text", "White-Ops")
            draw = ImageDraw.Draw(img)
            draw.text(
                (img.width - 150, img.height - 30),
                text,
                fill=(255, 255, 255, 128),
            )

        fmt = kwargs.get("format", Path(output).suffix[1:].upper() or "PNG")
        if fmt == "JPEG" and img.mode == "RGBA":
            img = img.convert("RGB")

        img.save(output, format=fmt)
        return f"Image saved: {output} ({img.width}x{img.height})"
