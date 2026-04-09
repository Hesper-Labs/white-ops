"""Tool registry - discovers and manages all available tools."""

import importlib
import pkgutil
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

# Tool category directories
TOOL_CATEGORIES = [
    "office",
    "communication",
    "research",
    "data",
    "filesystem",
    "business",
    "technical",
    "finance",
    "hr",
    "integrations",
    "devops",
    "monitoring",
    "cloud",
    "security_tools",
]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._discover_tools()

    def _discover_tools(self) -> None:
        """Auto-discover all tool classes from tool category packages."""
        tools_dir = Path(__file__).parent

        for category in TOOL_CATEGORIES:
            category_dir = tools_dir / category
            if not category_dir.exists():
                continue

            package_name = f"agent.tools.{category}"
            try:
                package = importlib.import_module(package_name)
            except ImportError:
                continue

            for _importer, module_name, _is_pkg in pkgutil.iter_modules([str(category_dir)]):
                try:
                    module = importlib.import_module(f"{package_name}.{module_name}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseTool)
                            and attr is not BaseTool
                            and hasattr(attr, "name")
                        ):
                            tool = attr()
                            self._tools[tool.name] = tool
                            logger.debug("tool_registered", name=tool.name, category=category)
                except Exception as e:
                    logger.warning("tool_load_failed", module=module_name, error=str(e))

        logger.info("tools_loaded", count=len(self._tools))

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_tool_names(self, filter_names: list[str] | None = None) -> list[str]:
        if filter_names:
            return [n for n in filter_names if n in self._tools]
        return list(self._tools.keys())

    def get_tool_definitions(self, filter_names: list[str] | None = None) -> list[dict]:
        if filter_names:
            return [
                self._tools[name].get_definition()
                for name in filter_names
                if name in self._tools
            ]
        return [tool.get_definition() for tool in self._tools.values()]

    async def execute(self, name: str, args: dict) -> Any:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        try:
            return await tool.execute(**args)
        except Exception as e:
            logger.error("tool_execution_failed", tool=name, error=str(e))
            return f"Error executing {name}: {e}"
