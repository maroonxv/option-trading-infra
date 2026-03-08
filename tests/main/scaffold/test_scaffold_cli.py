from __future__ import annotations

from pathlib import Path

from src.main.scaffold.cli import main


def test_scaffold_cli_generates_strategy_template(tmp_path: Path) -> None:
    rc = main(["--name", "alpha_demo", "--destination", str(tmp_path)])

    created = tmp_path / "alpha_demo"
    assert rc == 0
    assert (created / "indicator_service.py").exists()
    assert (created / "signal_service.py").exists()
    assert (created / "strategy_contract.toml").exists()
    assert (created / "tests" / "test_contracts.py").exists()
