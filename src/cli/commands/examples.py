"""示例浏览命令。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

from src.cli.common import abort, display_path, get_project_root


@dataclass(frozen=True)
class ExampleInfo:
    """示例元信息。"""

    name: str
    path: Path
    summary: str
    readme: str


def _extract_summary(readme: str) -> str:
    for raw_line in readme.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return "未提供额外说明。"


def _load_examples() -> list[ExampleInfo]:
    example_root = get_project_root() / "example"
    roots: list[Path] = []
    if example_root.exists():
        roots.append(example_root)

    strategy_root = get_project_root() / "src" / "strategies"
    if strategy_root.exists():
        roots.append(strategy_root)

    if not roots:
        return []

    items: list[ExampleInfo] = []
    seen_names: set[str] = set()
    for root in roots:
        for example_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            if example_dir.name in seen_names:
                continue
            seen_names.add(example_dir.name)
            readme_path = example_dir / "README.md"
            readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
            items.append(
                ExampleInfo(
                    name=example_dir.name,
                    path=example_dir,
                    summary=_extract_summary(readme),
                    readme=readme.strip(),
                )
            )
    return items


def command(
    name: Optional[str] = typer.Argument(None, help="示例名称；不传时列出全部示例。"),
) -> None:
    """列出内置示例，或查看某个示例的说明。"""
    examples = _load_examples()
    if not examples:
        abort("未找到任何示例目录。")

    if name is None:
        typer.echo("可用示例：")
        for item in examples:
            typer.echo(f"- {item.name}: {item.summary}")
        typer.echo("使用 `option-scaffold examples <name>` 查看详情。")
        return

    selected = next((item for item in examples if item.name == name), None)
    if selected is None:
        available_names = ", ".join(item.name for item in examples)
        abort(f"未找到示例 {name}。可用示例: {available_names}")

    typer.echo(f"示例: {selected.name}")
    typer.echo(f"路径: {display_path(selected.path)}")
    typer.echo(f"摘要: {selected.summary}")

    key_files = [
        selected.path / "strategy_contract.toml",
        selected.path / "indicator_service.py",
        selected.path / "signal_service.py",
        selected.path / "README.md",
    ]
    typer.echo("关键文件：")
    for file_path in key_files:
        if file_path.exists():
            typer.echo(f"- {display_path(file_path)}")

    if selected.readme:
        typer.echo("")
        typer.echo(selected.readme)
