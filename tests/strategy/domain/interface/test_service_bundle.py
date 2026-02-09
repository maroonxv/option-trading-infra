"""
Unit Tests for ServiceBundle Data Class

Tests the completeness and correctness of ServiceBundle fields.

**Validates: Requirements 5.2**
"""
import pytest
from dataclasses import fields
from typing import Optional
from unittest.mock import Mock

from src.strategy.domain.interface import (
    ServiceBundle,
    IIndicatorService,
    ISignalService,
    IPositionSizingService,
)
from src.strategy.domain.domain_service.future_selection_service import BaseFutureSelector
from src.strategy.domain.domain_service.option_selector_service import OptionSelectorService
from src.strategy.domain.entity.target_instrument import TargetInstrument


# Mock implementations for testing
class MockIndicatorService(IIndicatorService):
    def calculate_bar(self, instrument: TargetInstrument, bar: dict) -> None:
        pass


class MockSignalService(ISignalService):
    def check_open_signal(self, instrument: TargetInstrument) -> Optional[str]:
        return None
    
    def check_close_signal(
        self, 
        instrument: TargetInstrument, 
        position
    ) -> Optional[str]:
        return None


class MockPositionSizingService(IPositionSizingService):
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


class TestServiceBundleFieldCompleteness:
    """Test that ServiceBundle has all required fields"""
    
    def test_has_all_required_fields(self):
        """Test that ServiceBundle contains all 5 required service fields"""
        
        # Get all fields from the dataclass
        bundle_fields = {f.name for f in fields(ServiceBundle)}
        
        # Expected fields based on design document
        expected_fields = {
            'indicator_service',
            'signal_service',
            'position_sizing_service',
            'future_selection_service',
            'option_selector_service'
        }
        
        # Verify all expected fields are present
        assert bundle_fields == expected_fields, \
            f"Missing fields: {expected_fields - bundle_fields}, " \
            f"Extra fields: {bundle_fields - expected_fields}"
    
    def test_field_count(self):
        """Test that ServiceBundle has exactly 5 fields"""
        
        bundle_fields = fields(ServiceBundle)
        assert len(bundle_fields) == 5, \
            f"Expected 5 fields, but found {len(bundle_fields)}"
    
    def test_field_names_match_design(self):
        """Test that field names exactly match the design specification"""
        
        bundle_fields = [f.name for f in fields(ServiceBundle)]
        
        # Field names must match exactly as specified in design document
        assert 'indicator_service' in bundle_fields
        assert 'signal_service' in bundle_fields
        assert 'position_sizing_service' in bundle_fields
        assert 'future_selection_service' in bundle_fields
        assert 'option_selector_service' in bundle_fields


class TestServiceBundleInstantiation:
    """Test that ServiceBundle can be correctly instantiated"""
    
    def test_can_create_service_bundle(self):
        """Test that ServiceBundle can be instantiated with all services"""
        
        # Create mock services
        indicator_service = MockIndicatorService()
        signal_service = MockSignalService()
        position_sizing_service = MockPositionSizingService()
        future_selection_service = BaseFutureSelector()
        option_selector_service = OptionSelectorService()
        
        # Create ServiceBundle
        bundle = ServiceBundle(
            indicator_service=indicator_service,
            signal_service=signal_service,
            position_sizing_service=position_sizing_service,
            future_selection_service=future_selection_service,
            option_selector_service=option_selector_service
        )
        
        # Verify all fields are set correctly
        assert bundle.indicator_service is indicator_service
        assert bundle.signal_service is signal_service
        assert bundle.position_sizing_service is position_sizing_service
        assert bundle.future_selection_service is future_selection_service
        assert bundle.option_selector_service is option_selector_service
    
    def test_cannot_create_without_all_fields(self):
        """Test that ServiceBundle requires all fields to be provided"""
        
        # Missing fields should raise TypeError
        with pytest.raises(TypeError):
            ServiceBundle()
        
        with pytest.raises(TypeError):
            ServiceBundle(
                indicator_service=MockIndicatorService(),
                signal_service=MockSignalService()
                # Missing other fields
            )
    
    def test_fields_are_accessible(self):
        """Test that all fields can be accessed after instantiation"""
        
        bundle = ServiceBundle(
            indicator_service=MockIndicatorService(),
            signal_service=MockSignalService(),
            position_sizing_service=MockPositionSizingService(),
            future_selection_service=BaseFutureSelector(),
            option_selector_service=OptionSelectorService()
        )
        
        # All fields should be accessible
        assert hasattr(bundle, 'indicator_service')
        assert hasattr(bundle, 'signal_service')
        assert hasattr(bundle, 'position_sizing_service')
        assert hasattr(bundle, 'future_selection_service')
        assert hasattr(bundle, 'option_selector_service')
        
        # All fields should not be None
        assert bundle.indicator_service is not None
        assert bundle.signal_service is not None
        assert bundle.position_sizing_service is not None
        assert bundle.future_selection_service is not None
        assert bundle.option_selector_service is not None


class TestServiceBundleFieldTypes:
    """Test that ServiceBundle fields have correct types"""
    
    def test_indicator_service_field_type(self):
        """Test that indicator_service field accepts IIndicatorService"""
        
        bundle = ServiceBundle(
            indicator_service=MockIndicatorService(),
            signal_service=MockSignalService(),
            position_sizing_service=MockPositionSizingService(),
            future_selection_service=BaseFutureSelector(),
            option_selector_service=OptionSelectorService()
        )
        
        assert isinstance(bundle.indicator_service, IIndicatorService)
    
    def test_signal_service_field_type(self):
        """Test that signal_service field accepts ISignalService"""
        
        bundle = ServiceBundle(
            indicator_service=MockIndicatorService(),
            signal_service=MockSignalService(),
            position_sizing_service=MockPositionSizingService(),
            future_selection_service=BaseFutureSelector(),
            option_selector_service=OptionSelectorService()
        )
        
        assert isinstance(bundle.signal_service, ISignalService)
    
    def test_position_sizing_service_field_type(self):
        """Test that position_sizing_service field accepts IPositionSizingService"""
        
        bundle = ServiceBundle(
            indicator_service=MockIndicatorService(),
            signal_service=MockSignalService(),
            position_sizing_service=MockPositionSizingService(),
            future_selection_service=BaseFutureSelector(),
            option_selector_service=OptionSelectorService()
        )
        
        assert isinstance(bundle.position_sizing_service, IPositionSizingService)
    
    def test_future_selection_service_field_type(self):
        """Test that future_selection_service field accepts BaseFutureSelector"""
        
        bundle = ServiceBundle(
            indicator_service=MockIndicatorService(),
            signal_service=MockSignalService(),
            position_sizing_service=MockPositionSizingService(),
            future_selection_service=BaseFutureSelector(),
            option_selector_service=OptionSelectorService()
        )
        
        assert isinstance(bundle.future_selection_service, BaseFutureSelector)
    
    def test_option_selector_service_field_type(self):
        """Test that option_selector_service field accepts OptionSelectorService"""
        
        bundle = ServiceBundle(
            indicator_service=MockIndicatorService(),
            signal_service=MockSignalService(),
            position_sizing_service=MockPositionSizingService(),
            future_selection_service=BaseFutureSelector(),
            option_selector_service=OptionSelectorService()
        )
        
        assert isinstance(bundle.option_selector_service, OptionSelectorService)


class TestServiceBundleUsagePattern:
    """Test typical usage patterns of ServiceBundle"""
    
    def test_can_be_used_in_setup_services_pattern(self):
        """Test that ServiceBundle works in the setup_services pattern"""
        
        def setup_services() -> ServiceBundle:
            """Simulates GenericStrategyAdapter.setup_services() method"""
            return ServiceBundle(
                indicator_service=MockIndicatorService(),
                signal_service=MockSignalService(),
                position_sizing_service=MockPositionSizingService(),
                future_selection_service=BaseFutureSelector(),
                option_selector_service=OptionSelectorService()
            )
        
        # Should be able to call setup_services and get a valid bundle
        bundle = setup_services()
        
        assert isinstance(bundle, ServiceBundle)
        assert isinstance(bundle.indicator_service, IIndicatorService)
        assert isinstance(bundle.signal_service, ISignalService)
        assert isinstance(bundle.position_sizing_service, IPositionSizingService)
        assert isinstance(bundle.future_selection_service, BaseFutureSelector)
        assert isinstance(bundle.option_selector_service, OptionSelectorService)
    
    def test_can_unpack_services_from_bundle(self):
        """Test that services can be extracted from bundle for dependency injection"""
        
        bundle = ServiceBundle(
            indicator_service=MockIndicatorService(),
            signal_service=MockSignalService(),
            position_sizing_service=MockPositionSizingService(),
            future_selection_service=BaseFutureSelector(),
            option_selector_service=OptionSelectorService()
        )
        
        # Simulate extracting services for StrategyEngine initialization
        indicator_service = bundle.indicator_service
        signal_service = bundle.signal_service
        position_sizing_service = bundle.position_sizing_service
        future_selection_service = bundle.future_selection_service
        option_selector_service = bundle.option_selector_service
        
        # All services should be valid
        assert isinstance(indicator_service, IIndicatorService)
        assert isinstance(signal_service, ISignalService)
        assert isinstance(position_sizing_service, IPositionSizingService)
        assert isinstance(future_selection_service, BaseFutureSelector)
        assert isinstance(option_selector_service, OptionSelectorService)
