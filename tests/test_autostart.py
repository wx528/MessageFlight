"""Tests for message_flight.autostart module."""
import os
import sys

from message_flight.autostart import _exe_path, _shortcut_path, _startup_folder


def test_startup_folder_uses_appdata():
    folder = _startup_folder()
    assert folder == os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    assert "Startup" in folder


def test_shortcut_path_appends_lnk():
    path = _shortcut_path()
    assert path.endswith("MessageFlight.lnk")
    assert path == os.path.join(_startup_folder(), "MessageFlight.lnk")


def test_exe_path_unfrozen():
    # When not frozen, _exe_path returns the absolute path of __main__
    path = _exe_path()
    assert os.path.isabs(path)
    assert path.endswith(os.path.basename(sys.argv[0]))
