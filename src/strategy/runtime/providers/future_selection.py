from __future__ import annotations

from datetime import date, datetime
from typing import Any

from src.strategy.infrastructure.parsing.contract_helper import ContractHelper
from src.strategy.domain.value_object.selection.selection import MarketData as SelectionMarketData

from ..models import CapabilityContribution, UniverseRoles


def _build_market_data(entry: Any, contracts: list[Any]) -> dict[str, SelectionMarketData]:
    market_gateway = getattr(entry, "market_gateway", None)
    if market_gateway is None:
        return {}

    data: dict[str, SelectionMarketData] = {}
    for contract in contracts:
        vt_symbol = getattr(contract, "vt_symbol", "")
        if not vt_symbol:
            continue

        tick = market_gateway.get_tick(vt_symbol)
        if tick is None:
            continue

        try:
            volume = float(getattr(tick, "volume", 0) or 0)
            open_interest = float(getattr(tick, "open_interest", 0) or 0)
        except (TypeError, ValueError):
            continue

        if volume != volume or open_interest != open_interest:
            continue

        data[vt_symbol] = SelectionMarketData(
            vt_symbol=vt_symbol,
            volume=int(volume),
            open_interest=open_interest,
        )
    return data


class _FutureSelectionProvider:
    def build(
        self,
        entry: Any,
        full_config: dict[str, Any],
        kernel: Any,
    ) -> CapabilityContribution:
        service = getattr(entry, "future_selection_service", None)
        target_aggregate = getattr(entry, "target_aggregate", None)
        market_gateway = getattr(entry, "market_gateway", None)
        logger = getattr(entry, "logger", None)
        if service is None or target_aggregate is None or market_gateway is None:
            return CapabilityContribution()

        def initializer() -> None:
            for product in getattr(entry, "target_products", ()):
                existing = target_aggregate.get_active_contract(product)
                if existing:
                    continue

                try:
                    all_contracts = market_gateway.get_all_contracts()
                    product_contracts = [
                        contract
                        for contract in all_contracts
                        if ContractHelper.is_contract_of_product(contract, product)
                    ]
                    if not product_contracts:
                        if logger is not None:
                            logger.warning(f"鍝佺 {product} 鏈壘鍒板彲鐢ㄥ悎绾?")
                        continue

                    dominant = service.select_dominant_contract(
                        product_contracts,
                        date.today(),
                        market_data=_build_market_data(entry, product_contracts),
                        log_func=getattr(logger, "info", None),
                    )
                    if dominant:
                        vt_symbol = dominant.vt_symbol
                        target_aggregate.set_active_contract(product, vt_symbol)
                        target_aggregate.get_or_create_instrument(vt_symbol)
                        entry._subscribe_symbol(vt_symbol)
                        if logger is not None:
                            logger.info(f"鍝佺 {product} 涓诲姏鍚堢害: {vt_symbol}")
                except Exception as exc:
                    if logger is not None:
                        logger.error(f"鍝佺 {product} 涓诲姏鍚堢害鍒濆鍖栧け璐? {exc}")

        def rollover_checker(current_dt: datetime) -> bool:
            rollover_changed = False
            for product in getattr(entry, "target_products", ()):
                try:
                    current_vt = target_aggregate.get_active_contract(product)
                    if not current_vt:
                        continue

                    all_contracts = market_gateway.get_all_contracts()
                    product_contracts = [
                        contract
                        for contract in all_contracts
                        if ContractHelper.is_contract_of_product(contract, product)
                    ]
                    if not product_contracts:
                        continue

                    dominant = service.select_dominant_contract(
                        product_contracts,
                        current_dt.date(),
                        market_data=_build_market_data(entry, product_contracts),
                        log_func=getattr(logger, "info", None),
                    )
                    if dominant and dominant.vt_symbol != current_vt:
                        new_vt = dominant.vt_symbol
                        target_aggregate.set_active_contract(product, new_vt)
                        target_aggregate.get_or_create_instrument(new_vt)
                        entry._subscribe_symbol(new_vt)
                        rollover_changed = True
                        if logger is not None:
                            logger.info(f"鍝佺 {product} 鎹㈡湀: {current_vt} -> {new_vt}")
                except Exception as exc:
                    if logger is not None:
                        logger.error(f"鍝佺 {product} 鎹㈡湀妫€鏌ュけ璐? {exc}")

            return rollover_changed

        return CapabilityContribution(
            universe=UniverseRoles(
                initializer=initializer,
                rollover_checker=rollover_checker,
            )
        )


PROVIDER = _FutureSelectionProvider()
