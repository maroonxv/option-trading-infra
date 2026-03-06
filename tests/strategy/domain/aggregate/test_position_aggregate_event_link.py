"""
PositionAggregate / CombinationAggregate 事件联动测试
"""
from datetime import datetime

from src.strategy.domain.aggregate.combination_aggregate import CombinationAggregate
from src.strategy.domain.aggregate.position_aggregate import PositionAggregate
from src.strategy.domain.entity.combination import Combination
from src.strategy.domain.event.event_types import (
    CombinationStatusChangedEvent,
    ManualCloseDetectedEvent,
    PositionClosedEvent,
)
from src.strategy.domain.value_object.combination import (
    CombinationStatus,
    CombinationType,
    Leg,
)


def _build_single_leg_combination(vt_symbol: str) -> Combination:
    return Combination(
        combination_id="combo-1",
        combination_type=CombinationType.CUSTOM,
        underlying_vt_symbol="m2509.DCE",
        legs=[
            Leg(
                vt_symbol=vt_symbol,
                option_type="call",
                strike_price=2800.0,
                expiry_date="20250901",
                direction="short",
                volume=1,
                open_price=120.0,
            )
        ],
        status=CombinationStatus.ACTIVE,
        create_time=datetime(2026, 1, 1, 9, 0, 0),
    )


def test_trade_close_emits_position_closed_event_once() -> None:
    aggregate = PositionAggregate()
    vt_symbol = "m2509-C-2800.DCE"
    aggregate.create_position(
        option_vt_symbol=vt_symbol,
        underlying_vt_symbol="m2509.DCE",
        signal="test-open",
        target_volume=1,
    )

    aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 1,
            "offset": "open",
            "price": 100.0,
            "datetime": datetime(2026, 1, 1, 9, 1, 0),
        }
    )
    aggregate.pop_domain_events()

    aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 1,
            "offset": "close",
            "price": 90.0,
            "datetime": datetime(2026, 1, 1, 10, 0, 0),
        }
    )
    events = aggregate.pop_domain_events()
    close_events = [event for event in events if isinstance(event, PositionClosedEvent)]
    assert len(close_events) == 1
    assert close_events[0].vt_symbol == vt_symbol
    assert close_events[0].signal == "test-open"

    aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 1,
            "offset": "close",
            "price": 85.0,
            "datetime": datetime(2026, 1, 1, 10, 1, 0),
        }
    )
    events = aggregate.pop_domain_events()
    assert all(not isinstance(event, PositionClosedEvent) for event in events)


def test_manual_full_close_emits_manual_and_position_closed_events() -> None:
    aggregate = PositionAggregate()
    vt_symbol = "m2509-P-2800.DCE"
    aggregate.create_position(
        option_vt_symbol=vt_symbol,
        underlying_vt_symbol="m2509.DCE",
        signal="test-open",
        target_volume=1,
    )
    aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 1,
            "offset": "open",
            "price": 95.0,
            "datetime": datetime(2026, 1, 1, 9, 2, 0),
        }
    )
    aggregate.pop_domain_events()

    aggregate.update_from_position({"vt_symbol": vt_symbol, "volume": 0})

    events = aggregate.pop_domain_events()
    manual_events = [event for event in events if isinstance(event, ManualCloseDetectedEvent)]
    close_events = [event for event in events if isinstance(event, PositionClosedEvent)]
    assert len(manual_events) == 1
    assert len(close_events) == 1
    assert close_events[0].vt_symbol == vt_symbol


def test_position_closed_event_can_drive_combination_sync() -> None:
    vt_symbol = "m2509-C-2900.DCE"
    position_aggregate = PositionAggregate()
    combination_aggregate = CombinationAggregate()
    combination_aggregate.register_combination(_build_single_leg_combination(vt_symbol))

    position_aggregate.create_position(
        option_vt_symbol=vt_symbol,
        underlying_vt_symbol="m2509.DCE",
        signal="test-open",
        target_volume=1,
    )
    position_aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 1,
            "offset": "open",
            "price": 100.0,
            "datetime": datetime(2026, 1, 1, 9, 3, 0),
        }
    )
    position_aggregate.pop_domain_events()

    position_aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 1,
            "offset": "close",
            "price": 80.0,
            "datetime": datetime(2026, 1, 1, 11, 0, 0),
        }
    )
    events = position_aggregate.pop_domain_events()

    closed_symbols = position_aggregate.get_closed_vt_symbols()
    for event in events:
        if isinstance(event, PositionClosedEvent):
            combination_aggregate.sync_combination_status(event.vt_symbol, closed_symbols)

    combination = combination_aggregate.get_combination("combo-1")
    assert combination is not None
    assert combination.status == CombinationStatus.CLOSED

    combination_events = combination_aggregate.pop_domain_events()
    assert any(
        isinstance(event, CombinationStatusChangedEvent) for event in combination_events
    )
