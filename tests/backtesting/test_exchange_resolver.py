"""ExchangeResolver 单元测试"""

import pytest

from src.backtesting.config import EXCHANGE_MAP
from src.backtesting.contract.exchange_resolver import ExchangeResolver


class TestResolve:
    """ExchangeResolver.resolve() 测试"""

    def test_known_shfe_product(self):
        assert ExchangeResolver.resolve("rb") == "SHFE"

    def test_known_czce_product(self):
        assert ExchangeResolver.resolve("SA") == "CZCE"

    def test_known_dce_product(self):
        assert ExchangeResolver.resolve("m") == "DCE"

    def test_known_cffex_product(self):
        assert ExchangeResolver.resolve("IF") == "CFFEX"

    def test_known_ine_product(self):
        assert ExchangeResolver.resolve("sc") == "INE"

    def test_unknown_product_raises_value_error(self):
        with pytest.raises(ValueError, match="未知品种代码: UNKNOWN"):
            ExchangeResolver.resolve("UNKNOWN")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            ExchangeResolver.resolve("")


class TestIsCzce:
    """ExchangeResolver.is_czce() 测试"""

    def test_czce_product_returns_true(self):
        assert ExchangeResolver.is_czce("SA") is True
        assert ExchangeResolver.is_czce("AP") is True

    def test_non_czce_product_returns_false(self):
        assert ExchangeResolver.is_czce("rb") is False
        assert ExchangeResolver.is_czce("IF") is False

    def test_unknown_product_raises_value_error(self):
        with pytest.raises(ValueError):
            ExchangeResolver.is_czce("UNKNOWN")
