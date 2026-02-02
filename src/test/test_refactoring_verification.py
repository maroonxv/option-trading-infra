import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from src.strategy.application.volatility_trade import VolatilityTrade
from src.strategy.domain.value_object.macd_value import MACDValue
from src.strategy.domain.value_object.dullness_state import DullnessState
from src.strategy.domain.value_object.divergence_state import DivergenceState
from src.strategy.domain.value_object.td_value import TDValue
from src.strategy.domain.value_object.ema_state import EMAState
from src.strategy.domain.entity.target_instrument import TargetInstrument

def test_volatility_trade_refactoring():
    # Mock context
    mock_context = MagicMock()
    mock_context.strategy_name = "TestStrategy"
    
    # Mock services
    mock_indicator_service = MagicMock()
    
    # Initialize VolatilityTrade
    # We need to mock Gateway calls in __init__
    with patch("src.strategy.application.volatility_trade.VnpyMarketDataGateway"), \
         patch("src.strategy.application.volatility_trade.VnpyAccountGateway"), \
         patch("src.strategy.application.volatility_trade.VnpyTradeExecutionGateway"), \
         patch("src.strategy.application.volatility_trade.StrategyMonitor") as MockMonitor, \
         patch("src.strategy.application.volatility_trade.StateRepository"):
        
        vt = VolatilityTrade(
            strategy_context=mock_context,
            target_products=["rb"],
            indicator_service=mock_indicator_service
        )
        
        # Mock monitor to avoid DB operations
        vt.monitor = MockMonitor.return_value
        
        # Setup dummy indicator result
        mock_result = MagicMock()
        mock_result.is_complete = True
        mock_result.macd_value = MACDValue(dif=10.0, dea=5.0, macd_bar=5.0)
        mock_result.td_value = TDValue(td_count=1, td_setup=0, has_buy_8_9=False, has_sell_8_9=False)
        mock_result.ema_state = EMAState(fast_ema=100.0, slow_ema=90.0, trend_status="up")
        
        mock_indicator_service.calculate_all.return_value = mock_result
        
        # Mock SignalService static methods
        with patch("src.strategy.application.volatility_trade.SignalService") as MockSignalService:
            MockSignalService.check_dullness.return_value = DullnessState(is_top_active=True)
            MockSignalService.check_divergence.return_value = DivergenceState(is_top_confirmed=True)
            
            # Trigger update
            vt.handle_bar_update("rb2501.SHFE", {
                "datetime": "2023-01-01",
                "close_price": 100.0, # Note: key used in VolatilityTrade log is close_price, but update_bar might use others
                "open": 99.0,
                "high": 101.0,
                "low": 98.0,
                "close": 100.0,
                "volume": 1000
            })
            
            # Verify instrument state
            instrument = vt.target_aggregate.get_instrument("rb2501.SHFE")
            assert instrument is not None
            assert instrument.macd_value == mock_result.macd_value
            assert instrument.dullness_state.is_top_active is True
            assert instrument.divergence_state.is_top_confirmed is True
            
            # Verify MACD history was updated in instrument
            assert len(instrument.macd_history) == 1
            assert instrument.macd_history[0] == mock_result.macd_value
            
            # Verify record_snapshot uses aggregate
            # Since _record_snapshot is called in init, and also in handle_bars (not handle_bar_update)
            # Let's call _record_snapshot manually
            vt._record_snapshot()
            vt.monitor.record_snapshot.assert_called_with(
                target_aggregate=vt.target_aggregate,
                position_aggregate=vt.position_aggregate,
                strategy_context=mock_context
            )
            
            print("Verification successful!")

if __name__ == "__main__":
    try:
        test_volatility_trade_refactoring()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
