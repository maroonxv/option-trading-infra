"""策略脚手架命令入口。"""

from __future__ import annotations

import argparse
from pathlib import Path

from .generator import scaffold_strategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成策略开发脚手架")
    parser.add_argument("--name", required=True, help="策略目录名，例如 ema_breakout")
    parser.add_argument(
        "--destination",
        default="example",
        help="输出目录，默认写入根目录下的 example/",
    )
    parser.add_argument("--force", action="store_true", help="目录已存在时允许覆盖文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_dir = Path(args.destination)
    created = scaffold_strategy(args.name, output_dir, force=args.force)
    print(f"已生成策略脚手架: {created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
