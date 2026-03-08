"""策略脚手架生成器。"""

from __future__ import annotations

from pathlib import Path
import re
from textwrap import dedent


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", (name or "strategy").strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug.lower() or "strategy"


def _classify(name: str) -> str:
    slug = _slugify(name)
    return "".join(part.capitalize() for part in slug.split("_")) or "Strategy"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8")


def scaffold_strategy(name: str, destination: Path, force: bool = False) -> Path:
    """生成一套新的策略开发模板目录。"""
    slug = _slugify(name)
    class_prefix = _classify(name)
    package_dir = destination / slug
    if package_dir.exists() and not force:
        raise FileExistsError(f"目录已存在: {package_dir}")

    package_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = package_dir / "tests"

    _write(package_dir / "__init__.py", "")
    _write(tests_dir / "__init__.py", "")

    _write(
        package_dir / "indicator_service.py",
        f'''
        from __future__ import annotations

        from typing import Optional, TYPE_CHECKING

        from src.strategy.domain.domain_service.signal.indicator_service import IIndicatorService
        from src.strategy.domain.value_object.signal import IndicatorComputationResult, IndicatorContext

        if TYPE_CHECKING:
            from src.strategy.domain.entity.target_instrument import TargetInstrument


        class {class_prefix}IndicatorService(IIndicatorService):
            def __init__(self, **kwargs):
                self.config = dict(kwargs)

            def calculate_bar(
                self,
                instrument: "TargetInstrument",
                bar: dict,
                context: Optional[IndicatorContext] = None,
            ) -> IndicatorComputationResult:
                instrument.indicators.setdefault("template", {{}})
                instrument.indicators["template"].update({{
                    "last_close": float(bar.get("close", 0) or 0),
                    "bar_dt": bar.get("datetime"),
                }})
                return IndicatorComputationResult(
                    indicator_key="template",
                    updated_indicator_keys=["template"],
                    values=dict(instrument.indicators["template"]),
                    summary="模板指标已更新",
                )
        ''',
    )
    _write(
        package_dir / "signal_service.py",
        f'''
        from __future__ import annotations

        from typing import Optional, TYPE_CHECKING

        from src.strategy.domain.domain_service.signal.signal_service import ISignalService
        from src.strategy.domain.value_object.signal import (
            OptionSelectionPreference,
            SignalContext,
            SignalDecision,
        )

        if TYPE_CHECKING:
            from src.strategy.domain.entity.position import Position
            from src.strategy.domain.entity.target_instrument import TargetInstrument


        class {class_prefix}SignalService(ISignalService):
            def __init__(self, option_type: str = "call", strike_level: int = 1, **kwargs):
                self.option_type = option_type
                self.strike_level = strike_level
                self.config = dict(kwargs)

            def check_open_signal(
                self,
                instrument: "TargetInstrument",
                context: Optional[SignalContext] = None,
            ) -> Optional[SignalDecision]:
                return None

            def check_close_signal(
                self,
                instrument: "TargetInstrument",
                position: "Position",
                context: Optional[SignalContext] = None,
            ) -> Optional[SignalDecision]:
                return None
        ''',
    )
    _write(
        package_dir / "strategy_contract.toml",
        f'''
        [strategy_contracts]
        indicator_service = "example.{slug}.indicator_service:{class_prefix}IndicatorService"
        signal_service = "example.{slug}.signal_service:{class_prefix}SignalService"

        [strategy_contracts.indicator_kwargs]

        [strategy_contracts.signal_kwargs]
        option_type = "call"
        strike_level = 1

        [service_activation]
        future_selection = true
        option_chain = true
        option_selector = true
        position_sizing = false
        pricing_engine = false
        greeks_calculator = false
        portfolio_risk = false
        smart_order_executor = false
        monitoring = true
        decision_observability = true

        [observability]
        decision_journal_maxlen = 200
        emit_noop_decisions = false
        ''',
    )
    _write(
        tests_dir / "test_contracts.py",
        f'''
        from example.{slug}.indicator_service import {class_prefix}IndicatorService
        from example.{slug}.signal_service import {class_prefix}SignalService
        from src.strategy.domain.entity.target_instrument import TargetInstrument


        def test_indicator_service_updates_template_indicator() -> None:
            service = {class_prefix}IndicatorService()
            instrument = TargetInstrument(vt_symbol="IF2506.CFFEX")

            result = service.calculate_bar(
                instrument,
                {{"datetime": "2026-01-01 09:31:00", "close": 123.4}},
            )

            assert result.indicator_key == "template"
            assert instrument.indicators["template"]["last_close"] == 123.4


        def test_signal_service_defaults_to_no_signal() -> None:
            service = {class_prefix}SignalService()
            instrument = TargetInstrument(vt_symbol="IF2506.CFFEX")

            assert service.check_open_signal(instrument) is None
        ''',
    )
    _write(
        package_dir / "README.md",
        f'''
        # {slug}

        这是由脚手架命令生成的策略模板目录，包含：

        - `indicator_service.py`：指标契约实现模板
        - `signal_service.py`：信号契约实现模板
        - `strategy_contract.toml`：装配与可观测性模板配置
        - `tests/test_contracts.py`：最小契约测试

        典型用法：

        1. 在 `indicator_service.py` 中补指标计算。
        2. 在 `signal_service.py` 中补 `SignalDecision` 逻辑。
        3. 将 `strategy_contract.toml` 合并进实际策略配置。
        ''',
    )

    return package_dir
