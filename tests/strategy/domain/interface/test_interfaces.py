"""
Unit Tests for SPI Interface Definitions

Tests that interfaces can be correctly inherited and implemented.

**Validates: Requirements 5.2**
"""
import pytest
from typing import Optional
from unittest.mock import Mock

from src.strategy.domain.interface import (
    IIndicatorService,
    ISignalService,
    IPositionSizingService,
)
from src.strategy.domain.entity.target_instrument import TargetInstrument


class TestIIndicatorServiceInheritance:
    """Test that IIndicatorService can be correctly inherited"""
    
    def test_can_inherit_indicator_service(self):
        """Test that IIndicatorService can be inherited and implemented"""
        
        class ConcreteIndicatorService(IIndicatorService):
            def calculate_bar(self, instrument: TargetInstrument, bar: dict) -> None:
                # Simple implementation for testing
                instrument.indicators['test'] = 'calculated'
        
        # Should be able to instantiate the concrete class
        service = ConcreteIndicatorService()
        assert isinstance(service, IIndicatorService)
        
        # Should be able to call the method
        instrument = TargetInstrument(vt_symbol="test.SHFE")
        service.calculate_bar(instrument, {})
        assert instrument.indicators['test'] == 'calculated'
    
    def test_cannot_instantiate_abstract_indicator_service(self):
        """Test that IIndicatorService cannot be instantiated directly"""
        
        with pytest.raises(TypeError):
            IIndicatorService()
    
    def test_must_implement_calculate_bar(self):
        """Test that subclass must implement calculate_bar method"""
        
        with pytest.raises(TypeError):
            class IncompleteIndicatorService(IIndicatorService):
                pass
            
            IncompleteIndicatorService()


class TestISignalServiceInheritance:
    """Test that ISignalService can be correctly inherited"""
    
    def test_can_inherit_signal_service(self):
        """Test that ISignalService can be inherited and implemented"""
        
        class ConcreteSignalService(ISignalService):
            def check_open_signal(self, instrument: TargetInstrument) -> Optional[str]:
                return "test_open_signal"
            
            def check_close_signal(
                self, 
                instrument: TargetInstrument, 
                position
            ) -> Optional[str]:
                return "test_close_signal"
        
        # Should be able to instantiate the concrete class
        service = ConcreteSignalService()
        assert isinstance(service, ISignalService)
        
        # Should be able to call the methods
        instrument = TargetInstrument(vt_symbol="test.SHFE")
        assert service.check_open_signal(instrument) == "test_open_signal"
        
        # Use a mock position object
        position = Mock()
        assert service.check_close_signal(instrument, position) == "test_close_signal"
    
    def test_cannot_instantiate_abstract_signal_service(self):
        """Test that ISignalService cannot be instantiated directly"""
        
        with pytest.raises(TypeError):
            ISignalService()
    
    def test_must_implement_both_methods(self):
        """Test that subclass must implement both check_open_signal and check_close_signal"""
        
        # Missing check_close_signal
        with pytest.raises(TypeError):
            class IncompleteSignalService1(ISignalService):
                def check_open_signal(self, instrument: TargetInstrument) -> Optional[str]:
                    return None
            
            IncompleteSignalService1()
        
        # Missing check_open_signal
        with pytest.raises(TypeError):
            class IncompleteSignalService2(ISignalService):
                def check_close_signal(
                    self, 
                    instrument: TargetInstrument, 
                    position
                ) -> Optional[str]:
                    return None
            
            IncompleteSignalService2()


class TestIPositionSizingServiceInheritance:
    """Test that IPositionSizingService can be correctly inherited"""
    
    def test_can_inherit_position_sizing_service(self):
        """Test that IPositionSizingService can be inherited and implemented"""
        
        class ConcretePositionSizingService(IPositionSizingService):
            def calculate_open_volume(
                self,
                desired_volume: int,
                instrument: TargetInstrument,
                account: dict
            ) -> int:
                return desired_volume
            
            def calculate_exit_volume(
                self,
                desired_volume: int,
                current_position
            ) -> int:
                return desired_volume
        
        # Should be able to instantiate the concrete class
        service = ConcretePositionSizingService()
        assert isinstance(service, IPositionSizingService)
        
        # Should be able to call the methods
        instrument = TargetInstrument(vt_symbol="test.SHFE")
        assert service.calculate_open_volume(10, instrument, {}) == 10
        
        # Use a mock position object
        position = Mock()
        assert service.calculate_exit_volume(5, position) == 5
    
    def test_cannot_instantiate_abstract_position_sizing_service(self):
        """Test that IPositionSizingService cannot be instantiated directly"""
        
        with pytest.raises(TypeError):
            IPositionSizingService()
    
    def test_must_implement_both_methods(self):
        """Test that subclass must implement both calculate methods"""
        
        # Missing calculate_exit_volume
        with pytest.raises(TypeError):
            class IncompletePositionSizingService1(IPositionSizingService):
                def calculate_open_volume(
                    self,
                    desired_volume: int,
                    instrument: TargetInstrument,
                    account: dict
                ) -> int:
                    return desired_volume
            
            IncompletePositionSizingService1()
        
        # Missing calculate_open_volume
        with pytest.raises(TypeError):
            class IncompletePositionSizingService2(IPositionSizingService):
                def calculate_exit_volume(
                    self,
                    desired_volume: int,
                    current_position
                ) -> int:
                    return desired_volume
            
            IncompletePositionSizingService2()


class TestInterfaceMethodSignatures:
    """Test that interface methods have correct signatures"""
    
    def test_indicator_service_signature(self):
        """Test IIndicatorService.calculate_bar signature"""
        
        class TestIndicatorService(IIndicatorService):
            def calculate_bar(self, instrument: TargetInstrument, bar: dict) -> None:
                pass
        
        service = TestIndicatorService()
        instrument = TargetInstrument(vt_symbol="test.SHFE")
        
        # Should accept correct parameters
        result = service.calculate_bar(instrument, {"close": 100.0})
        assert result is None  # Should return None
    
    def test_signal_service_signatures(self):
        """Test ISignalService method signatures"""
        
        class TestSignalService(ISignalService):
            def check_open_signal(self, instrument: TargetInstrument) -> Optional[str]:
                return "test_signal"
            
            def check_close_signal(
                self, 
                instrument: TargetInstrument, 
                position
            ) -> Optional[str]:
                return None
        
        service = TestSignalService()
        instrument = TargetInstrument(vt_symbol="test.SHFE")
        position = Mock()
        
        # Should accept correct parameters and return Optional[str]
        open_signal = service.check_open_signal(instrument)
        assert isinstance(open_signal, str) or open_signal is None
        
        close_signal = service.check_close_signal(instrument, position)
        assert isinstance(close_signal, str) or close_signal is None
    
    def test_position_sizing_service_signatures(self):
        """Test IPositionSizingService method signatures"""
        
        class TestPositionSizingService(IPositionSizingService):
            def calculate_open_volume(
                self,
                desired_volume: int,
                instrument: TargetInstrument,
                account: dict
            ) -> int:
                return 10
            
            def calculate_exit_volume(
                self,
                desired_volume: int,
                current_position
            ) -> int:
                return 5
        
        service = TestPositionSizingService()
        instrument = TargetInstrument(vt_symbol="test.SHFE")
        position = Mock()
        
        # Should accept correct parameters and return int
        open_volume = service.calculate_open_volume(10, instrument, {})
        assert isinstance(open_volume, int)
        
        exit_volume = service.calculate_exit_volume(5, position)
        assert isinstance(exit_volume, int)
