"""CLI 子命令注册。"""

from __future__ import annotations

import typer

from src.cli.commands.backtest import command as backtest_command
from src.cli.commands.doctor import command as doctor_command
from src.cli.commands.examples import command as examples_command
from src.cli.commands.init import command as init_command
from src.cli.commands.run import command as run_command
from src.cli.commands.validate import command as validate_command


def register_commands(app: typer.Typer) -> None:
    """注册统一 CLI 子命令。"""
    app.command("init")(init_command)
    app.command("run")(run_command)
    app.command("backtest")(backtest_command)
    app.command("validate")(validate_command)
    app.command("doctor")(doctor_command)
    app.command("examples")(examples_command)
