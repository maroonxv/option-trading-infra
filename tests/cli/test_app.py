"""统一 CLI 测试。"""

from __future__ import annotations

from pathlib import Path
import tomllib
from unittest.mock import patch

from typer.testing import CliRunner

from src import __version__
from src.cli.app import app

runner = CliRunner()


def test_version_flag_outputs_package_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"option-scaffold {__version__}" in result.stdout


def test_help_lists_phase_two_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "validate" in result.stdout
    assert "doctor" in result.stdout
    assert "examples" in result.stdout


def test_init_command_generates_strategy_scaffold(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["init", "ema_breakout", "--destination", str(tmp_path)],
    )

    created_dir = tmp_path / "ema_breakout"

    assert result.exit_code == 0
    assert created_dir.exists()
    assert (created_dir / "strategy_contract.toml").exists()
    assert (created_dir / "tests" / "test_contracts.py").exists()


def test_create_command_generates_project_workspace(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["create", "alpha_lab", "--destination", str(tmp_path), "-y"],
    )

    created_dir = tmp_path / "alpha_lab"
    config = tomllib.loads((created_dir / "config" / "strategy_config.toml").read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert created_dir.exists()
    assert (created_dir / "src" / "strategies" / "alpha_lab" / "indicator_service.py").exists()
    assert (created_dir / "tests" / "strategies" / "alpha_lab" / "test_contracts.py").exists()
    assert config["strategy_contracts"]["indicator_service"] == (
        "src.strategies.alpha_lab.indicator_service:AlphaLabIndicatorService"
    )


def test_create_command_supports_nested_option_flags(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "create",
            "option_lab",
            "--destination",
            str(tmp_path),
            "--preset",
            "custom",
            "--with",
            "hedging",
            "--with-option",
            "vega-hedging",
            "--without-option",
            "delta-hedging",
            "--no-interactive",
        ],
    )

    created_dir = tmp_path / "option_lab"
    config = tomllib.loads((created_dir / "config" / "strategy_config.toml").read_text(encoding="utf-8"))

    assert result.exit_code == 0
    assert config["service_activation"]["vega_hedging"] is True
    assert config["service_activation"]["delta_hedging"] is False


def test_run_command_forwards_arguments_to_legacy_main() -> None:
    config_path = str(Path("config/strategy_config.toml"))
    override_path = str(Path("config/timeframe/5m.toml"))
    log_dir = str(Path("data/logs/demo"))

    with patch("src.main.main.main", return_value=0) as mock_main:
        result = runner.invoke(
            app,
            [
                "run",
                "--mode",
                "daemon",
                "--config",
                "config/strategy_config.toml",
                "--override-config",
                "config/timeframe/5m.toml",
                "--log-level",
                "DEBUG",
                "--log-dir",
                "data/logs/demo",
                "--no-ui",
                "--paper",
            ],
        )

    assert result.exit_code == 0
    mock_main.assert_called_once_with(
        [
            "--mode",
            "daemon",
            "--config",
            config_path,
            "--override-config",
            override_path,
            "--log-level",
            "DEBUG",
            "--log-dir",
            log_dir,
            "--no-ui",
            "--paper",
        ]
    )


def test_backtest_command_forwards_arguments_to_legacy_main() -> None:
    config_path = str(Path("config/strategy_config.toml"))

    with patch("src.backtesting.cli.main", return_value=0) as mock_main:
        result = runner.invoke(
            app,
            [
                "backtest",
                "--config",
                "config/strategy_config.toml",
                "--start",
                "2025-01-01",
                "--end",
                "2025-03-01",
                "--capital",
                "500000",
                "--rate",
                "0.0001",
                "--slippage",
                "0.5",
                "--size",
                "100",
                "--pricetick",
                "0.1",
                "--no-chart",
            ],
        )

    assert result.exit_code == 0
    mock_main.assert_called_once_with(
        [
            "--config",
            config_path,
            "--start",
            "2025-01-01",
            "--end",
            "2025-03-01",
            "--capital",
            "500000",
            "--rate",
            "0.0001",
            "--slippage",
            "0.5",
            "--size",
            "100",
            "--pricetick",
            "0.1",
            "--no-chart",
        ]
    )


def test_validate_command_reports_success_for_default_config() -> None:
    result = runner.invoke(app, ["validate"])

    assert result.exit_code == 0
    assert "校验通过" in result.stdout
    assert "[OK] 策略配置文件" in result.stdout


def test_validate_command_rejects_inverted_date_range() -> None:
    result = runner.invoke(
        app,
        ["validate", "--start", "2025-03-01", "--end", "2025-01-01"],
    )

    assert result.exit_code == 2
    assert "开始日期 2025-03-01 晚于结束日期 2025-01-01" in result.stdout


def test_examples_command_lists_available_examples() -> None:
    result = runner.invoke(app, ["examples"])

    assert result.exit_code == 0
    assert "ema_cross_example" in result.stdout
    assert "iv_rank_example" in result.stdout


def test_examples_command_shows_selected_example_details() -> None:
    result = runner.invoke(app, ["examples", "ema_cross_example"])

    assert result.exit_code == 0
    assert "示例: ema_cross_example" in result.stdout
    assert "strategy_contract.toml" in result.stdout


def test_doctor_command_reports_summary() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "诊断完成" in result.stdout
    assert "[OK] Python" in result.stdout
