import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
import pandas as pd

from src.strategy.application.volatility_trade import VolatilityTrade
from src.strategy.domain.aggregate.position_aggregate import PositionAggregate
from src.strategy.domain.value_object.signal_type import SignalType
from src.strategy.domain.value_object.order_instruction import OrderInstruction, Direction, Offset
from src.strategy.infrastructure.utils.contract_helper import ContractHelper

class TestVolatilityTradeLimits:
    
    @pytest.fixture
    def strategy_context(self):
        ctx = Mock()
        ctx.strategy_name = "TestStrategy"
        ctx.logger = Mock()
        ctx.backtesting = False
        return ctx
        
    @pytest.fixture
    def trade(self, strategy_context):
        # Create VolatilityTrade with mocked dependencies
        trade = VolatilityTrade(strategy_context, target_products=["IF"])
        
        # Mock dependencies
        trade.market_gateway = Mock()
        trade.account_gateway = Mock()
        trade.exec_gateway = Mock()
        trade.target_aggregate = Mock()
        
        # Use REAL PositionAggregate to test state changes
        trade.position_aggregate = PositionAggregate()
        
        trade.option_selector_service = Mock()
        trade.position_sizing_service = Mock()
        trade.logger = Mock()
        
        return trade
        
    def test_daily_reset(self, trade):
        """Test counters reset on new day"""
        # Set initial state in aggregate
        trade.position_aggregate._global_daily_open_count = 10
        trade.position_aggregate._daily_open_count_map = {"IF2312-C-4000": 2}
        trade.position_aggregate._last_trading_date = date(2023, 1, 1)
        
        # Mock datetime.now() or _get_current_date
        with patch.object(trade, '_get_current_date', return_value=date(2023, 1, 2)):
            
            # This triggers reset logic (early return because instrument lookup mocked to None) 
            trade.target_aggregate.get_instrument.return_value = None 
            trade._check_and_execute_open("IF2312")
            
            assert trade.position_aggregate.get_global_daily_open_volume() == 0
            assert trade.position_aggregate.get_daily_open_volume("IF2312-C-4000") == 0
            assert trade.position_aggregate._last_trading_date == date(2023, 1, 2)

    def test_contract_limit_check_flow(self, trade):
        """
        Test that limit values are correctly retrieved from aggregate 
        and passed to position sizing service.
        """
        # Set state
        trade.position_aggregate._global_daily_open_count = 5
        trade.position_aggregate._daily_open_count_map = {"IF2312-C-4000": 2}
        trade.position_aggregate._last_trading_date = datetime.now().date()
        
        # Setup mocks
        instrument = Mock()
        trade.target_aggregate.get_instrument.return_value = instrument
        
        with patch('src.strategy.application.volatility_trade.SignalService') as mock_signal_service, \
             patch('src.strategy.infrastructure.utils.contract_helper.ContractHelper') as mock_helper:
            
            mock_signal_service.check_open_signal.return_value = SignalType.SELL_CALL_DIVERGENCE_CONFIRM
            
            # Mock option selection
            option_contract = Mock(vt_symbol="IF2312-C-4000", bid_price=10.0, ask_price=11.0)
            trade._select_option = Mock(return_value=option_contract)
            
            # Mock liquidity check pass
            trade.option_selector_service.check_liquidity.return_value = True
            
            # Set return value to None to avoid further execution logic in this test
            trade.position_sizing_service.make_open_decision.return_value = None

            trade._check_and_execute_open("IF2312")
            
            # Verify sizing service called with correct counts
            trade.position_sizing_service.make_open_decision.assert_called()
            call_args = trade.position_sizing_service.make_open_decision.call_args
            
            # current_daily_open_count (Global)
            assert call_args.kwargs['current_daily_open_count'] == 5
            # current_contract_open_count (Contract specific)
            assert call_args.kwargs['current_contract_open_count'] == 2

    def test_liquidity_check_fail(self, trade):
        """Test liquidity check blocks opening"""
        instrument = Mock()
        trade.target_aggregate.get_instrument.return_value = instrument
        
        with patch('src.strategy.application.volatility_trade.SignalService') as mock_signal_service:
            mock_signal_service.check_open_signal.return_value = SignalType.SELL_CALL_DIVERGENCE_CONFIRM
            
            option_contract = Mock(vt_symbol="IF2312-C-4000")
            trade._select_option = Mock(return_value=option_contract)
            
            # Liquidity check returns False
            trade.option_selector_service.check_liquidity.return_value = False
            
            trade._check_and_execute_open("IF2312")
            
            # Should check liquidity
            trade.option_selector_service.check_liquidity.assert_called()
            
            # Should NOT call sizing service
            trade.position_sizing_service.make_open_decision.assert_not_called()

    def test_double_order_execution_and_state_update(self, trade):
        """Test successful double order execution and subsequent state update via trade update"""
        instrument = Mock()
        trade.target_aggregate.get_instrument.return_value = instrument
        
        with patch('src.strategy.application.volatility_trade.SignalService') as mock_signal_service:
            mock_signal_service.check_open_signal.return_value = SignalType.SELL_CALL_DIVERGENCE_CONFIRM
            
            # Option Contract
            option_contract = Mock()
            option_contract.vt_symbol = "IF2312-C-4000"
            option_contract.bid_price = 10.0
            option_contract.ask_price = 12.0
            trade._select_option = Mock(return_value=option_contract)
            
            # Liquidity pass
            trade.option_selector_service.check_liquidity.return_value = True
            
            # Sizing returns instruction (1 lot)
            instruction = OrderInstruction(
                vt_symbol="IF2312-C-4000",
                direction=Direction.SHORT,
                offset=Offset.OPEN,
                volume=1,
                price=10.0,
                signal_type=SignalType.SELL_CALL_DIVERGENCE_CONFIRM.value
            )
            trade.position_sizing_service.make_open_decision.return_value = instruction
            
            # Exec gateway returns mock order ids
            trade.exec_gateway.send_order.side_effect = [["1"], ["2"]]
            
            trade._check_and_execute_open("IF2312")
            
            # Verify Exec Gateway called TWICE
            assert trade.exec_gateway.send_order.call_count == 2
            
            # Simulate fills (limit counters update on actual trades)
            # Use handle_trade_update which calls position_aggregate.update_from_trade
            trade.handle_trade_update({
                "vt_symbol": "IF2312-C-4000",
                "offset": "open",
                "volume": 1,
                "price": 10.0,
                "datetime": datetime.now(),
            })
            trade.handle_trade_update({
                "vt_symbol": "IF2312-C-4000",
                "offset": "open",
                "volume": 1,
                "price": 12.0,
                "datetime": datetime.now(),
            })

            # Check aggregate state updated
            assert trade.position_aggregate.get_global_daily_open_volume() == 2
            assert trade.position_aggregate.get_daily_open_volume("IF2312-C-4000") == 2

            # Verify Position Created with volume 2
            # Check the position in the aggregate
            position = trade.position_aggregate.get_position("IF2312-C-4000")
            assert position is not None
            assert position.target_volume == 2
            assert position.volume == 2  # After fills
