"""策略运行命令。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from src.cli.common import (
    EXIT_CODE_FAILURE,
    abort,
    append_flag,
    append_option,
    flag_enabled,
    invoke_legacy_main,
)


class RunMode(str, Enum):
    standalone = "standalone"
    daemon = "daemon"


class LogLevel(str, Enum):
    debug = "DEBUG"
    info = "INFO"
    warning = "WARNING"
    error = "ERROR"


def command(
    mode: RunMode = typer.Option(RunMode.standalone, "--mode", help="运行模式：standalone 或 daemon。"),
    config: Path = typer.Option(Path("config/strategy_config.toml"), "--config", help="策略配置文件路径。"),
    override_config: Optional[Path] = typer.Option(None, "--override-config", help="覆盖配置文件路径。"),
    log_level: LogLevel = typer.Option(LogLevel.info, "--log-level", help="日志级别。"),
    log_dir: Path = typer.Option(Path("data/logs"), "--log-dir", help="日志目录。"),
    no_ui: str = typer.Option("", "--no-ui", flag_value="1", show_default=False, help="无界面模式运行。"),
    paper: str = typer.Option("", "--paper", flag_value="1", show_default=False, help="启用模拟交易模式。"),
) -> None:
    """运行策略主程序。"""
    argv: list[str] = []
    append_option(argv, "--mode", mode.value)
    append_option(argv, "--config", config)
    append_option(argv, "--override-config", override_config)
    append_option(argv, "--log-level", log_level.value)
    append_option(argv, "--log-dir", log_dir)
    append_flag(argv, "--no-ui", flag_enabled(no_ui))
    append_flag(argv, "--paper", flag_enabled(paper))

    try:
        from src.main.main import main as legacy_main

        exit_code = invoke_legacy_main(legacy_main, argv)
    except ModuleNotFoundError as exc:
        abort(
            f"运行命令缺少依赖: {exc.name}。请先执行 `pip install -r requirements.txt`，然后运行 `pip install -e .`。",
            exit_code=EXIT_CODE_FAILURE,
        )
    except FileNotFoundError as exc:
        missing_path = exc.filename or str(exc)
        abort(f"运行命令找不到文件: {missing_path}")
    except ValueError as exc:
        abort(str(exc))
    except Exception as exc:
        abort(f"运行命令执行失败: {exc}", exit_code=EXIT_CODE_FAILURE)

    if exit_code:
        raise typer.Exit(code=exit_code)
