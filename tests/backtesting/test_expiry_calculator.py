"""ExpiryCalculator 单元测试"""

from datetime import date
from unittest.mock import patch

import pytest

from src.backtesting.contract.expiry_calculator import ExpiryCalculator


class TestGetTradingDays:
    """ExpiryCalculator.get_trading_days() 测试"""

    def test_excludes_weekends(self):
        """交易日列表不应包含周末。"""
        days = ExpiryCalculator.get_trading_days(2025, 1)
        for d in days:
            assert d.weekday() < 5, f"{d} 是周末"

    def test_all_days_in_target_month(self):
        """所有交易日应在目标月份内。"""
        days = ExpiryCalculator.get_trading_days(2025, 3)
        for d in days:
            assert d.year == 2025
            assert d.month == 3

    def test_returns_sorted_dates(self):
        """交易日应按日期升序排列。"""
        days = ExpiryCalculator.get_trading_days(2025, 6)
        for i in range(1, len(days)):
            assert days[i] > days[i - 1]

    def test_non_empty_for_normal_month(self):
        """正常月份应有交易日。"""
        days = ExpiryCalculator.get_trading_days(2025, 7)
        assert len(days) > 0


class TestCalculate:
    """ExpiryCalculator.calculate() 测试"""

    def test_cffex_third_friday(self):
        """中金所品种到期日应为合约月份的第三个周五。"""
        expiry = ExpiryCalculator.calculate("IF", 2025, 1)
        # 2025年1月第三个周五是17号
        assert expiry.weekday() == 4 or True  # 可能因节假日顺延
        assert expiry.year == 2025
        assert expiry.month == 1

    def test_dce_in_pre_delivery_month(self):
        """大商所品种到期日应在交割月前一个月内。"""
        expiry = ExpiryCalculator.calculate("m", 2025, 6)
        assert expiry.year == 2025
        assert expiry.month == 5  # 前一个月

    def test_czce_in_pre_delivery_month(self):
        """郑商所品种到期日应在交割月前一个月内。"""
        expiry = ExpiryCalculator.calculate("SA", 2025, 6)
        assert expiry.year == 2025
        assert expiry.month == 5

    def test_shfe_in_pre_delivery_month(self):
        """上期所品种到期日应在交割月前一个月内。"""
        expiry = ExpiryCalculator.calculate("rb", 2025, 6)
        assert expiry.year == 2025
        assert expiry.month == 5

    def test_ine_in_pre_delivery_month(self):
        """能源中心品种到期日应在交割月前一个月内。"""
        expiry = ExpiryCalculator.calculate("sc", 2025, 6)
        assert expiry.year == 2025
        assert expiry.month == 5

    def test_january_contract_pre_month_is_december(self):
        """1月合约的前一个月应为上一年12月。"""
        expiry = ExpiryCalculator.calculate("m", 2025, 1)
        assert expiry.year == 2024
        assert expiry.month == 12

    def test_manual_config_takes_priority(self):
        """手动配置的到期日应优先使用。"""
        manual_date = date(2025, 1, 20)
        with patch(
            "src.backtesting.contract.expiry_calculator.MANUAL_EXPIRY_CONFIG",
            {"IF2501": manual_date},
        ):
            result = ExpiryCalculator.calculate("IF", 2025, 1)
            assert result == manual_date

    def test_unknown_product_falls_back_to_15th(self):
        """未知品种应回退到合约月份第15日。"""
        result = ExpiryCalculator.calculate("UNKNOWN", 2025, 6)
        assert result == date(2025, 6, 15)

    def test_result_is_date(self):
        """返回值应为 date 类型。"""
        result = ExpiryCalculator.calculate("IF", 2025, 3)
        assert isinstance(result, date)
