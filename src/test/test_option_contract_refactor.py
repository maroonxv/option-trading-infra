
import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from src.strategy.domain.value_object.option_contract import OptionContract, OptionType
from src.strategy.domain.domain_service.option_selector_service import OptionSelectorService

def test_option_contract_import():
    print("Testing OptionContract import...")
    contract = OptionContract(
        vt_symbol="IO2312-C-4000.CFFEX",
        underlying_symbol="IF2312.CFFEX",
        option_type="call",
        strike_price=4000.0,
        expiry_date="2023-12-15",
        diff1=0.05,
        bid_price=120.0,
        bid_volume=10,
        ask_price=121.0,
        ask_volume=20,
        days_to_expiry=15
    )
    print(f"Successfully created OptionContract: {contract}")
    assert contract.vt_symbol == "IO2312-C-4000.CFFEX"
    assert contract.option_type == "call"

def test_option_selector_service_import():
    print("Testing OptionSelectorService import...")
    service = OptionSelectorService()
    print(f"Successfully created OptionSelectorService: {service}")
    assert hasattr(service, "select_target_option")

if __name__ == "__main__":
    try:
        test_option_contract_import()
        test_option_selector_service_import()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
