"""回测命令。"""

from __future__ import annotations

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


def command(
    config: Optional[Path] = typer.Option(None, "--config", help="策略配置文件路径。"),
    start: Optional[str] = typer.Option(None, "--start", help="开始日期，格式 YYYY-MM-DD。"),
    end: Optional[str] = typer.Option(None, "--end", help="结束日期，格式 YYYY-MM-DD。"),
    capital: Optional[int] = typer.Option(None, "--capital", help="初始资金。"),
    rate: Optional[float] = typer.Option(None, "--rate", help="手续费率。"),
    slippage: Optional[float] = typer.Option(None, "--slippage", help="滑点。"),
    size: Optional[int] = typer.Option(None, "--size", help="合约乘数。"),
    pricetick: Optional[float] = typer.Option(None, "--pricetick", help="最小价格变动。"),
    no_chart: str = typer.Option("", "--no-chart", flag_value="1", show_default=False, help="不显示图表。"),
) -> None:
    """运行组合策略回测。"""
    argv: list[str] = []
    append_option(argv, "--config", config)
    append_option(argv, "--start", start)
    append_option(argv, "--end", end)
    append_option(argv, "--capital", capital)
    append_option(argv, "--rate", rate)
    append_option(argv, "--slippage", slippage)
    append_option(argv, "--size", size)
    append_option(argv, "--pricetick", pricetick)
    append_flag(argv, "--no-chart", flag_enabled(no_chart))

    try:
        from src.backtesting.cli import main as legacy_main

        exit_code = invoke_legacy_main(legacy_main, argv)
    except ModuleNotFoundError as exc:
        abort(
            f"回测命令缺少依赖: {exc.name}。请先执行 `pip install -r requirements.txt`，然后运行 `pip install -e .`。",
            exit_code=EXIT_CODE_FAILURE,
        )
    except FileNotFoundError as exc:
        missing_path = exc.filename or str(exc)
        abort(f"回测命令找不到文件: {missing_path}")
    except ValueError as exc:
        abort(str(exc))
    except Exception as exc:
        abort(f"回测命令执行失败: {exc}", exit_code=EXIT_CODE_FAILURE)

    if exit_code:
        raise typer.Exit(code=exit_code)
