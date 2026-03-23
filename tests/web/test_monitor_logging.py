from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch

from src.web import app as web_app


def test_create_app_initializes_monitor_file_logging(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MONITOR_LOG_DIR", str(tmp_path))

    with patch.object(web_app, "setup_logging") as setup_logging_mock:
        web_app.create_app(
            start_background_services=False,
            snapshot_reader=MagicMock(),
            state_reader=MagicMock(),
        )

    setup_logging_mock.assert_called_once_with("INFO", str(tmp_path), "monitor")


def test_monitor_app_script_entrypoint_loads_without_import_error(tmp_path) -> None:
    app_path = Path(__file__).resolve().parents[2] / "src" / "web" / "app.py"
    probe = (
        "import runpy; "
        f"runpy.run_path(r'{app_path.as_posix()}')"
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
