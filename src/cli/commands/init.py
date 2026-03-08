"""策略初始化命令。"""

from __future__ import annotations

from pathlib import Path

import typer

from src.cli.common import EXIT_CODE_VALIDATION, abort, flag_enabled
from src.main.scaffold.generator import scaffold_strategy


def command(
    name: str = typer.Argument(..., help="策略目录名，例如 ema_breakout。"),
    destination: Path = typer.Option(Path("example"), "--destination", "-d", help="输出目录，默认写入根目录下的 example/。"),
    force: str = typer.Option("", "--force", flag_value="1", show_default=False, help="目录已存在时允许覆盖文件。"),
) -> None:
    """生成策略开发骨架。"""
    try:
        created = scaffold_strategy(name, destination, force=flag_enabled(force))
    except FileExistsError as exc:
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    typer.echo(f"已生成策略脚手架: {created}")
