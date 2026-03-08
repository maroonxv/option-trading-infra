"""CLI 共享工具。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv
import typer

EXIT_CODE_FAILURE = 1
EXIT_CODE_VALIDATION = 2


@dataclass(frozen=True)
class CheckResult:
    """命令行检查结果。"""

    status: str
    title: str
    detail: str


def append_option(arguments: list[str], flag: str, value: Any | None) -> None:
    """向参数列表追加带值选项。"""
    if value is None:
        return
    arguments.extend([flag, str(value)])


def append_flag(arguments: list[str], flag: str, enabled: bool) -> None:
    """向参数列表追加布尔开关。"""
    if enabled:
        arguments.append(flag)


def flag_enabled(value: Any) -> bool:
    """兼容 Typer 在不同 Click 版本下的旗标取值。"""
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def invoke_legacy_main(
    entrypoint: Callable[[list[str] | None], int | None],
    argv: Sequence[str],
) -> int:
    """调用现有 CLI 入口，并将 ``SystemExit`` 统一转换为退出码。"""
    try:
        result = entrypoint(list(argv))
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1

    return 0 if result is None else int(result)


def get_project_root() -> Path:
    """返回仓库根目录。"""
    return Path(__file__).resolve().parents[2]


def resolve_project_path(path: str | Path) -> Path:
    """将相对路径解析为仓库根目录下的绝对路径。"""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return get_project_root() / candidate


def display_path(path: str | Path) -> str:
    """优先使用仓库相对路径展示文件位置。"""
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(get_project_root()))
    except Exception:
        return str(candidate)


def ensure_project_root_on_path() -> None:
    """确保仓库根目录可用于导入本地模块与示例包。"""
    project_root = str(get_project_root())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def load_project_dotenv() -> Path | None:
    """加载项目根目录下的 ``.env``，不存在时回退到默认搜索。"""
    env_path = get_project_root() / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        return env_path

    load_dotenv(override=False)
    return None


def echo_check(result: CheckResult) -> None:
    """输出单条检查结果。"""
    typer.echo(f"[{result.status}] {result.title}: {result.detail}")


def abort(message: str, *, exit_code: int = EXIT_CODE_VALIDATION) -> None:
    """输出错误并以指定退出码终止。"""
    typer.echo(f"错误: {message}", err=True)
    raise typer.Exit(code=exit_code)
