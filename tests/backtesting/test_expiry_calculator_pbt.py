"""
ExpiryCalculator 属性测试

Feature: backtesting-restructure, Property 4: 到期日计算交易所规则正确性
Validates: Requirements 4.1, 4.2, 4.3, 4.4
"""

from datetime import date

from hypothesis import given, settings
from hypothesis import strategies as st

from src.backtesting.config import EXCHANGE_MAP
from src.backtesting.contract.expiry_calculator import ExpiryCalculator

# 按交易所分组品种代码
_CFFEX_PRODUCTS = sorted(k for k, v in EXCHANGE_MAP.items() if v == "CFFEX")
_DCE_PRODUCTS = sorted(k for k, v in EXCHANGE_MAP.items() if v == "DCE")
_CZCE_PRODUCTS = sorted(k for k, v in EXCHANGE_MAP.items() if v == "CZCE")
_SHFE_PRODUCTS = sorted(k for k, v in EXCHANGE_MAP.items() if v == "SHFE")
_INE_PRODUCTS = sorted(k for k, v in EXCHANGE_MAP.items() if v == "INE")

_year_st = st.integers(min_value=2020, max_value=2030)
_month_st = st.integers(min_value=1, max_value=12)


class TestExpiryCalculatorProperty:
    """Property 4: 到期日计算交易所规则正确性

    *For any* 品种代码和有效的年/月组合，ExpiryCalculator.calculate() 返回的到期日应满足：
    - 中金所品种：到期日是合约月份的第三个周五（weekday == 4），可能因节假日顺延
    - 大商所品种：到期日在交割月前一个月内
    - 郑商所品种：到期日在交割月前一个月内
    - 上期所/能源中心品种：到期日在交割月前一个月内

    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    """

    @given(
        product_code=st.sampled_from(_CFFEX_PRODUCTS),
        year=_year_st,
        month=_month_st,
    )
    @settings(max_examples=100)
    def test_cffex_expiry_in_contract_month_and_weekday(
        self, product_code: str, year: int, month: int
    ):
        """中金所品种：到期日在合约月份内且为工作日。

        **Validates: Requirements 4.1**
        """
        expiry = ExpiryCalculator.calculate(product_code, year, month)

        assert isinstance(expiry, date)
        assert expiry.year == year, (
            f"{product_code}{year}{month:02d}: 到期日年份 {expiry.year} != {year}"
        )
        assert expiry.month == month, (
            f"{product_code}{year}{month:02d}: 到期日月份 {expiry.month} != {month}"
        )
        # 到期日应为工作日（周一到周五），节假日顺延后仍为工作日
        assert expiry.weekday() < 5, (
            f"{product_code}{year}{month:02d}: 到期日 {expiry} 是周末"
        )

    @given(
        product_code=st.sampled_from(_DCE_PRODUCTS),
        year=_year_st,
        month=_month_st,
    )
    @settings(max_examples=100)
    def test_dce_expiry_in_pre_delivery_month(
        self, product_code: str, year: int, month: int
    ):
        """大商所品种：到期日在交割月前一个月内。

        **Validates: Requirements 4.2**
        """
        expiry = ExpiryCalculator.calculate(product_code, year, month)

        assert isinstance(expiry, date)

        if month == 1:
            expected_year, expected_month = year - 1, 12
        else:
            expected_year, expected_month = year, month - 1

        assert expiry.year == expected_year, (
            f"{product_code}{year}{month:02d}: 到期日年份 {expiry.year} != {expected_year}"
        )
        assert expiry.month == expected_month, (
            f"{product_code}{year}{month:02d}: 到期日月份 {expiry.month} != {expected_month}"
        )

    @given(
        product_code=st.sampled_from(_CZCE_PRODUCTS),
        year=_year_st,
        month=_month_st,
    )
    @settings(max_examples=100)
    def test_czce_expiry_in_pre_delivery_month(
        self, product_code: str, year: int, month: int
    ):
        """郑商所品种：到期日在交割月前一个月内。

        **Validates: Requirements 4.3**
        """
        expiry = ExpiryCalculator.calculate(product_code, year, month)

        assert isinstance(expiry, date)

        if month == 1:
            expected_year, expected_month = year - 1, 12
        else:
            expected_year, expected_month = year, month - 1

        assert expiry.year == expected_year, (
            f"{product_code}{year}{month:02d}: 到期日年份 {expiry.year} != {expected_year}"
        )
        assert expiry.month == expected_month, (
            f"{product_code}{year}{month:02d}: 到期日月份 {expiry.month} != {expected_month}"
        )

    @given(
        product_code=st.sampled_from(_SHFE_PRODUCTS + _INE_PRODUCTS),
        year=_year_st,
        month=_month_st,
    )
    @settings(max_examples=100)
    def test_shfe_ine_expiry_in_pre_delivery_month(
        self, product_code: str, year: int, month: int
    ):
        """上期所/能源中心品种：到期日在交割月前一个月内。

        **Validates: Requirements 4.4**
        """
        expiry = ExpiryCalculator.calculate(product_code, year, month)

        assert isinstance(expiry, date)

        if month == 1:
            expected_year, expected_month = year - 1, 12
        else:
            expected_year, expected_month = year, month - 1

        assert expiry.year == expected_year, (
            f"{product_code}{year}{month:02d}: 到期日年份 {expiry.year} != {expected_year}"
        )
        assert expiry.month == expected_month, (
            f"{product_code}{year}{month:02d}: 到期日月份 {expiry.month} != {expected_month}"
        )
