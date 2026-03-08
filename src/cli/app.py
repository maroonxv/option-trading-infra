"""统一 CLI 应用入口。"""

from __future__ import annotations

from pathlib import Path

import click
import typer.main as typer_main
import typer.testing as typer_testing

from src import __version__
from src.cli.commands.backtest import command as backtest_command
from src.cli.commands.create import command as create_command
from src.cli.commands.doctor import command as doctor_command
from src.cli.commands.examples import command as examples_command
from src.cli.commands.init import command as init_command
from src.cli.commands.run import LogLevel, RunMode, command as run_command
from src.cli.commands.validate import command as validate_command


def _version_option_callback(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    del param
    if not value or ctx.resilient_parsing:
        return

    click.echo(f"option-scaffold {__version__}")
    ctx.exit()


@click.group(name="option-scaffold", help="期权策略脚手架统一命令入口。", no_args_is_help=True)
@click.option(
    "--version",
    "-V",
    is_flag=True,
    expose_value=False,
    is_eager=True,
    callback=_version_option_callback,
    help="显示版本并退出。",
)
def app() -> None:
    """统一暴露初始化、运行、回测、校验与诊断命令。"""


@app.command("create", help="按需装配并生成整仓库级期权策略脚手架。")
@click.argument("name", required=False)
@click.option(
    "--destination",
    "-d",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("."),
    show_default=True,
    help="输出父目录，最终会生成到 <destination>/<name>/。",
)
@click.option(
    "--preset",
    type=click.Choice(["custom", "ema-cross", "iv-rank", "delta-neutral"], case_sensitive=False),
    default=None,
    help="策略预设。",
)
@click.option(
    "--with",
    "with_",
    multiple=True,
    type=click.Choice(["selection", "position-sizing", "pricing", "greeks-risk", "execution", "hedging", "monitoring", "observability"], case_sensitive=False),
    help="显式开启能力，可重复传入。",
)
@click.option(
    "--without",
    multiple=True,
    type=click.Choice(["selection", "position-sizing", "pricing", "greeks-risk", "execution", "hedging", "monitoring", "observability"], case_sensitive=False),
    help="显式关闭能力，可重复传入。",
)
@click.option(
    "--with-option",
    "with_option",
    multiple=True,
    type=click.Choice([
        "future-selection",
        "option-chain",
        "option-selector",
        "position-sizing",
        "pricing-engine",
        "greeks-calculator",
        "portfolio-risk",
        "smart-order-executor",
        "advanced-order-scheduler",
        "delta-hedging",
        "vega-hedging",
        "monitoring",
        "decision-observability",
    ], case_sensitive=False),
    help="显式开启二级子选项，可重复传入。",
)
@click.option(
    "--without-option",
    "without_option",
    multiple=True,
    type=click.Choice([
        "future-selection",
        "option-chain",
        "option-selector",
        "position-sizing",
        "pricing-engine",
        "greeks-calculator",
        "portfolio-risk",
        "smart-order-executor",
        "advanced-order-scheduler",
        "delta-hedging",
        "vega-hedging",
        "monitoring",
        "decision-observability",
    ], case_sensitive=False),
    help="显式关闭二级子选项，可重复传入。",
)
@click.option("--force", is_flag=True, help="跳过破坏性目录操作的二次确认。")
@click.option("--clear", is_flag=True, help="目标目录非空时先清空再生成。")
@click.option("--overwrite", is_flag=True, help="目标目录非空时仅覆盖冲突文件。")
@click.option("-y", "--default", "use_default", is_flag=True, help="跳过提问，使用默认预设与默认能力组合。")
@click.option("--no-interactive", is_flag=True, help="禁用交互模式，仅按显式 flags 执行。")
def create_click(
    name: str | None,
    destination: Path,
    preset: str | None,
    with_: tuple[str, ...],
    without: tuple[str, ...],
    with_option: tuple[str, ...],
    without_option: tuple[str, ...],
    force: bool,
    clear: bool,
    overwrite: bool,
    use_default: bool,
    no_interactive: bool,
) -> None:
    create_command(
        name=name,
        destination=destination,
        preset=preset,
        with_=tuple(with_),
        without=tuple(without),
        with_option=tuple(with_option),
        without_option=tuple(without_option),
        force="1" if force else "",
        clear="1" if clear else "",
        overwrite="1" if overwrite else "",
        use_default="1" if use_default else "",
        no_interactive="1" if no_interactive else "",
    )


@app.command("init", help="生成策略开发骨架。")
@click.argument("name")
@click.option(
    "--destination",
    "-d",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("example"),
    show_default=True,
    help="输出目录，默认写入根目录下的 example/。",
)
@click.option("--force", is_flag=True, help="目录已存在时允许覆盖文件。")
def init_click(name: str, destination: Path, force: bool) -> None:
    init_command(name=name, destination=destination, force="1" if force else "")


@app.command("run", help="运行策略主程序。")
@click.option(
    "--mode",
    type=click.Choice([member.value for member in RunMode], case_sensitive=True),
    default=RunMode.standalone.value,
    show_default=True,
    help="运行模式：standalone 或 daemon。",
)
@click.option(
    "--config",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("config/strategy_config.toml"),
    show_default=True,
    help="策略配置文件路径。",
)
@click.option(
    "--override-config",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="覆盖配置文件路径。",
)
@click.option(
    "--log-level",
    type=click.Choice([member.value for member in LogLevel], case_sensitive=True),
    default=LogLevel.info.value,
    show_default=True,
    help="日志级别。",
)
@click.option(
    "--log-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=Path("data/logs"),
    show_default=True,
    help="日志目录。",
)
@click.option("--no-ui", is_flag=True, help="无界面模式运行。")
@click.option("--paper", is_flag=True, help="启用模拟交易模式。")
def run_click(
    mode: str,
    config: Path,
    override_config: Path | None,
    log_level: str,
    log_dir: Path,
    no_ui: bool,
    paper: bool,
) -> None:
    run_command(
        mode=RunMode(mode),
        config=config,
        override_config=override_config,
        log_level=LogLevel(log_level),
        log_dir=log_dir,
        no_ui="1" if no_ui else "",
        paper="1" if paper else "",
    )


@app.command("backtest", help="运行组合策略回测。")
@click.option("--config", type=click.Path(path_type=Path, dir_okay=False), default=None, help="策略配置文件路径。")
@click.option("--start", default=None, help="开始日期，格式 YYYY-MM-DD。")
@click.option("--end", default=None, help="结束日期，格式 YYYY-MM-DD。")
@click.option("--capital", type=int, default=None, help="初始资金。")
@click.option("--rate", type=float, default=None, help="手续费率。")
@click.option("--slippage", type=float, default=None, help="滑点。")
@click.option("--size", type=int, default=None, help="合约乘数。")
@click.option("--pricetick", type=float, default=None, help="最小价格变动。")
@click.option("--no-chart", is_flag=True, help="不显示图表。")
def backtest_click(
    config: Path | None,
    start: str | None,
    end: str | None,
    capital: int | None,
    rate: float | None,
    slippage: float | None,
    size: int | None,
    pricetick: float | None,
    no_chart: bool,
) -> None:
    backtest_command(
        config=config,
        start=start,
        end=end,
        capital=capital,
        rate=rate,
        slippage=slippage,
        size=size,
        pricetick=pricetick,
        no_chart="1" if no_chart else "",
    )


@app.command("validate", help="校验策略配置、契约绑定与可选回测参数。")
@click.option(
    "--config",
    type=click.Path(path_type=Path, dir_okay=False),
    default=Path("config/strategy_config.toml"),
    show_default=True,
    help="策略配置文件路径。",
)
@click.option(
    "--override-config",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="可选的覆盖配置文件路径。",
)
@click.option("--start", default=None, help="可选的回测开始日期，格式 YYYY-MM-DD。")
@click.option("--end", default=None, help="可选的回测结束日期，格式 YYYY-MM-DD。")
@click.option("--capital", type=int, default=None, help="可选的回测初始资金覆盖值。")
@click.option("--rate", type=float, default=None, help="可选的回测手续费率覆盖值。")
@click.option("--slippage", type=float, default=None, help="可选的回测滑点覆盖值。")
@click.option("--size", type=int, default=None, help="可选的回测合约乘数覆盖值。")
@click.option("--pricetick", type=float, default=None, help="可选的回测最小价格变动覆盖值。")
@click.option("--no-chart", is_flag=True, help="按回测命令语义校验图表开关。")
def validate_click(
    config: Path,
    override_config: Path | None,
    start: str | None,
    end: str | None,
    capital: int | None,
    rate: float | None,
    slippage: float | None,
    size: int | None,
    pricetick: float | None,
    no_chart: bool,
) -> None:
    validate_command(
        config=config,
        override_config=override_config,
        start=start,
        end=end,
        capital=capital,
        rate=rate,
        slippage=slippage,
        size=size,
        pricetick=pricetick,
        no_chart="1" if no_chart else "",
    )


@app.command("doctor", help="诊断本地 CLI 环境、配置文件与运行依赖。")
@click.option("--strict", is_flag=True, help="将警告也视为失败。")
@click.option("--check-db", is_flag=True, help="额外尝试连接数据库并执行 SELECT 1。")
def doctor_click(strict: bool, check_db: bool) -> None:
    doctor_command(strict="1" if strict else "", check_db="1" if check_db else "")


@app.command("examples", help="列出内置示例，或查看某个示例的说明。")
@click.argument("name", required=False)
def examples_click(name: str | None) -> None:
    examples_command(name=name)


_original_get_command = typer_main.get_command


def _patched_get_command(target: object):
    if isinstance(target, click.Command):
        return target
    return _original_get_command(target)


typer_main.get_command = _patched_get_command
typer_testing._get_command = _patched_get_command


def main() -> None:
    """模块执行入口。"""
    app()


if __name__ == "__main__":
    main()
