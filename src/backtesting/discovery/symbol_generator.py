"""
合约代码生成器

根据品种代码和时间范围生成标准 vt_symbol。
"""

from datetime import date
from typing import List

from src.backtesting.contract.exchange_resolver import ExchangeResolver


class SymbolGenerator:
    """合约代码生成器，根据品种代码和时间范围生成标准 vt_symbol。"""

    @classmethod
    def generate_for_range(
        cls,
        product_code: str,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
    ) -> List[str]:
        """
        生成指定时间范围内的所有 vt_symbol。

        如果 product_code 已包含交易所后缀（含 "."），直接返回该代码。
        郑商所品种使用三位数字格式（1位年份 + 2位月份，如 AP601），
        其他交易所使用四位数字格式（2位年份 + 2位月份，如 rb2601）。

        Args:
            product_code: 品种代码（如 "rb"）或完整 vt_symbol（如 "rb2505.SHFE"）
            start_year: 开始年份（如 2025）
            start_month: 开始月份（1-12）
            end_year: 结束年份（如 2026）
            end_month: 结束月份（1-12）

        Returns:
            vt_symbol 列表（如 ["rb2512.SHFE", "rb2601.SHFE"]）
        """
        # Req 2.4: 已包含交易所后缀时直接返回
        if "." in product_code:
            return [product_code]

        exchange = ExchangeResolver.resolve(product_code)
        is_czce = exchange == "CZCE"

        symbols: List[str] = []
        current_year = start_year
        current_month = start_month
        end_val = end_year * 100 + end_month

        while current_year * 100 + current_month <= end_val:
            month_str = f"{current_month:02d}"

            if is_czce:
                # 郑商所: 1位年份 + 2位月份（如 AP601）
                year_char = str(current_year)[-1]
                symbol_code = f"{product_code}{year_char}{month_str}"
            else:
                # 其他交易所: 2位年份 + 2位月份（如 rb2601）
                short_year = str(current_year)[-2:]
                symbol_code = f"{product_code}{short_year}{month_str}"

            symbols.append(f"{symbol_code}.{exchange}")

            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return symbols

    @classmethod
    def generate_recent(
        cls, product_code: str, months_ahead: int = 1
    ) -> List[str]:
        """
        生成近期合约代码（当前月到 N 个月后）。

        不使用硬编码开始日期，以当前月份作为起始。

        Args:
            product_code: 品种代码（如 "rb"）
            months_ahead: 向前延伸的月数，默认 1

        Returns:
            vt_symbol 列表
        """
        now = date.today()
        start_year = now.year
        start_month = now.month

        # 计算结束月份：当前月 + months_ahead
        total_months = now.year * 12 + now.month + months_ahead
        end_year = (total_months - 1) // 12
        end_month = (total_months - 1) % 12 + 1

        return cls.generate_for_range(
            product_code=product_code,
            start_year=start_year,
            start_month=start_month,
            end_year=end_year,
            end_month=end_month,
        )
