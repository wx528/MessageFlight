import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import QByteArray, QEventLoop, QTimer
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply

from message_flight.persona_rewriter import PersonaRewriter


@pytest.fixture(autouse=True)
def _ensure_qapp(qapp):
    """Request pytest-qt's session-scoped qapp so a QApplication is
    instantiated before any test runs the event loop. pytest-qt only
    creates the QApplication when ``qapp`` is requested, so without
    this autouse dependency the event-loop tests would hang.
    """
    return qapp


def _pump_until(loop, predicate, timeout_ms=2000):
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout_ms)
    while not predicate():
        loop.exec()
    timer.stop()


def test_rewrite_returns_original_when_disabled():
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="x", enabled=False)
    assert rw.rewrite("[WeChat] hi") == "[WeChat] hi"


def test_rewrite_returns_original_when_api_key_empty():
    rw = PersonaRewriter(api_key="", preset_key="airplane", system_prompt="you are X", enabled=True)
    assert rw.rewrite("[WeChat] hi") == "[WeChat] hi"


def test_rewrite_returns_original_when_system_prompt_empty():
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="", enabled=True)
    assert rw.rewrite("[WeChat] hi") == "[WeChat] hi"


def test_rewrite_returns_original_when_message_empty():
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="x", enabled=True)
    assert rw.rewrite("") == ""


def test_rewrite_sends_payload_and_emits_rewritten_text(monkeypatch):
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="you are X", enabled=True)
    captured = {}

    class FakeReply:
        def readAll(self):
            return QByteArray(json.dumps({
                "choices": [{"message": {"content": "__REWRITTEN__"}}]
            }).encode())

        def error(self):
            return QNetworkReply.NetworkError.NoError

        def deleteLater(self):
            pass

    class FakeNAM(QNetworkAccessManager):
        def post(self, request, body):
            captured["url"] = request.url().toString()
            captured["auth"] = bytes(request.rawHeader(b"Authorization")).decode()
            captured["body"] = bytes(body).decode()
            return FakeReply()

    monkeypatch.setattr(PersonaRewriter, "_make_nam", lambda self: FakeNAM())

    results = []

    def collect(text):
        results.append(text)

    rw.rewrite_finished.connect(collect)
    sync = rw.rewrite("[WeChat] hi")
    if sync is not None:
        results.append(sync)

    loop = QEventLoop()
    rw.rewrite_finished.connect(lambda _t: loop.quit())
    _pump_until(loop, lambda: len(results) >= 1, timeout_ms=3000)

    assert "minimaxi" in captured["url"].lower() or "minimax" in captured["url"].lower()
    assert captured["auth"] == "Bearer abc"
    payload = json.loads(captured["body"])
    assert payload["model"]
    messages = payload["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "you are X"
    assert messages[1]["role"] == "user"
    assert "[WeChat] hi" in messages[1]["content"]
    assert "__REWRITTEN__" in results


def test_rewrite_falls_back_to_original_on_network_error(monkeypatch):
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="x", enabled=True)

    class FakeReply:
        def readAll(self):
            return QByteArray(b"")

        def error(self):
            return QNetworkReply.NetworkError.OperationCanceledError

        def errorString(self):
            return "boom"

        def deleteLater(self):
            pass

    class FakeNAM(QNetworkAccessManager):
        def post(self, request, body):
            return FakeReply()

    monkeypatch.setattr(PersonaRewriter, "_make_nam", lambda self: FakeNAM())

    results = []
    rw.rewrite_finished.connect(results.append)
    rw.rewrite("[WeChat] hi")
    loop = QEventLoop()
    rw.rewrite_finished.connect(lambda _t: loop.quit())
    _pump_until(loop, lambda: len(results) >= 1, timeout_ms=3000)
    assert "[WeChat] hi" in results


def test_rewrite_falls_back_to_original_on_status_code_error(monkeypatch):
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="x", enabled=True)

    class FakeReply:
        def readAll(self):
            return QByteArray(json.dumps({
                "base_resp": {"status_code": 1001, "status_msg": "auth failed"},
            }).encode())

        def error(self):
            return QNetworkReply.NetworkError.NoError

        def deleteLater(self):
            pass

    class FakeNAM(QNetworkAccessManager):
        def post(self, request, body):
            return FakeReply()

    monkeypatch.setattr(PersonaRewriter, "_make_nam", lambda self: FakeNAM())

    results = []
    rw.rewrite_finished.connect(results.append)
    rw.rewrite("[WeChat] hi")
    loop = QEventLoop()
    rw.rewrite_finished.connect(lambda _t: loop.quit())
    _pump_until(loop, lambda: len(results) >= 1, timeout_ms=3000)
    assert "[WeChat] hi" in results


def test_rewrite_falls_back_to_original_on_empty_content(monkeypatch):
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="x", enabled=True)

    class FakeReply:
        def readAll(self):
            return QByteArray(json.dumps({"choices": [{"message": {"content": "  "}}]}).encode())

        def error(self):
            return QNetworkReply.NetworkError.NoError

        def deleteLater(self):
            pass

    class FakeNAM(QNetworkAccessManager):
        def post(self, request, body):
            return FakeReply()

    monkeypatch.setattr(PersonaRewriter, "_make_nam", lambda self: FakeNAM())

    results = []
    rw.rewrite_finished.connect(results.append)
    rw.rewrite("[WeChat] hi")
    loop = QEventLoop()
    rw.rewrite_finished.connect(lambda _t: loop.quit())
    _pump_until(loop, lambda: len(results) >= 1, timeout_ms=3000)
    assert "[WeChat] hi" in results


def test_rewrite_falls_back_to_original_on_json_parse_error(monkeypatch):
    rw = PersonaRewriter(api_key="abc", preset_key="airplane", system_prompt="x", enabled=True)

    class FakeReply:
        def readAll(self):
            return QByteArray(b"not json {{{")

        def error(self):
            return QNetworkReply.NetworkError.NoError

        def deleteLater(self):
            pass

    class FakeNAM(QNetworkAccessManager):
        def post(self, request, body):
            return FakeReply()

    monkeypatch.setattr(PersonaRewriter, "_make_nam", lambda self: FakeNAM())

    results = []
    rw.rewrite_finished.connect(results.append)
    rw.rewrite("[WeChat] hi")
    loop = QEventLoop()
    rw.rewrite_finished.connect(lambda _t: loop.quit())
    _pump_until(loop, lambda: len(results) >= 1, timeout_ms=3000)
    assert "[WeChat] hi" in results
