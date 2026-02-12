"""
SymbolGenerator 属性测试

Feature: backtesting-restructure
Property 1: 合约代码生成格式正确性
Validates: Requirements 2.1, 2.2, 2.3
"""

import re

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from src.backtesting.config import EXCHANGE_MAP
from src.backtesting.discovery.symbol_generator import SymbolGenerator

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# 从 EXCHANGE_MAP 中采样品种代码
_product_codes = st.sampled_from(list(EXCHANGE_MAP.keys()))

# 年份和月份范围
_years = st.integers(min_value=2020, max_value=2030)
_months = st.integers(min_value=1, max_value=12)


# ---------------------------------------------------------------------------
# Property 1: 合约代码生成格式正确性
# ---------------------------------------------------------------------------


class TestSymbolGeneratorFormat:
    """Property 1: 合约代码生成格式正确性

    *For any* 品种代码和有效的时间范围（start_year/start_month 到 end_year/end_month），
    SymbolGenerator 生成的 vt_symbol 列表应满足：
    - 列表长度等于时间范围内的月份数
    - 郑商所品种使用 1 位年份 + 2 位月份格式（如 AP601）
    - 其他交易所品种使用 2 位年份 + 2 位月份格式（如 rb2601）
    - 每个 symbol 以 ".交易所代码" 结尾

    **Validates: Requirements 2.1, 2.2, 2.3**
    """

    @given(
        product_code=_product_codes,
        start_year=_years,
        start_month=_months,
        end_year=_years,
        end_month=_months,
    )
    @settings(max_examples=200)
    def test_list_length_equals_month_count(
        self, product_code, start_year, start_month, end_year, end_month
    ):
        """生成的 vt_symbol 列表长度等于时间范围内的月份数。

        **Validates: Requirements 2.1**
        """
        assume(start_year * 12 + start_month <= end_year * 12 + end_month)

        result = SymbolGenerator.generate_for_range(
            product_code, start_year, start_month, end_year, end_month
        )

        expected_months = (end_year - start_year) * 12 + (end_month - start_month) + 1
        assert len(result) == expected_months, (
            f"product={product_code}, range={start_year}/{start_month}-{end_year}/{end_month}, "
            f"expected {expected_months} symbols, got {len(result)}"
        )

    @given(
        product_code=_product_codes.filter(lambda p: EXCHANGE_MAP[p] == "CZCE"),
        start_year=_years,
        start_month=_months,
        end_year=_years,
        end_month=_months,
    )
    @settings(max_examples=200)
    def test_czce_format_one_digit_year_two_digit_month(
        self, product_code, start_year, start_month, end_year, end_month
    ):
        """郑商所品种使用 1 位年份 + 2 位月份格式（如 AP601）。

        **Validates: Requirements 2.2**
        """
        assume(start_year * 12 + start_month <= end_year * 12 + end_month)

        result = SymbolGenerator.generate_for_range(
            product_code, start_year, start_month, end_year, end_month
        )

        # 郑商所格式: {product_code}{1位年份}{2位月份}.CZCE
        pattern = re.compile(rf"^{re.escape(product_code)}\d{{3}}\.CZCE$")
        for symbol in result:
            assert pattern.match(symbol), (
                f"CZCE symbol {symbol!r} does not match pattern "
                f"{product_code}XMM.CZCE (1-digit year + 2-digit month)"
            )

    @given(
        product_code=_product_codes.filter(lambda p: EXCHANGE_MAP[p] != "CZCE"),
        start_year=_years,
        start_month=_months,
        end_year=_years,
        end_month=_months,
    )
    @settings(max_examples=200)
    def test_non_czce_format_two_digit_year_two_digit_month(
        self, product_code, start_year, start_month, end_year, end_month
    ):
        """其他交易所品种使用 2 位年份 + 2 位月份格式（如 rb2601）。

        **Validates: Requirements 2.3**
        """
        assume(start_year * 12 + start_month <= end_year * 12 + end_month)

        exchange = EXCHANGE_MAP[product_code]
        result = SymbolGenerator.generate_for_range(
            product_code, start_year, start_month, end_year, end_month
        )

        # 非郑商所格式: {product_code}{2位年份}{2位月份}.{exchange}
        pattern = re.compile(
            rf"^{re.escape(product_code)}\d{{4}}\.{re.escape(exchange)}$"
        )
        for symbol in result:
            assert pattern.match(symbol), (
                f"Non-CZCE symbol {symbol!r} does not match pattern "
                f"{product_code}YYMM.{exchange} (2-digit year + 2-digit month)"
            )

    @given(
        product_code=_product_codes,
        start_year=_years,
        start_month=_months,
        end_year=_years,
        end_month=_months,
    )
    @settings(max_examples=200)
    def test_every_symbol_ends_with_exchange_suffix(
        self, product_code, start_year, start_month, end_year, end_month
    ):
        """每个 symbol 以 ".交易所代码" 结尾。

        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        assume(start_year * 12 + start_month <= end_year * 12 + end_month)

        exchange = EXCHANGE_MAP[product_code]
        result = SymbolGenerator.generate_for_range(
            product_code, start_year, start_month, end_year, end_month
        )

        for symbol in result:
            assert symbol.endswith(f".{exchange}"), (
                f"Symbol {symbol!r} does not end with .{exchange}"
            )
