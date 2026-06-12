"""Tests for STTReader and MiniMaxSTTReader."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtNetwork import QNetworkReply

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    yield app


def test_stt_reader_abstract() -> None:
    from message_flight.stt import STTReader

    with pytest.raises(TypeError):
        STTReader()


def test_minimax_reader_emits_transcribed_on_2xx(qapp) -> None:
    """Successful HTTP response should be parsed and emit (text, audio)."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.NoError
        mock_reply.attribute.return_value = 200
        mock_reply.readAll.return_value.data.return_value = b'{"text": "\u6682\u505c"}'
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="test-key")
        captured = []
        reader.transcribed.connect(lambda text, audio: captured.append((text, audio)))

        audio = b"\x00\x00" * 1600
        reader.transcribe(audio)

        # Simulate the finished signal
        finished = mock_nam.finished.connect.call_args.args[0]
        finished(mock_reply)

        assert len(captured) == 1
        assert captured[0][0] == "暂停"
        assert captured[0][1] == audio


def test_minimax_reader_emits_error_on_network_error(qapp) -> None:
    """Network failure should emit (error_msg, audio) with original audio."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.HostNotFoundError
        mock_reply.errorString.return_value = "host not found"
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="test-key")
        captured = []
        reader.error_occurred.connect(lambda msg, audio: captured.append((msg, audio)))

        audio = b"\x00\x00" * 1600
        reader.transcribe(audio)

        finished = mock_nam.finished.connect.call_args.args[0]
        finished(mock_reply)

        assert len(captured) == 1
        assert "host not found" in captured[0][0]
        assert captured[0][1] == audio


def test_minimax_reader_emits_error_on_empty_body(qapp) -> None:
    """Empty response body should emit error."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.NoError
        mock_reply.attribute.return_value = 200
        mock_reply.readAll.return_value.data.return_value = b""
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="test-key")
        captured = []
        reader.error_occurred.connect(lambda msg, audio: captured.append((msg, audio)))

        audio = b"\x00\x00" * 1600
        reader.transcribe(audio)

        finished = mock_nam.finished.connect.call_args.args[0]
        finished(mock_reply)

        assert len(captured) == 1
        assert "empty" in captured[0][0].lower()


def test_minimax_reader_request_includes_bearer_token(qapp) -> None:
    """Authorization header must contain the configured API key."""

    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="my-secret-key")
        reader.transcribe(b"\x00\x00" * 100)

        # Get the QNetworkRequest passed to post()
        request = mock_nam.post.call_args.args[0]
        auth_header = request.rawHeader(b"Authorization")
        assert auth_header == b"Bearer my-secret-key"


def test_minimax_reader_emits_error_when_no_api_key(qapp) -> None:
    """Empty API key should immediately emit error without network call."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        reader = MiniMaxSTTReader(api_key="")
        captured = []
        reader.error_occurred.connect(lambda msg, audio: captured.append((msg, audio)))

        reader.transcribe(b"\x00\x00" * 100)

        assert len(captured) == 1
        assert "api key" in captured[0][0].lower()
        mock_nam.post.assert_not_called()


def test_minimax_reader_emits_error_on_http_non_200(qapp) -> None:
    """HTTP 4xx/5xx should emit error."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.NoError
        mock_reply.attribute.return_value = 401
        mock_reply.errorString.return_value = "unauthorized"
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="bad-key")
        captured = []
        reader.error_occurred.connect(lambda msg, audio: captured.append((msg, audio)))

        audio = b"\x00\x00" * 100
        reader.transcribe(audio)

        finished = mock_nam.finished.connect.call_args.args[0]
        finished(mock_reply)

        assert len(captured) == 1
        assert "401" in captured[0][0]


def test_minimax_reader_emits_error_on_base_resp_error(qapp) -> None:
    """MiniMax returns HTTP 200 with in-body error."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.NoError
        mock_reply.attribute.return_value = 200
        mock_reply.readAll.return_value.data.return_value = (
            b'{"base_resp": {"status_code": 1004, "status_msg": "invalid api key"}}'
        )
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="test-key")
        captured = []
        reader.error_occurred.connect(lambda msg, audio: captured.append((msg, audio)))

        audio = b"\x00\x00" * 100
        reader.transcribe(audio)

        finished = mock_nam.finished.connect.call_args.args[0]
        finished(mock_reply)

        assert len(captured) == 1
        assert "1004" in captured[0][0] or "invalid api key" in captured[0][0].lower()


def test_minimax_reader_emits_error_on_empty_text_field(qapp) -> None:
    """HTTP 200 with `{"text": ""}` should emit error."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.NoError
        mock_reply.attribute.return_value = 200
        mock_reply.readAll.return_value.data.return_value = b'{"text": ""}'
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="test-key")
        captured = []
        reader.error_occurred.connect(lambda msg, audio: captured.append((msg, audio)))

        audio = b"\x00\x00" * 100
        reader.transcribe(audio)

        finished = mock_nam.finished.connect.call_args.args[0]
        finished(mock_reply)

        assert len(captured) == 1
        assert "empty" in captured[0][0].lower()


def test_minimax_reader_emits_error_on_null_text_field(qapp) -> None:
    """HTTP 200 with `{"text": null}` should emit error (not AttributeError)."""
    from message_flight.stt import MiniMaxSTTReader

    with patch("PyQt6.QtNetwork.QNetworkAccessManager") as mock_nam_cls:
        mock_nam = mock_nam_cls.return_value
        mock_reply = MagicMock()
        mock_reply.error.return_value = QNetworkReply.NetworkError.NoError
        mock_reply.attribute.return_value = 200
        mock_reply.readAll.return_value.data.return_value = b'{"text": null}'
        mock_nam.post.return_value = mock_reply

        reader = MiniMaxSTTReader(api_key="test-key")
        captured = []
        reader.error_occurred.connect(lambda msg, audio: captured.append((msg, audio)))

        audio = b"\x00\x00" * 100
        reader.transcribe(audio)

        finished = mock_nam.finished.connect.call_args.args[0]
        finished(mock_reply)

        assert len(captured) == 1
        assert "empty" in captured[0][0].lower()
