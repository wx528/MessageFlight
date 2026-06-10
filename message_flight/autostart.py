"""Windows startup folder integration for auto-launch on boot."""
import json
import os
import subprocess
import sys


def _startup_folder():
    return os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")


def _shortcut_path():
    return os.path.join(_startup_folder(), "MessageFlight.lnk")


def _exe_path():
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def is_auto_start_enabled():
    return os.path.exists(_shortcut_path())


def set_auto_start(enabled: bool):
    shortcut = _shortcut_path()
    if enabled:
        target = _exe_path()
        working_dir = os.path.dirname(target)
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut({json.dumps(shortcut)}); '
            f'$s.TargetPath = {json.dumps(target)}; '
            f'$s.WorkingDirectory = {json.dumps(working_dir)}; '
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-Command", ps_cmd], check=True, capture_output=True)
    else:
        if os.path.exists(shortcut):
            os.remove(shortcut)
