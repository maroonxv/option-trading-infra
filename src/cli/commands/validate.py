"""配置校验命令。"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Optional

import typer

from src.backtesting.config import BacktestConfig
from src.cli.common import (
    CheckResult,
    EXIT_CODE_VALIDATION,
    display_path,
    echo_check,
    ensure_project_root_on_path,
    flag_enabled,
    resolve_project_path,
)
from src.main.config.config_loader import ConfigLoader

DEFAULT_INDICATOR_SERVICE = "src.strategy.domain.domain_service.signal.indicator_service:IndicatorService"
DEFAULT_SIGNAL_SERVICE = "src.strategy.domain.domain_service.signal.signal_service:SignalService"


def _ok(title: str, detail: str) -> CheckResult:
    return CheckResult(status="OK", title=title, detail=detail)


def _warn(title: str, detail: str) -> CheckResult:
    return CheckResult(status="WARN", title=title, detail=detail)


def _error(title: str, detail: str) -> CheckResult:
    return CheckResult(status="ERROR", title=title, detail=detail)


def _parse_iso_date(raw: str, label: str) -> tuple[date | None, CheckResult]:
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        return None, _error(label, f"日期格式必须为 YYYY-MM-DD，收到: {raw}")

    return parsed, _ok(label, raw)


def _validate_backtest_overrides(
    config: Path,
    start: str | None,
    end: str | None,
    capital: int | None,
    rate: float | None,
    slippage: float | None,
    size: int | None,
    pricetick: float | None,
    no_chart: str,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    start_date: date | None = None
    end_date: date | None = None

    if start is not None:
        start_date, result = _parse_iso_date(start, "回测开始日期")
        results.append(result)

    if end is not None:
        end_date, result = _parse_iso_date(end, "回测结束日期")
        results.append(result)

    if start_date is not None and end_date is not None:
        if start_date > end_date:
            results.append(_error("回测日期区间", f"开始日期 {start} 晚于结束日期 {end}"))
        else:
            results.append(_ok("回测日期区间", f"{start} → {end}"))

    numeric_checks = [
        ("初始资金", capital, lambda value: value > 0, "必须大于 0"),
        ("手续费率", rate, lambda value: value >= 0, "不能为负数"),
        ("滑点", slippage, lambda value: value >= 0, "不能为负数"),
        ("合约乘数", size, lambda value: value > 0, "必须大于 0"),
        ("最小价格变动", pricetick, lambda value: value > 0, "必须大于 0"),
    ]

    for title, value, predicate, message in numeric_checks:
        if value is None:
            continue
        if predicate(value):
            results.append(_ok(title, str(value)))
        else:
            results.append(_error(title, f"{value}，{message}"))

    args = argparse.Namespace(
        config=str(config),
        start=start,
        end=end,
        capital=capital,
        rate=rate,
        slippage=slippage,
        size=size,
        pricetick=pricetick,
        no_chart=flag_enabled(no_chart),
    )
    backtest_config = BacktestConfig.from_args(args)
    results.append(
        _ok(
            "回测参数摘要",
            (
                f"config={display_path(backtest_config.config_path)}, capital={backtest_config.capital}, "
                f"rate={backtest_config.rate}, slippage={backtest_config.slippage}, "
                f"size={backtest_config.default_size}, pricetick={backtest_config.default_pricetick}, "
                f"show_chart={backtest_config.show_chart}"
            ),
        )
    )
    return results


def command(
    config: Path = typer.Option(Path("config/strategy_config.toml"), "--config", help="策略配置文件路径。"),
    override_config: Optional[Path] = typer.Option(None, "--override-config", help="可选的覆盖配置文件路径。"),
    start: Optional[str] = typer.Option(None, "--start", help="可选的回测开始日期，格式 YYYY-MM-DD。"),
    end: Optional[str] = typer.Option(None, "--end", help="可选的回测结束日期，格式 YYYY-MM-DD。"),
    capital: Optional[int] = typer.Option(None, "--capital", help="可选的回测初始资金覆盖值。"),
    rate: Optional[float] = typer.Option(None, "--rate", help="可选的回测手续费率覆盖值。"),
    slippage: Optional[float] = typer.Option(None, "--slippage", help="可选的回测滑点覆盖值。"),
    size: Optional[int] = typer.Option(None, "--size", help="可选的回测合约乘数覆盖值。"),
    pricetick: Optional[float] = typer.Option(None, "--pricetick", help="可选的回测最小价格变动覆盖值。"),
    no_chart: str = typer.Option("", "--no-chart", flag_value="1", show_default=False, help="按回测命令语义校验图表开关。"),
) -> None:
    """校验策略配置、契约绑定与可选回测参数。"""
    ensure_project_root_on_path()

    results: list[CheckResult] = []
    base_config: dict | None = None
    merged_config: dict | None = None
    override_payload: dict | None = None

    resolved_config = resolve_project_path(config)
    if not resolved_config.exists():
        results.append(_error("策略配置文件", f"未找到 {display_path(resolved_config)}"))
    else:
        try:
            base_config = ConfigLoader.load_toml(str(resolved_config))
            results.append(_ok("策略配置文件", display_path(resolved_config)))
        except Exception as exc:
            results.append(_error("策略配置文件", f"{display_path(resolved_config)} 解析失败: {exc}"))

    if override_config is not None:
        resolved_override = resolve_project_path(override_config)
        if not resolved_override.exists():
            results.append(_error("覆盖配置文件", f"未找到 {display_path(resolved_override)}"))
        else:
            try:
                override_payload = ConfigLoader.load_toml(str(resolved_override))
                results.append(_ok("覆盖配置文件", display_path(resolved_override)))
            except Exception as exc:
                results.append(_error("覆盖配置文件", f"{display_path(resolved_override)} 解析失败: {exc}"))

    if base_config is not None:
        try:
            merged_config = ConfigLoader.merge_strategy_config(base_config, override_payload or {})
            ConfigLoader.validate_strategy_config(merged_config)
            strategy_count = len(merged_config.get("strategies") or [])
            results.append(_ok("策略结构", f"已识别 {strategy_count} 个策略定义"))
        except Exception as exc:
            results.append(_error("策略结构", str(exc)))

    if merged_config is not None:
        strategy_contracts = dict(merged_config.get("strategy_contracts") or {})
        contract_mappings = {
            "indicator_service": strategy_contracts.get("indicator_service", DEFAULT_INDICATOR_SERVICE),
            "signal_service": strategy_contracts.get("signal_service", DEFAULT_SIGNAL_SERVICE),
        }
        for name, import_path in contract_mappings.items():
            try:
                contract_cls = ConfigLoader.import_from_string(import_path)
                results.append(_ok(f"契约 {name}", f"{import_path} -> {contract_cls.__name__}"))
            except Exception as exc:
                results.append(_error(f"契约 {name}", f"{import_path} 导入失败: {exc}"))

        service_activation = ConfigLoader.resolve_service_activation(merged_config)
        enabled_count = sum(1 for enabled in service_activation.values() if enabled)
        results.append(_ok("服务开关", f"启用 {enabled_count} 项，共 {len(service_activation)} 项"))

        observability = dict(merged_config.get("observability") or {})
        try:
            journal_limit = int(observability.get("decision_journal_maxlen", 200) or 200)
            if journal_limit <= 0:
                results.append(_error("可观测性配置", "decision_journal_maxlen 必须大于 0"))
            else:
                emit_noop = bool(observability.get("emit_noop_decisions", False))
                results.append(_ok("可观测性配置", f"decision_journal_maxlen={journal_limit}, emit_noop_decisions={emit_noop}"))
        except (TypeError, ValueError):
            results.append(_error("可观测性配置", "decision_journal_maxlen 必须为整数"))

    target_path = resolve_project_path("config/general/trading_target.toml")
    if not target_path.exists():
        results.append(_error("交易标的配置", f"未找到 {display_path(target_path)}"))
    else:
        try:
            targets = ConfigLoader.load_target_products(str(target_path))
            if not targets:
                results.append(_error("交易标的配置", "targets 不能为空"))
            else:
                results.append(_ok("交易标的配置", f"已配置 {len(targets)} 个标的: {', '.join(targets)}"))
        except Exception as exc:
            results.append(_error("交易标的配置", str(exc)))

    subscription_path = resolve_project_path("config/subscription/subscription.toml")
    if subscription_path.exists():
        try:
            subscription_config = ConfigLoader.load_toml(str(subscription_path))
            enabled = bool(subscription_config.get("enabled", False))
            results.append(_ok("订阅配置", f"{display_path(subscription_path)}，enabled={enabled}"))
        except Exception as exc:
            results.append(_error("订阅配置", f"{display_path(subscription_path)} 解析失败: {exc}"))
    else:
        results.append(_warn("订阅配置", f"未找到 {display_path(subscription_path)}，已按可选项跳过"))

    results.extend(
        _validate_backtest_overrides(
            config=resolved_config,
            start=start,
            end=end,
            capital=capital,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            no_chart=no_chart,
        )
    )

    for result in results:
        echo_check(result)

    error_count = sum(1 for result in results if result.status == "ERROR")
    warning_count = sum(1 for result in results if result.status == "WARN")
    if error_count:
        typer.echo(f"校验失败：{error_count} 个错误，{warning_count} 个提示。")
        raise typer.Exit(code=EXIT_CODE_VALIDATION)

    typer.echo(f"校验通过：0 个错误，{warning_count} 个提示。")
