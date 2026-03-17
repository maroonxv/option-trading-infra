from __future__ import annotations

from typing import Any

from src.strategy.domain.value_object.market.option_chain import OptionChainSnapshot

from ..models import CapabilityContribution, OpenPipelineRoles


class _OptionChainProvider:
    def build(
        self,
        entry: Any,
        full_config: dict[str, Any],
        kernel: Any,
    ) -> CapabilityContribution:
        market_gateway = getattr(entry, "market_gateway", None)
        if market_gateway is None:
            return CapabilityContribution()

        def option_chain_loader(
            vt_symbol: str,
            instrument: Any,
            bar_data: dict[str, Any],
        ) -> OptionChainSnapshot | None:
            contracts = market_gateway.get_all_contracts()
            if not contracts:
                return None
            return OptionChainSnapshot.from_contracts(
                underlying_vt_symbol=vt_symbol,
                underlying_price=instrument.latest_close,
                contracts=contracts,
                get_tick=market_gateway.get_tick,
                as_of=bar_data["datetime"],
            )

        return CapabilityContribution(
            open_pipeline=OpenPipelineRoles(option_chain_loader=option_chain_loader)
        )


PROVIDER = _OptionChainProvider()
