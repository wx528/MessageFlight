"""Tests for the LLM Agent module."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from message_flight.agent import LLMAgent, TOOL_DEFINITIONS, TOOL_ACTION_MAP


@pytest.fixture
def agent():
    """Create an LLMAgent with a fake API key."""
    a = LLMAgent(api_key="test-key", enabled=True)
    yield a
    # Cleanup: stop any pending network
    if a._nam:
        a._nam.deleteLater()
        a._nam = None


class TestLLMAgentInit:
    def test_default_state(self, agent):
        assert agent.enabled is True
        assert agent._api_key == "test-key"
        assert agent._mcp_tool_definitions == []
        assert agent._history == []

    def test_disabled_agent(self):
        a = LLMAgent(api_key="key", enabled=False)
        assert a.enabled is False


class TestSetMcpTools:
    def test_updates_definitions(self, agent):
        defs = [{"type": "function", "function": {"name": "mcp__test__foo", "parameters": {}}}]
        agent.set_mcp_tools(defs)
        assert agent._mcp_tool_definitions == defs

    def test_replaces_previous(self, agent):
        agent.set_mcp_tools([{"type": "function", "function": {"name": "a"}}])
        agent.set_mcp_tools([{"type": "function", "function": {"name": "b"}}])
        assert len(agent._mcp_tool_definitions) == 1
        assert agent._mcp_tool_definitions[0]["function"]["name"] == "b"


class TestChat:
    def test_disabled_emits_error(self):
        a = LLMAgent(api_key="key", enabled=False)
        with pytest.MonkeyPatch.context() as mp:
            errors = []
            a.error_occurred.connect(lambda msg: errors.append(msg))
            a.chat("hello")
            assert errors == ["agent disabled"]

    def test_no_api_key_emits_error(self):
        a = LLMAgent(api_key="", enabled=True)
        errors = []
        a.error_occurred.connect(lambda msg: errors.append(msg))
        a.chat("hello")
        assert errors == ["no API key"]

    @patch("message_flight.agent.QNetworkAccessManager")
    def test_chat_sends_request(self, mock_nam_cls, agent):
        mock_nam = MagicMock()
        mock_reply = MagicMock()
        mock_nam.post.return_value = mock_reply
        mock_nam_cls.return_value = mock_nam

        agent.chat("hello")

        mock_nam.post.assert_called_once()
        call_args = mock_nam.post.call_args
        request = call_args[0][0]
        body = call_args[0][1]

        # Verify the body contains expected fields
        payload = json.loads(body)
        assert payload["model"] == "MiniMax-Text-01"
        assert len(payload["messages"]) >= 2  # system + user
        assert payload["messages"][-1]["content"] == "hello"
        assert payload["tool_choice"] == "auto"


class TestSubmitToolResult:
    def test_no_api_key_emits_error(self):
        a = LLMAgent(api_key="", enabled=True)
        errors = []
        a.error_occurred.connect(lambda msg: errors.append(msg))
        a.submit_tool_result("mcp__test__foo", "result")
        assert errors == ["no API key"]

    @patch("message_flight.agent.QNetworkAccessManager")
    def test_appends_tool_message_to_history(self, mock_nam_cls, agent):
        mock_nam = MagicMock()
        mock_reply = MagicMock()
        mock_nam.post.return_value = mock_reply
        mock_nam_cls.return_value = mock_nam

        agent.submit_tool_result("mcp__obsidian__search", '{"files": []}')

        # Check history has tool message
        assert len(agent._history) == 1
        assert agent._history[0]["role"] == "tool"
        assert agent._history[0]["name"] == "mcp__obsidian__search"
        assert agent._history[0]["content"] == '{"files": []}'

    @patch("message_flight.agent.QNetworkAccessManager")
    def test_truncates_long_result(self, mock_nam_cls, agent):
        mock_nam = MagicMock()
        mock_reply = MagicMock()
        mock_nam.post.return_value = mock_reply
        mock_nam_cls.return_value = mock_nam

        long_result = "x" * 5000
        agent.submit_tool_result("mcp__test__foo", long_result)

        assert len(agent._history[0]["content"]) == 2000


class TestToolDefinitions:
    def test_all_tools_have_action_mapping(self):
        for td in TOOL_DEFINITIONS:
            name = td["function"]["name"]
            assert name in TOOL_ACTION_MAP, f"Tool {name} missing from TOOL_ACTION_MAP"

    def test_tool_definitions_are_valid(self):
        for td in TOOL_DEFINITIONS:
            assert td["type"] == "function"
            assert "name" in td["function"]
            assert "parameters" in td["function"]
