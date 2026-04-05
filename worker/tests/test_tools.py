import pytest

from agent.tools.base import BaseTool
from agent.tools.registry import ToolRegistry


def test_base_tool_definition():
    class DummyTool(BaseTool):
        name = "dummy"
        description = "A test tool"
        parameters = {"type": "object", "properties": {}}

        async def execute(self, **kwargs):
            return "ok"

    tool = DummyTool()
    definition = tool.get_definition()

    assert definition["type"] == "function"
    assert definition["function"]["name"] == "dummy"
    assert definition["function"]["description"] == "A test tool"


@pytest.mark.asyncio
async def test_dummy_tool_execute():
    class DummyTool(BaseTool):
        name = "dummy"
        description = "A test tool"
        parameters = {"type": "object", "properties": {}}

        async def execute(self, **kwargs):
            return f"result: {kwargs.get('input', 'none')}"

    tool = DummyTool()
    result = await tool.execute(input="test")
    assert result == "result: test"
