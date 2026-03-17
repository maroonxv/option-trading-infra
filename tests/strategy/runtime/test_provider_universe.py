from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.strategy.runtime.registry import CAPABILITY_REGISTRY


def _manifest(**overrides: bool) -> dict[str, bool]:
    manifest = {key: False for key in CAPABILITY_REGISTRY}
    manifest.update(overrides)
    return manifest


def test_future_selection_provider_contributes_initializer() -> None:
    from src.strategy.runtime.providers.future_selection import PROVIDER

    entry = SimpleNamespace(
        target_products=["IF"],
        target_aggregate=MagicMock(),
        future_selection_service=MagicMock(),
        market_gateway=MagicMock(get_all_contracts=lambda: []),
        logger=SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None, error=lambda *a, **k: None),
        _subscribe_symbol=lambda vt_symbol: None,
    )
    contribution = PROVIDER.build(
        entry,
        {"service_activation": _manifest(future_selection=True)},
        kernel=SimpleNamespace(),
    )

    assert contribution.universe.initializer is not None
    assert contribution.universe.rollover_checker is not None


def test_option_chain_provider_contributes_loader() -> None:
    from src.strategy.runtime.providers.option_chain import PROVIDER

    contract = SimpleNamespace(
        vt_symbol="IO2506-C-3800.CFFEX",
        option_type="CALL",
        option_underlying="IF2506",
        option_strike=3800,
        exchange=SimpleNamespace(value="CFFEX"),
        size=100,
        pricetick=0.2,
    )
    gateway = SimpleNamespace(
        get_all_contracts=lambda: [contract],
        get_tick=lambda vt_symbol: SimpleNamespace(
            vt_symbol=vt_symbol,
            bid_price_1=10.0,
            bid_volume_1=20,
            ask_price_1=10.2,
            ask_volume_1=20,
            last_price=10.1,
            volume=100,
            open_interest=500,
            datetime=datetime(2026, 1, 2, 10, 0, 0),
        ),
    )
    entry = SimpleNamespace(market_gateway=gateway, logger=MagicMock())
    contribution = PROVIDER.build(
        entry,
        {"service_activation": _manifest(option_chain=True)},
        kernel=SimpleNamespace(),
    )

    assert contribution.open_pipeline.option_chain_loader is not None
