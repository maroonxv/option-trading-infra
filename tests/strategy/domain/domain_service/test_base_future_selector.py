import pytest
from hypothesis import given, strategies as st
from datetime import date
from typing import List
from vnpy.trader.object import ContractData, Exchange, Product

from src.strategy.domain.domain_service.selection.future_selection_service import BaseFutureSelector

# Helper to create dummy ContractData
def create_contract(symbol: str) -> ContractData:
    return ContractData(
        symbol=symbol,
        exchange=Exchange.SHFE,
        name=symbol,
        product=Product.FUTURES,
        size=10,
        pricetick=1.0,
        gateway_name="test"
    )

class TestBaseFutureSelector:
    
    @pytest.fixture
    def selector(self):
        return BaseFutureSelector()
    
    def test_select_dominant_contract_empty(self, selector):
        assert selector.select_dominant_contract([], date.today()) is None
        
    def test_select_dominant_contract_basic(self, selector):
        contracts = [create_contract("rb2505"), create_contract("rb2501")]
        # rb2501 comes before rb2505 alphabetically
        selected = selector.select_dominant_contract(contracts, date.today())
        assert selected.symbol == "rb2501"

    def test_filter_by_maturity_current(self, selector):
        contracts = [create_contract("rb2505"), create_contract("rb2501")]
        filtered = selector.filter_by_maturity(contracts, date.today(), mode="current_month")
        assert len(filtered) == 1
        assert filtered[0].symbol == "rb2501"
        
    def test_filter_by_maturity_next(self, selector):
        contracts = [create_contract("rb2505"), create_contract("rb2501")]
        filtered = selector.filter_by_maturity(contracts, date.today(), mode="next_month")
        assert len(filtered) == 1
        assert filtered[0].symbol == "rb2505"
        
    def test_filter_by_maturity_next_empty(self, selector):
        contracts = [create_contract("rb2501")]
        filtered = selector.filter_by_maturity(contracts, date.today(), mode="next_month")
        assert len(filtered) == 0

    @given(st.lists(st.text(min_size=1, max_size=10), min_size=1))
    def test_property_select_dominant_always_first_sorted(self, symbols):
        selector = BaseFutureSelector()
        contracts = [create_contract(s) for s in symbols]
        
        selected = selector.select_dominant_contract(contracts, date.today())
        
        sorted_contracts = sorted(contracts, key=lambda c: c.symbol)
        assert selected.symbol == sorted_contracts[0].symbol
