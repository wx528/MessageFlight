"""LLM Agent with function calling for voice-driven app control.

Uses the MiniMax chat completion API (OpenAI-compatible) to interpret
free-form speech, decide which built-in tool to call, and generate
natural-language responses.

Architecture:
    1. User speech → STT → text
    2. If the text matches a fixed command keyword → execute directly
    3. Otherwise → send to LLM with available tool definitions
    4. LLM decides: call a tool, or just respond with text
    5. Tool calls are routed back to the app via signals
    6. LLM's text response is spoken via TTS

The agent maintains a short conversation history (last N turns) so it
can handle follow-up questions naturally.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "pause_flight",
            "description": "Pause the airplane flight animation",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resume_flight",
            "description": "Resume the airplane flight animation",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "next_preset",
            "description": "Switch to the next airplane preset / skin",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "toggle_dnd",
            "description": "Toggle Do Not Disturb mode on or off",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True to enable DND, False to disable. If omitted, toggle.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_settings",
            "description": "Open the application settings dialog",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quit_app",
            "description": "Quit / close the application",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_status",
            "description": "Get the current application status (flight state, DND, current preset, etc.)",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_demo",
            "description": "Send a demo / test notification",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

# Map tool names to VoiceCommand-style action keys
TOOL_ACTION_MAP: dict[str, str] = {
    "pause_flight": "pause",
    "resume_flight": "resume",
    "next_preset": "next_preset",
    "toggle_dnd": "toggle_dnd",
    "open_settings": "open_settings",
    "quit_app": "quit_app",
    "get_status": "get_status",
    "send_demo": "send_demo",
}

SYSTEM_PROMPT = (
    "You are the AI assistant for MessageFlight, a desktop notification app with a flying airplane animation. "
    "You understand Chinese and English. When the user asks you to do something, use the available tools. "
    "For casual conversation or questions, respond naturally and concisely (1-2 sentences). "
    "Always respond in the same language the user is speaking."
)

MAX_HISTORY_TURNS = 10  # Keep last 10 messages (5 user + 5 assistant)


class LLMAgent(QObject):
    """Agent that uses LLM function calling to interpret user speech.

    Signals:
        tool_called(action, params): A tool should be executed.
            *action* is one of the keys in TOOL_ACTION_MAP values.
            *params* is a dict of tool parameters.
        text_response(text): The LLM responded with plain text (no tool call).
        error_occurred(msg): An error occurred during the LLM call.
    """

    tool_called = pyqtSignal(str, dict)
    text_response = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    _ENDPOINT = "https://api.minimaxi.com/v1/text/chatcompletion_v2"
    _MODEL = "MiniMax-Text-01"
    _TIMEOUT_MS = 15000

    def __init__(
        self,
        api_key: str = "",
        enabled: bool = True,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._api_key = api_key
        self._enabled = enabled
        self._nam: Optional[QNetworkAccessManager] = None
        self._pending: dict[int, list[dict]] = {}  # id(reply) -> messages sent
        self._history: list[dict[str, str]] = []
        self._status_info: str = ""  # Updated by the app

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def set_api_key(self, api_key: str) -> None:
        self._api_key = api_key

    def set_status_info(self, info: str) -> None:
        """Update the current app status string (injected into system prompt)."""
        self._status_info = info

    def clear_history(self) -> None:
        self._history.clear()

    def chat(self, user_text: str) -> None:
        """Send user text to the LLM for interpretation.

        Results arrive via :signal:`tool_called` or :signal:`text_response`.
        """
        if not self._enabled:
            self.error_occurred.emit("agent disabled")
            return
        if not self._api_key:
            self.error_occurred.emit("no API key")
            return

        # Build messages
        system_content = SYSTEM_PROMPT
        if self._status_info:
            system_content += f"\n\nCurrent app status: {self._status_info}"

        messages = [{"role": "system", "content": system_content}]
        messages.extend(self._history[-MAX_HISTORY_TURNS:])
        messages.append({"role": "user", "content": user_text})

        # Build request
        request = QNetworkRequest(QUrl(self._ENDPOINT))
        request.setTransferTimeout(self._TIMEOUT_MS)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json")
        request.setRawHeader(b"Authorization", f"Bearer {self._api_key}".encode())

        payload: dict[str, Any] = {
            "model": self._MODEL,
            "messages": messages,
            "tools": TOOL_DEFINITIONS,
            "tool_choice": "auto",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        nam = self._get_nam()
        reply = nam.post(request, body)
        self._pending[id(reply)] = messages
        logger.info("LLMAgent.chat: sent %d chars", len(user_text))

    def _get_nam(self) -> QNetworkAccessManager:
        if self._nam is None:
            self._nam = QNetworkAccessManager(self)
            self._nam.finished.connect(self._on_reply_finished)
        return self._nam

    def _on_reply_finished(self, reply: QNetworkReply) -> None:
        messages = self._pending.pop(id(reply), [])
        if not messages:
            reply.deleteLater()
            return

        if reply.error() != QNetworkReply.NetworkError.NoError:
            err = f"LLM network error: {reply.errorString()}"
            logger.warning("LLMAgent: %s", err)
            self.error_occurred.emit(err)
            reply.deleteLater()
            return

        try:
            data = reply.readAll().data().decode("utf-8")
            response = json.loads(data)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            logger.warning("LLMAgent: parse error %s", exc)
            self.error_occurred.emit("LLM response parse error")
            reply.deleteLater()
            return

        # Check API-level error
        base_resp = response.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            err = f"LLM API error: {base_resp.get('status_msg', 'unknown')}"
            logger.warning("LLMAgent: %s", err)
            self.error_occurred.emit(err)
            reply.deleteLater()
            return

        try:
            choice = response["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError):
            logger.warning("LLMAgent: unexpected response structure")
            self.error_occurred.emit("LLM response format error")
            reply.deleteLater()
            return

        # Process the response
        finish_reason = choice.get("finish_reason", "")
        user_text = messages[-1].get("content", "") if messages else ""

        # Handle tool calls
        tool_calls = message.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                tool_params_str = func.get("arguments", "{}")
                try:
                    tool_params = json.loads(tool_params_str) if isinstance(tool_params_str, str) else tool_params_str
                except json.JSONDecodeError:
                    tool_params = {}

                action = TOOL_ACTION_MAP.get(tool_name)
                if action:
                    logger.info("LLMAgent: tool call %s(%s)", tool_name, tool_params)
                    # For get_status, inject the status info into params
                    if action == "get_status":
                        tool_params["_status"] = self._status_info
                    self.tool_called.emit(action, tool_params)
                else:
                    logger.warning("LLMAgent: unknown tool %s", tool_name)

            # Add to history
            self._history.append({"role": "user", "content": user_text})
            # Store assistant message with tool calls
            self._history.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
            self._trim_history()

        elif message.get("content"):
            # Plain text response
            text = message["content"].strip()
            logger.info("LLMAgent: text response %r", text[:80])
            self.text_response.emit(text)

            # Add to history
            self._history.append({"role": "user", "content": user_text})
            self._history.append({"role": "assistant", "content": text})
            self._trim_history()
        else:
            logger.warning("LLMAgent: empty response from LLM")
            self.error_occurred.emit("empty LLM response")

        reply.deleteLater()

    def _trim_history(self) -> None:
        """Keep only the last MAX_HISTORY_TURNS messages."""
        if len(self._history) > MAX_HISTORY_TURNS:
            self._history = self._history[-MAX_HISTORY_TURNS:]
