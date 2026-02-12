"""
回测命令行入口

提供 argparse CLI，解析命令行参数并启动回测流程。
所有参数默认值为 None，由 BacktestConfig.from_args() 决定是否覆盖默认配置。
"""

import argparse
import sys
from pathlib import Path


def main() -> None:
    """CLI 入口：解析参数 → 构建配置 → 初始化数据库 → 运行回测。"""
    parser = argparse.ArgumentParser(description="运行组合策略回测")
    parser.add_argument("--config", type=str, default=None, help="策略配置文件路径")
    parser.add_argument("--start", type=str, default=None, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--capital", type=int, default=None, help="初始资金")
    parser.add_argument("--rate", type=float, default=None, help="手续费率")
    parser.add_argument("--slippage", type=float, default=None, help="滑点")
    parser.add_argument("--size", type=int, default=None, help="合约乘数")
    parser.add_argument("--pricetick", type=float, default=None, help="最小价格变动")
    parser.add_argument(
        "--no-chart", action="store_true", default=None, dest="no_chart",
        help="不显示图表",
    )

    args = parser.parse_args()

    # 1. 构建回测配置（CLI 参数非 None 时覆盖默认值）
    from src.backtesting.config import BacktestConfig

    config = BacktestConfig.from_args(args)

    # 2. 加载环境变量并初始化数据库
    from dotenv import load_dotenv

    load_dotenv()

    from src.main.bootstrap.database_factory import DatabaseFactory

    factory = DatabaseFactory.get_instance()
    factory.initialize(eager=True)

    # 3. 创建执行器并运行回测
    from src.backtesting.runner import BacktestRunner

    runner = BacktestRunner(config)
    runner.run()


if __name__ == "__main__":
    main()
