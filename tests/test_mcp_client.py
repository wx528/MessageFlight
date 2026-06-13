"""Tests for the MCP Client module."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from message_flight.mcp_client import MCPClientManager, MCPToolInfo


@pytest.fixture
def manager():
    """Create an MCPClientManager."""
    m = MCPClientManager()
    yield m


class TestMCPClientManagerInit:
    def test_initial_state(self, manager):
        assert manager._tools == {}
        assert manager._connected_servers == set()

    def test_available_property(self, manager):
        # Just check it returns a bool without error
        assert isinstance(manager.available, bool)


class TestParseToolCall:
    def test_valid_qualified_name(self, manager):
        result = manager.parse_tool_call("mcp__obsidian__search_notes")
        assert result == ("obsidian", "search_notes")

    def test_non_mcp_name(self, manager):
        result = manager.parse_tool_call("pause_flight")
        assert result is None

    def test_malformed_name(self, manager):
        result = manager.parse_tool_call("mcp__onlyonepart")
        assert result is None

    def test_name_with_underscores(self, manager):
        result = manager.parse_tool_call("mcp__my_server__my_tool_name")
        assert result == ("my_server", "my_tool_name")


class TestGetToolDefinitions:
    def test_empty_when_no_tools(self, manager):
        assert manager.get_tool_definitions() == []

    def test_returns_function_definitions(self, manager):
        tool = MCPToolInfo(
            server_name="test",
            tool_name="foo",
            description="A test tool",
            input_schema={"type": "object", "properties": {"x": {"type": "string"}}},
        )
        manager._tools["mcp__test__foo"] = tool
        defs = manager.get_tool_definitions()
        assert len(defs) == 1
        assert defs[0]["type"] == "function"
        assert defs[0]["function"]["name"] == "mcp__test__foo"
        assert defs[0]["function"]["description"] == "[test] A test tool"


class TestMCPToolInfo:
    def test_to_function_definition(self):
        tool = MCPToolInfo(
            server_name="obsidian",
            tool_name="search",
            description="Search notes",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        )
        fd = tool.to_function_definition()
        assert fd["type"] == "function"
        assert fd["function"]["name"] == "mcp__obsidian__search"
        assert fd["function"]["description"] == "[obsidian] Search notes"
        assert "query" in fd["function"]["parameters"]["properties"]


class TestParseServersConfig:
    def test_valid_json(self, manager):
        config = json.dumps({
            "obsidian": {
                "command": "npx",
                "args": ["-y", "@huangyihe/obsidian-mcp"],
            }
        })
        result = manager._parse_servers_config(config)
        assert "obsidian" in result
        assert result["obsidian"].command == "npx"

    def test_invalid_json(self, manager):
        result = manager._parse_servers_config("not json")
        assert result == {}

    def test_empty_string(self, manager):
        result = manager._parse_servers_config("")
        assert result == {}

    def test_non_dict_json(self, manager):
        result = manager._parse_servers_config("[1,2,3]")
        assert result == {}
