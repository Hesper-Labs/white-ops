"""Data visualization tool - create charts and graphs."""

import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agent.tools.base import BaseTool


class DataVisualizationTool(BaseTool):
    name = "data_visualization"
    description = (
        "Create charts and graphs from data. "
        "Supports: bar, line, pie, scatter, histogram, heatmap. "
        "Outputs PNG images."
    )
    parameters = {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["bar", "line", "pie", "scatter", "histogram"],
            },
            "data": {
                "type": "object",
                "description": "Chart data: {labels: [...], values: [...], series_name: '...'}",
            },
            "title": {"type": "string"},
            "xlabel": {"type": "string"},
            "ylabel": {"type": "string"},
            "output_path": {"type": "string"},
            "figsize": {"type": "array", "items": {"type": "number"}, "description": "[width, height]"},
        },
        "required": ["chart_type", "data", "output_path"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        chart_type = kwargs["chart_type"]
        data = kwargs["data"]
        output = kwargs["output_path"]
        title = kwargs.get("title", "")
        xlabel = kwargs.get("xlabel", "")
        ylabel = kwargs.get("ylabel", "")
        figsize = kwargs.get("figsize", [10, 6])

        Path(output).parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=tuple(figsize))

        labels = data.get("labels", [])
        values = data.get("values", [])

        if chart_type == "bar":
            ax.bar(labels, values, color="#4c6ef5")
        elif chart_type == "line":
            ax.plot(labels, values, marker="o", color="#4c6ef5", linewidth=2)
        elif chart_type == "pie":
            ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        elif chart_type == "scatter":
            x = data.get("x", values)
            y = data.get("y", values)
            ax.scatter(x, y, color="#4c6ef5", alpha=0.7)
        elif chart_type == "histogram":
            ax.hist(values, bins=data.get("bins", 20), color="#4c6ef5", edgecolor="white")

        if title:
            ax.set_title(title, fontsize=14, fontweight="bold")
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        if chart_type != "pie":
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output, dpi=150, bbox_inches="tight")
        plt.close()

        return f"Chart saved: {output}"
