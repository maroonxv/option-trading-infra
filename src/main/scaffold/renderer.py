"""整仓库脚手架渲染层。"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from textwrap import dedent

from .catalog import REPO_ROOT, capability_label, capability_option_label, get_capability_options
from .models import CapabilityKey, CapabilityOptionKey, DirectoryConflictPolicy, ScaffoldPlan

COPY_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    ".hypothesis",
    ".venv",
    ".mypy_cache",
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).lstrip("\n"), encoding="utf-8")


def _clear_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _prepare_target_directory(plan: ScaffoldPlan) -> None:
    target = plan.project_root
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
        return

    if not target.is_dir():
        raise FileExistsError(f"目标路径不是目录: {target}")

    if not any(target.iterdir()):
        return

    if plan.conflict_policy == DirectoryConflictPolicy.CLEAR:
        _clear_directory(target)
        return
    if plan.conflict_policy == DirectoryConflictPolicy.OVERWRITE:
        return
    raise FileExistsError(
        f"目标目录已存在且非空: {target}。请使用 `--clear` 或 `--overwrite`，或改用交互模式。"
    )


def _copy_base_assets(plan: ScaffoldPlan) -> None:
    for relative_path in plan.base_copy_paths:
        source_path = REPO_ROOT / relative_path
        target_path = plan.project_root / relative_path
        if source_path.is_dir():
            shutil.copytree(source_path, target_path, dirs_exist_ok=True, ignore=COPY_IGNORE)
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _toml_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _render_key_values(section: dict[str, object]) -> str:
    if not section:
        return ""
    return "\n".join(f"{key} = {_toml_scalar(value)}" for key, value in section.items())


def _has_option(plan: ScaffoldPlan, *options: CapabilityOptionKey) -> bool:
    enabled = set(plan.enabled_options)
    return any(option in enabled for option in options)


def _render_grouped_capabilities(plan: ScaffoldPlan) -> str:
    lines: list[str] = []
    enabled = set(plan.enabled_options)
    for capability in plan.capabilities:
        option_labels = ", ".join(
            capability_option_label(option)
            for option in get_capability_options(capability)
            if option in enabled
        )
        if option_labels:
            lines.append(f"- `{capability.value}`：{capability_label(capability)}（{option_labels}）")
        else:
            lines.append(f"- `{capability.value}`：{capability_label(capability)}")
    return "\n".join(lines)


def _render_strategy_contract(plan: ScaffoldPlan) -> str:
    indicator_kwargs = _render_key_values(plan.preset.indicator_kwargs)
    signal_kwargs = _render_key_values(plan.preset.signal_kwargs)
    service_activation = _render_key_values(plan.service_activation)
    observability = ""
    if _has_option(plan, CapabilityOptionKey.DECISION_OBSERVABILITY):
        observability = dedent(
            """
            [observability]
            decision_journal_maxlen = 200
            emit_noop_decisions = false
            """
        ).strip()

    content = f'''
    [strategy_contracts]
    indicator_service = "{plan.indicator_import_path}"
    signal_service = "{plan.signal_import_path}"

    [strategy_contracts.indicator_kwargs]
    {indicator_kwargs}

    [strategy_contracts.signal_kwargs]
    {signal_kwargs}

    [service_activation]
    {service_activation}
    '''
    if observability:
        content = f"{content.strip()}\n\n{observability}\n"
    return dedent(content).strip() + "\n"


def _render_strategy_config(plan: ScaffoldPlan) -> str:
    blocks: list[str] = [
        f'''
        [[strategies]]
        class_name = "StrategyEntry"
        strategy_name = "{plan.project_slug}"
        vt_symbols = []

        [strategies.setting]
        max_positions = 5
        position_ratio = 0.1
        strike_level = 3
        bar_window = 1
        bar_interval = "MINUTE"

        [strategy_contracts]
        indicator_service = "{plan.indicator_import_path}"
        signal_service = "{plan.signal_import_path}"

        [strategy_contracts.indicator_kwargs]
        {_render_key_values(plan.preset.indicator_kwargs)}

        [strategy_contracts.signal_kwargs]
        {_render_key_values(plan.preset.signal_kwargs)}

        [service_activation]
        {_render_key_values(plan.service_activation)}

        [runtime]
        log_level = "INFO"
        log_dir = "data/logs"
        heartbeat_interval = 60
        max_restart_count = 10
        restart_delay = 5.0
        '''
    ]

    if _has_option(plan, CapabilityOptionKey.DECISION_OBSERVABILITY):
        blocks.append(
            '''
            [observability]
            decision_journal_maxlen = 200
            emit_noop_decisions = false
            '''
        )
    if _has_option(plan, CapabilityOptionKey.POSITION_SIZING):
        blocks.append(
            '''
            [position_sizing]
            margin_ratio = 0.12
            min_margin_ratio = 0.07
            margin_usage_limit = 0.6
            max_volume_per_order = 10
            '''
        )
    if _has_option(plan, CapabilityOptionKey.GREEKS_CALCULATOR, CapabilityOptionKey.PORTFOLIO_RISK):
        blocks.append(
            '''
            [greeks_risk]
            risk_free_rate = 0.02

            [greeks_risk.position_limits]
            delta = 0.8
            gamma = 0.1
            vega = 50.0

            [greeks_risk.portfolio_limits]
            delta = 5.0
            gamma = 1.0
            vega = 500.0
            '''
        )
    if _has_option(plan, CapabilityOptionKey.SMART_ORDER_EXECUTOR, CapabilityOptionKey.ADVANCED_ORDER_SCHEDULER):
        blocks.append(
            '''
            [order_execution]
            timeout_seconds = 30
            max_retries = 3
            slippage_ticks = 2

            [[order_execution.trading_periods]]
            start = "08:40"
            end = "11:30"

            [[order_execution.trading_periods]]
            start = "13:00"
            end = "15:30"

            [advanced_orders]
            default_iceberg_batch_size = 5
            default_twap_slices = 10
            default_time_window_seconds = 300
            '''
        )
    if _has_option(plan, CapabilityOptionKey.DELTA_HEDGING, CapabilityOptionKey.VEGA_HEDGING):
        blocks.append(
            '''
            [hedging.delta_hedging]
            target_delta = 0.0
            hedging_band = 0.5
            hedge_instrument_vt_symbol = ""
            hedge_instrument_delta = 1.0
            hedge_instrument_multiplier = 10.0

            [hedging.vega_hedging]
            target_vega = 0.0
            hedging_band = 50.0
            hedge_instrument_vt_symbol = ""
            hedge_instrument_vega = 0.1
            hedge_instrument_delta = 0.5
            hedge_instrument_gamma = 0.01
            hedge_instrument_theta = -0.05
            hedge_instrument_multiplier = 10.0
            '''
        )

    return "\n\n".join(dedent(block).strip() for block in blocks if block.strip()) + "\n"


def _render_project_pyproject(plan: ScaffoldPlan) -> str:
    return dedent(
        f'''
        [build-system]
        requires = ["setuptools>=69", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "{plan.project_slug}"
        dynamic = ["version", "dependencies"]
        description = "Option strategy workspace for {plan.project_name}"
        readme = "README.md"
        requires-python = ">=3.11"
        license = "AGPL-3.0-or-later"
        license-files = ["LICENSE"]
        keywords = ["options", "trading", "backtesting", "cli", "vnpy"]
        classifiers = [
            "Environment :: Console",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
        ]

        [project.scripts]
        option-scaffold = "src.cli.app:app"

        [tool.setuptools.dynamic]
        version = {{ attr = "src.__version__" }}
        dependencies = {{ file = ["requirements.txt"] }}

        [tool.setuptools.packages.find]
        include = ["src*"]
        exclude = ["tests*", "deploy*", "doc*", "temp*"]
        '''
    ).strip() + "\n"


def _render_root_readme(plan: ScaffoldPlan) -> str:
    capability_lines = _render_grouped_capabilities(plan)
    return dedent(
        f'''
        # {plan.project_name}

        这是由 `option-scaffold create` 生成的期权策略工作区。

        ## 选择摘要

        - 预设：`{plan.preset.key}`（{plan.preset.display_name}）
        - 策略包：`src/strategies/{plan.strategy_slug}`
        - 主配置：`config/strategy_config.toml`
        - 最小测试：`tests/strategies/{plan.strategy_slug}/test_contracts.py`

        ## 已启用能力

        {capability_lines}

        ## 关键文件

        - `src/strategies/{plan.strategy_slug}/indicator_service.py`
        - `src/strategies/{plan.strategy_slug}/signal_service.py`
        - `src/strategies/{plan.strategy_slug}/strategy_contract.toml`
        - `config/strategy_config.toml`

        ## 下一步

        1. 创建虚拟环境并安装依赖：

           ```powershell
           python -m venv .venv
           .\\.venv\\Scripts\\Activate.ps1
           pip install -r requirements.txt
           pip install -e .
           ```

        2. 校验配置与合同绑定：

           ```powershell
           option-scaffold validate --config config/strategy_config.toml
           ```

        3. 运行最小测试：

           ```powershell
           pytest -c config/pytest.ini tests/strategies/{plan.strategy_slug}/test_contracts.py
           ```

        4. 按需修改交易目标、领域服务配置和策略实现。
        '''
    ).strip() + "\n"


def _render_custom_indicator(plan: ScaffoldPlan) -> str:
    return dedent(
        f'''
        from __future__ import annotations

        from typing import Optional, TYPE_CHECKING

        from src.strategy.domain.domain_service.signal.indicator_service import IIndicatorService
        from src.strategy.domain.value_object.signal import IndicatorComputationResult, IndicatorContext

        if TYPE_CHECKING:
            from src.strategy.domain.entity.target_instrument import TargetInstrument


        class {plan.indicator_class_name}(IIndicatorService):
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
        '''
    ).strip() + "\n"


def _render_custom_signal(plan: ScaffoldPlan) -> str:
    return dedent(
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


        class {plan.signal_class_name}(ISignalService):
            def __init__(self, option_type: str = "call", strike_level: int = 1, **kwargs):
                self.option_type = option_type
                self.strike_level = int(strike_level)
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
        '''
    ).strip() + "\n"


def _load_template_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_strategy_package_readme(plan: ScaffoldPlan) -> str:
    if plan.preset.template_dir is None:
        content = f"# {plan.strategy_slug}\n\n自定义最小策略模板，适合从零开始补齐指标、信号与能力配置。\n"
    else:
        content = _load_template_text(plan.preset.template_dir / "README.md")
        first_line = content.splitlines()[0] if content.splitlines() else ""
        if first_line.startswith("# "):
            content = content.replace(first_line, f"# {plan.strategy_slug}", 1)

    enabled_caps = _render_grouped_capabilities(plan)
    return dedent(
        f'''
        {content.strip()}

        ## 当前启用能力

        {enabled_caps}
        '''
    ).strip() + "\n"


def _render_strategy_package(plan: ScaffoldPlan) -> None:
    strategy_dir = plan.strategy_package_dir
    strategy_dir.mkdir(parents=True, exist_ok=True)

    if plan.preset.template_dir is None:
        indicator_content = _render_custom_indicator(plan)
        signal_content = _render_custom_signal(plan)
    else:
        indicator_content = _load_template_text(plan.preset.template_dir / "indicator_service.py")
        signal_content = _load_template_text(plan.preset.template_dir / "signal_service.py")

    _write(strategy_dir / "__init__.py", "")
    _write(strategy_dir / "indicator_service.py", indicator_content)
    _write(strategy_dir / "signal_service.py", signal_content)
    _write(strategy_dir / "strategy_contract.toml", _render_strategy_contract(plan))
    _write(strategy_dir / "README.md", _render_strategy_package_readme(plan))


def _render_project_tests(plan: ScaffoldPlan) -> None:
    tests_dir = plan.project_root / "tests" / "strategies" / plan.strategy_slug
    _write(plan.project_root / "tests" / "__init__.py", "")
    _write(plan.project_root / "tests" / "strategies" / "__init__.py", "")
    _write(tests_dir / "__init__.py", "")
    _write(
        tests_dir / "test_contracts.py",
        f'''
        from __future__ import annotations

        from pathlib import Path
        import tomllib

        from src.strategies.{plan.strategy_slug}.indicator_service import {plan.indicator_class_name}
        from src.strategies.{plan.strategy_slug}.signal_service import {plan.signal_class_name}


        def test_contract_classes_can_be_imported() -> None:
            assert {plan.indicator_class_name}.__name__ == "{plan.indicator_class_name}"
            assert {plan.signal_class_name}.__name__ == "{plan.signal_class_name}"


        def test_strategy_contract_points_to_generated_package() -> None:
            contract_path = Path(__file__).resolve().parents[3] / "src" / "strategies" / "{plan.strategy_slug}" / "strategy_contract.toml"
            payload = tomllib.loads(contract_path.read_text(encoding="utf-8"))

            assert payload["strategy_contracts"]["indicator_service"] == "{plan.indicator_import_path}"
            assert payload["strategy_contracts"]["signal_service"] == "{plan.signal_import_path}"
        ''',
    )


def render_scaffold_plan(plan: ScaffoldPlan) -> Path:
    """执行整仓库脚手架渲染。"""
    _prepare_target_directory(plan)
    _copy_base_assets(plan)
    _write(plan.project_root / "pyproject.toml", _render_project_pyproject(plan))
    _write(plan.project_root / "README.md", _render_root_readme(plan))
    _write(plan.project_root / "config" / "strategy_config.toml", _render_strategy_config(plan))
    _write(plan.project_root / "src" / "strategies" / "__init__.py", "")
    _render_strategy_package(plan)
    _render_project_tests(plan)
    return plan.project_root
