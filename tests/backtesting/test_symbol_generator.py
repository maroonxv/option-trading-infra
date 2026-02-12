"""SymbolGenerator 单元测试"""

from datetime import date
from unittest.mock import patch

import pytest

from src.backtesting.discovery.symbol_generator import SymbolGenerator


class TestGenerateForRange:
    """SymbolGenerator.generate_for_range() 测试"""

    def test_shfe_product_four_digit_format(self):
        """SHFE 品种使用 2位年份+2位月份 格式"""
        result = SymbolGenerator.generate_for_range("rb", 2025, 1, 2025, 3)
        assert result == ["rb2501.SHFE", "rb2502.SHFE", "rb2503.SHFE"]

    def test_czce_product_three_digit_format(self):
        """郑商所品种使用 1位年份+2位月份 格式"""
        result = SymbolGenerator.generate_for_range("SA", 2025, 10, 2025, 12)
        assert result == ["SA510.CZCE", "SA511.CZCE", "SA512.CZCE"]

    def test_dce_product(self):
        result = SymbolGenerator.generate_for_range("m", 2026, 1, 2026, 2)
        assert result == ["m2601.DCE", "m2602.DCE"]

    def test_cffex_product(self):
        result = SymbolGenerator.generate_for_range("IF", 2025, 6, 2025, 6)
        assert result == ["IF2506.CFFEX"]

    def test_ine_product(self):
        result = SymbolGenerator.generate_for_range("sc", 2025, 3, 2025, 4)
        assert result == ["sc2503.INE", "sc2504.INE"]

    def test_cross_year_boundary(self):
        """跨年边界"""
        result = SymbolGenerator.generate_for_range("rb", 2025, 11, 2026, 2)
        assert result == [
            "rb2511.SHFE", "rb2512.SHFE",
            "rb2601.SHFE", "rb2602.SHFE",
        ]

    def test_czce_cross_year(self):
        """郑商所跨年：年份末位变化"""
        result = SymbolGenerator.generate_for_range("AP", 2029, 12, 2030, 1)
        assert result == ["AP912.CZCE", "AP001.CZCE"]

    def test_single_month(self):
        result = SymbolGenerator.generate_for_range("rb", 2025, 5, 2025, 5)
        assert result == ["rb2505.SHFE"]

    def test_product_code_with_dot_returns_directly(self):
        """Req 2.4: 已包含交易所后缀时直接返回"""
        result = SymbolGenerator.generate_for_range("rb2505.SHFE", 2025, 1, 2025, 12)
        assert result == ["rb2505.SHFE"]

    def test_unknown_product_raises_value_error(self):
        with pytest.raises(ValueError):
            SymbolGenerator.generate_for_range("UNKNOWN", 2025, 1, 2025, 1)

    def test_empty_range(self):
        """结束早于开始时返回空列表"""
        result = SymbolGenerator.generate_for_range("rb", 2026, 1, 2025, 1)
        assert result == []


class TestGenerateRecent:
    """SymbolGenerator.generate_recent() 测试"""

    @patch("src.backtesting.discovery.symbol_generator.date")
    def test_default_months_ahead(self, mock_date):
        """默认 months_ahead=1，从当前月到下个月"""
        mock_date.today.return_value = date(2025, 6, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        result = SymbolGenerator.generate_recent("rb")
        assert result == ["rb2506.SHFE", "rb2507.SHFE"]

    @patch("src.backtesting.discovery.symbol_generator.date")
    def test_months_ahead_three(self, mock_date):
        mock_date.today.return_value = date(2025, 6, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        result = SymbolGenerator.generate_recent("rb", months_ahead=3)
        assert result == [
            "rb2506.SHFE", "rb2507.SHFE",
            "rb2508.SHFE", "rb2509.SHFE",
        ]

    @patch("src.backtesting.discovery.symbol_generator.date")
    def test_december_cross_year(self, mock_date):
        """12月时跨年"""
        mock_date.today.return_value = date(2025, 12, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        result = SymbolGenerator.generate_recent("rb", months_ahead=1)
        assert result == ["rb2512.SHFE", "rb2601.SHFE"]

    @patch("src.backtesting.discovery.symbol_generator.date")
    def test_no_hardcoded_start_date(self, mock_date):
        """确保不使用硬编码开始日期，始终从当前月开始"""
        mock_date.today.return_value = date(2030, 3, 10)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        result = SymbolGenerator.generate_recent("rb", months_ahead=0)
        assert result == ["rb3003.SHFE"]

    @patch("src.backtesting.discovery.symbol_generator.date")
    def test_czce_recent(self, mock_date):
        mock_date.today.return_value = date(2025, 6, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        result = SymbolGenerator.generate_recent("SA", months_ahead=1)
        assert result == ["SA506.CZCE", "SA507.CZCE"]
