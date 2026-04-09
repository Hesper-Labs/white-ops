"""Data visualization tool - create charts and graphs using matplotlib and seaborn."""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
CHART_DIR = "/tmp/whiteops_charts"


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class VisualizationTool(BaseTool):
    name = "visualization"
    description = (
        "Create charts and visualizations from data. Supports bar charts, line charts, "
        "scatter plots, pie charts, heatmaps, and histograms. "
        "Saves output as PNG images to /tmp/whiteops_charts/."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "bar_chart",
                    "line_chart",
                    "scatter_plot",
                    "pie_chart",
                    "heatmap",
                    "histogram",
                ],
                "description": "Chart type to create.",
            },
            "data": {
                "type": "object",
                "description": "Chart data object. Structure depends on chart type.",
            },
            "x": {
                "type": "string",
                "description": "X-axis data key or label.",
            },
            "y": {
                "type": "string",
                "description": "Y-axis data key or label.",
            },
            "labels": {
                "type": "string",
                "description": "Labels key for pie chart.",
            },
            "values": {
                "type": "string",
                "description": "Values key for pie chart.",
            },
            "column": {
                "type": "string",
                "description": "Column name for histogram.",
            },
            "bins": {
                "type": "integer",
                "description": "Number of bins for histogram (default 20).",
            },
            "title": {
                "type": "string",
                "description": "Chart title.",
            },
            "figsize": {
                "type": "array",
                "items": {"type": "number"},
                "description": "[width, height] in inches (default [10, 6]).",
            },
            "colors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Custom color palette.",
            },
            "xlabel": {
                "type": "string",
                "description": "X-axis label.",
            },
            "ylabel": {
                "type": "string",
                "description": "Y-axis label.",
            },
            "output_path": {
                "type": "string",
                "description": "Custom output file path (optional).",
            },
        },
        "required": ["action", "data"],
    }

    def _setup_plot(self, kwargs: dict):
        """Set up matplotlib figure with common settings."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set_theme(style="whitegrid")

        figsize = tuple(kwargs.get("figsize", [10, 6]))
        fig, ax = plt.subplots(figsize=figsize)
        return fig, ax, plt, sns

    def _get_output_path(self, kwargs: dict, chart_type: str) -> str:
        """Get the output file path."""
        if kwargs.get("output_path"):
            return kwargs["output_path"]

        Path(CHART_DIR).mkdir(parents=True, exist_ok=True)
        filename = f"{chart_type}_{uuid4().hex[:8]}.png"
        return str(Path(CHART_DIR) / filename)

    def _finalize_plot(self, fig, ax, plt, kwargs: dict, output_path: str) -> str:
        """Apply common styling and save the chart."""
        title = kwargs.get("title", "")
        xlabel = kwargs.get("xlabel", "")
        ylabel = kwargs.get("ylabel", "")

        if title:
            ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=11)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=11)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        file_size = Path(output_path).stat().st_size
        return _truncate(json.dumps({
            "success": True,
            "file_path": output_path,
            "file_size_bytes": file_size,
            "title": title,
        }))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("visualization_execute", action=action)

        try:
            if action == "bar_chart":
                return await self._bar_chart(kwargs)
            elif action == "line_chart":
                return await self._line_chart(kwargs)
            elif action == "scatter_plot":
                return await self._scatter_plot(kwargs)
            elif action == "pie_chart":
                return await self._pie_chart(kwargs)
            elif action == "heatmap":
                return await self._heatmap(kwargs)
            elif action == "histogram":
                return await self._histogram(kwargs)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except ImportError as e:
            return _truncate(json.dumps({"error": f"Required library not available: {e}"}))
        except Exception as e:
            logger.error("visualization_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Chart creation failed: {e}"}))

    async def _bar_chart(self, kwargs: dict) -> str:
        fig, ax, plt, sns = self._setup_plot(kwargs)
        data = kwargs.get("data", {})
        x_key = kwargs.get("x", "x")
        y_key = kwargs.get("y", "y")
        colors = kwargs.get("colors")

        x_data = data.get(x_key, data.get("labels", []))
        y_data = data.get(y_key, data.get("values", []))

        color = colors[0] if colors else "#4c6ef5"
        ax.bar(x_data, y_data, color=color, edgecolor="white", linewidth=0.5)
        ax.grid(True, alpha=0.3, axis="y")

        if len(x_data) > 8:
            plt.xticks(rotation=45, ha="right")

        output = self._get_output_path(kwargs, "bar")
        logger.info("visualization_bar_chart", items=len(x_data))
        return self._finalize_plot(fig, ax, plt, kwargs, output)

    async def _line_chart(self, kwargs: dict) -> str:
        fig, ax, plt, sns = self._setup_plot(kwargs)
        data = kwargs.get("data", {})
        x_key = kwargs.get("x", "x")
        y_key = kwargs.get("y", "y")
        colors = kwargs.get("colors")

        x_data = data.get(x_key, data.get("labels", []))
        y_data = data.get(y_key, data.get("values", []))

        color = colors[0] if colors else "#4c6ef5"
        ax.plot(x_data, y_data, marker="o", color=color, linewidth=2, markersize=5)
        ax.fill_between(range(len(y_data)), y_data, alpha=0.1, color=color)
        ax.grid(True, alpha=0.3)

        if len(x_data) > 8:
            plt.xticks(rotation=45, ha="right")

        output = self._get_output_path(kwargs, "line")
        logger.info("visualization_line_chart", items=len(x_data))
        return self._finalize_plot(fig, ax, plt, kwargs, output)

    async def _scatter_plot(self, kwargs: dict) -> str:
        fig, ax, plt, sns = self._setup_plot(kwargs)
        data = kwargs.get("data", {})
        x_key = kwargs.get("x", "x")
        y_key = kwargs.get("y", "y")
        colors = kwargs.get("colors")

        x_data = data.get(x_key, [])
        y_data = data.get(y_key, [])

        color = colors[0] if colors else "#4c6ef5"
        ax.scatter(x_data, y_data, color=color, alpha=0.7, edgecolors="white", linewidth=0.5, s=60)
        ax.grid(True, alpha=0.3)

        output = self._get_output_path(kwargs, "scatter")
        logger.info("visualization_scatter_plot", points=len(x_data))
        return self._finalize_plot(fig, ax, plt, kwargs, output)

    async def _pie_chart(self, kwargs: dict) -> str:
        fig, ax, plt, sns = self._setup_plot(kwargs)
        data = kwargs.get("data", {})
        labels_key = kwargs.get("labels", "labels")
        values_key = kwargs.get("values", "values")
        colors = kwargs.get("colors")

        labels = data.get(labels_key, [])
        values = data.get(values_key, [])

        palette = colors or sns.color_palette("husl", len(labels))
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=palette,
            pctdistance=0.85,
        )
        for autotext in autotexts:
            autotext.set_fontsize(9)

        output = self._get_output_path(kwargs, "pie")
        logger.info("visualization_pie_chart", segments=len(labels))
        return self._finalize_plot(fig, ax, plt, kwargs, output)

    async def _heatmap(self, kwargs: dict) -> str:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set_theme(style="whitegrid")

        data = kwargs.get("data", {})
        figsize = tuple(kwargs.get("figsize", [10, 8]))
        fig, ax = plt.subplots(figsize=figsize)

        # Data should be a 2D array or dict of lists
        import pandas as pd
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame(data)

        sns.heatmap(
            df.select_dtypes(include=["number"]),
            annot=True,
            fmt=".1f",
            cmap="YlOrRd",
            ax=ax,
            linewidths=0.5,
        )

        output = self._get_output_path(kwargs, "heatmap")
        logger.info("visualization_heatmap", shape=df.shape)
        return self._finalize_plot(fig, ax, plt, kwargs, output)

    async def _histogram(self, kwargs: dict) -> str:
        fig, ax, plt, sns = self._setup_plot(kwargs)
        data = kwargs.get("data", {})
        column = kwargs.get("column", "")
        bins = kwargs.get("bins", 20)
        colors = kwargs.get("colors")

        if column and column in data:
            values = data[column]
        elif isinstance(data, dict) and "values" in data:
            values = data["values"]
        elif isinstance(data, list):
            values = data
        else:
            # Use first list found in data
            values = next((v for v in data.values() if isinstance(v, list)), [])

        color = colors[0] if colors else "#4c6ef5"
        ax.hist(values, bins=bins, color=color, edgecolor="white", linewidth=0.5, alpha=0.8)
        ax.grid(True, alpha=0.3, axis="y")

        output = self._get_output_path(kwargs, "histogram")
        logger.info("visualization_histogram", values=len(values), bins=bins)
        return self._finalize_plot(fig, ax, plt, kwargs, output)
