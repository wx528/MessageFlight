import runpy
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_main_configures_logging_and_runs_tray_app():
    from message_flight.cli import main

    with patch("message_flight.cli.logging.basicConfig") as basic_config, \
         patch("message_flight.cli.TrayApplication") as tray_app:
        main()

    basic_config.assert_called_once_with(
        level=20,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    tray_app.return_value.run.assert_called_once_with()


def test_module_entrypoint_runs_main(monkeypatch):
    main = MagicMock(return_value=None)
    monkeypatch.setattr("message_flight.cli.main", main)

    runpy.run_module("message_flight", run_name="__main__")

    main.assert_called_once_with()


def test_pyproject_installs_messageflight_script():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert '[project.scripts]' in pyproject
    assert 'messageflight = "message_flight.cli:main"' in pyproject
