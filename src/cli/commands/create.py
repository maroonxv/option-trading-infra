"""整仓库脚手架创建命令。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import typer

from src.cli.common import EXIT_CODE_VALIDATION, abort, display_path, flag_enabled
from src.main.scaffold.models import CapabilityKey, CapabilityOptionKey, CreateOptions
from src.main.scaffold.project import create_project_scaffold


def _to_capabilities(values: Iterable[str]) -> tuple[CapabilityKey, ...]:
    return tuple(CapabilityKey(value) for value in values)


def _to_options(values: Iterable[str]) -> tuple[CapabilityOptionKey, ...]:
    return tuple(CapabilityOptionKey(value) for value in values)


def command(
    name: str | None = typer.Argument(None, help="项目名称；省略时在交互模式中询问。"),
    destination: Path = typer.Option(Path("."), "--destination", "-d", help="输出父目录，最终会生成到 <destination>/<name>/。"),
    preset: str | None = typer.Option(None, "--preset", help="策略预设，例如 custom、ema-cross、iv-rank、delta-neutral。"),
    with_: tuple[str, ...] = typer.Option((), "--with", help="显式开启的能力，可重复传入。"),
    without: tuple[str, ...] = typer.Option((), "--without", help="显式关闭的能力，可重复传入。"),
    with_option: tuple[str, ...] = typer.Option((), "--with-option", help="显式开启的二级子选项，可重复传入。"),
    without_option: tuple[str, ...] = typer.Option((), "--without-option", help="显式关闭的二级子选项，可重复传入。"),
    force: str = typer.Option("", "--force", flag_value="1", show_default=False, help="跳过破坏性目录操作的二次确认。"),
    clear: str = typer.Option("", "--clear", flag_value="1", show_default=False, help="目标目录非空时先清空再生成。"),
    overwrite: str = typer.Option("", "--overwrite", flag_value="1", show_default=False, help="目标目录非空时保留目录，仅覆盖冲突文件。"),
    use_default: str = typer.Option("", "-y", "--default", flag_value="1", show_default=False, help="跳过提问，使用默认预设与默认能力组合。"),
    no_interactive: str = typer.Option("", "--no-interactive", flag_value="1", show_default=False, help="禁用交互模式，仅按显式 flags 执行。"),
) -> None:
    """按需装配并生成整仓库级期权策略脚手架。"""
    try:
        plan = create_project_scaffold(
            CreateOptions(
                name=name,
                destination=destination,
                preset=preset,
                include_capabilities=_to_capabilities(with_),
                exclude_capabilities=_to_capabilities(without),
                include_options=_to_options(with_option),
                exclude_options=_to_options(without_option),
                use_default=flag_enabled(use_default),
                no_interactive=flag_enabled(no_interactive),
                force=flag_enabled(force),
                clear=flag_enabled(clear),
                overwrite=flag_enabled(overwrite),
            )
        )
    except (FileExistsError, ValueError) as exc:
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    typer.echo(f"已生成项目工作区: {display_path(plan.project_root)}")
    typer.echo(f"策略包路径: src/strategies/{plan.strategy_slug}")
    typer.echo(f"主配置文件: {display_path(plan.project_root / 'config' / 'strategy_config.toml')}")
