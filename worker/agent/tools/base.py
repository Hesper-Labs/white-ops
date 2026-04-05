"""Base class for all agent tools."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base class for all White-Ops tools.

    Every tool must define:
    - name: unique identifier
    - description: what the tool does (shown to LLM)
    - parameters: JSON schema for tool arguments
    - execute(): async method that runs the tool
    """

    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Execute the tool with the given arguments."""
        ...

    def get_definition(self) -> dict:
        """Return the OpenAI-compatible tool definition for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
