import pytest
from datetime import date
from src.main.utils.contract_utils import ContractUtils
from src.strategy.domain.domain_service.future_selection_service import FutureSelectionService
from vnpy.trader.object import ContractData
from vnpy.trader.constant import Exchange, Product

def test_contract_utils_expiry():
    # 4 digits
    assert ContractUtils.get_expiry_from_symbol("rb2501") == date(2025, 1, 15)
    assert ContractUtils.get_expiry_from_symbol("m2505") == date(2025, 5, 15)
    
    # 3 digits (Zhengzhou)
    current_year = date.today().year
    decade = (current_year // 10) * 10
    assert ContractUtils.get_expiry_from_symbol("SA501") == date(decade + 5, 1, 15)
    
    # Invalid
    assert ContractUtils.get_expiry_from_symbol("rb") is None
    assert ContractUtils.get_expiry_from_symbol("123") is None # 123 -> year suffix 1, month 23 (Invalid month) -> None
    assert ContractUtils.get_expiry_from_symbol("rb2513") is None # Invalid month

def test_future_selection_service():
    service = FutureSelectionService()
    
    # Mock contracts
    c1 = ContractData(
        symbol="rb2501",
        exchange=Exchange.SHFE,
        name="rb2501",
        product=Product.FUTURES,
        size=10,
        pricetick=1.0,
        gateway_name="CTP"
    )
    c2 = ContractData(
        symbol="rb2505",
        exchange=Exchange.SHFE,
        name="rb2505",
        product=Product.FUTURES,
        size=10,
        pricetick=1.0,
        gateway_name="CTP"
    )
    contracts = [c1, c2]
    
    # Case 1: Current date is far from c1 expiry (2025-01-15)
    current_date = date(2024, 12, 1)
    selected = service.select_dominant_contract(contracts, current_date)
    assert selected.symbol == "rb2501"
    
    # Case 2: Current date is within 7 days of c1 expiry
    current_date = date(2025, 1, 10) # 5 days to expiry
    selected = service.select_dominant_contract(contracts, current_date)
    assert selected.symbol == "rb2505"
    
    # Case 3: Only one contract available, near expiry
    selected = service.select_dominant_contract([c1], current_date)
    assert selected.symbol == "rb2501"

if __name__ == "__main__":
    pytest.main([__file__])
