from __future__ import annotations

from types import SimpleNamespace

from src.strategy.application.lifecycle_workflow import LifecycleWorkflow
from src.strategy.runtime.registry import CAPABILITY_REGISTRY


def _manifest(**overrides: bool) -> dict[str, bool]:
    manifest = {key: False for key in CAPABILITY_REGISTRY}
    manifest.update(overrides)
    return manifest


def test_on_init_builds_runtime_and_runs_init_hooks(monkeypatch) -> None:
    calls: list[str] = []
    runtime = SimpleNamespace(
        lifecycle=SimpleNamespace(init_hooks=[lambda: calls.append("init")])
    )
    service_cls = type("Service", (), {"__init__": lambda self, **kwargs: None})

    entry = SimpleNamespace(
        logger=SimpleNamespace(
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            error=lambda *a, **k: None,
        ),
        setting={
            "strategy_full_config": {
                "service_activation": _manifest(),
                "strategy_contracts": {},
                "observability": {},
            },
            "bar_window": 0,
        },
        strategy_name="demo",
        max_positions=5,
        strike_level=3,
        backtesting=True,
        warmup_days=1,
        history_repo=SimpleNamespace(),
        feishu_webhook="",
        vt_symbols=[],
        _init_subscription_management=lambda: None,
        _record_snapshot=lambda: None,
        load_bars=lambda days: None,
    )

    monkeypatch.setattr(
        "src.main.config.config_loader.ConfigLoader.load_target_products",
        lambda: ["IF"],
    )
    monkeypatch.setattr(
        "src.main.config.config_loader.ConfigLoader.import_from_string",
        lambda _: service_cls,
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_position_sizing_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_pricing_engine_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_future_selector_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_option_selector_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.bootstrap.database_factory.DatabaseFactory.get_instance",
        lambda: object(),
    )

    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.InstrumentManager",
        lambda: SimpleNamespace(get_all_active_contracts=lambda: []),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.PositionAggregate",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.CombinationAggregate",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyMarketDataGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyAccountGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyOrderGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyTradeExecutionGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.JsonSerializer",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.StateRepository",
        lambda **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.build_runtime",
        lambda *args, **kwargs: runtime,
        raising=False,
    )

    LifecycleWorkflow(entry).on_init()

    assert entry.runtime is runtime
    assert calls == ["init"]
