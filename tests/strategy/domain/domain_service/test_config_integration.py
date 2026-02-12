"""
配置加载与默认值回退单元测试

验证 YAML 配置解析和缺失配置时的默认值行为。
"""
import os
import yaml
import tempfile
import pytest

from src.strategy.domain.value_object.risk import RiskThresholds
from src.strategy.domain.value_object.order_execution import OrderExecutionConfig


def _load_config(yaml_content: str) -> dict:
    """辅助: 从 YAML 字符串加载配置"""
    return yaml.safe_load(yaml_content) or {}


def _build_risk_thresholds(config: dict) -> RiskThresholds:
    """从配置字典构建 RiskThresholds，缺失时使用默认值"""
    greeks_risk_cfg = config.get("greeks_risk", {})
    pos = greeks_risk_cfg.get("position_limits", {})
    port = greeks_risk_cfg.get("portfolio_limits", {})
    return RiskThresholds(
        position_delta_limit=pos.get("delta", 0.8),
        position_gamma_limit=pos.get("gamma", 0.1),
        position_vega_limit=pos.get("vega", 50.0),
        portfolio_delta_limit=port.get("delta", 5.0),
        portfolio_gamma_limit=port.get("gamma", 1.0),
        portfolio_vega_limit=port.get("vega", 500.0),
    )


def _build_order_config(config: dict) -> OrderExecutionConfig:
    """从配置字典构建 OrderExecutionConfig，缺失时使用默认值"""
    oe = config.get("order_execution", {})
    return OrderExecutionConfig(
        timeout_seconds=oe.get("timeout_seconds", 30),
        max_retries=oe.get("max_retries", 3),
        slippage_ticks=oe.get("slippage_ticks", 2),
    )


class TestConfigIntegration:

    def test_full_config_parsing(self):
        """完整配置正确解析"""
        yaml_str = """
greeks_risk:
  risk_free_rate: 0.03
  position_limits:
    delta: 0.9
    gamma: 0.2
    vega: 60.0
  portfolio_limits:
    delta: 6.0
    gamma: 2.0
    vega: 600.0
order_execution:
  timeout_seconds: 45
  max_retries: 5
  slippage_ticks: 3
"""
        config = _load_config(yaml_str)
        thresholds = _build_risk_thresholds(config)
        order_cfg = _build_order_config(config)

        assert thresholds.position_delta_limit == 0.9
        assert thresholds.position_gamma_limit == 0.2
        assert thresholds.position_vega_limit == 60.0
        assert thresholds.portfolio_delta_limit == 6.0
        assert thresholds.portfolio_gamma_limit == 2.0
        assert thresholds.portfolio_vega_limit == 600.0
        assert order_cfg.timeout_seconds == 45
        assert order_cfg.max_retries == 5
        assert order_cfg.slippage_ticks == 3

    def test_missing_greeks_risk_uses_defaults(self):
        """缺少 greeks_risk 节时使用默认值"""
        config = _load_config("order_execution:\n  timeout_seconds: 10\n")
        thresholds = _build_risk_thresholds(config)

        assert thresholds.position_delta_limit == 0.8
        assert thresholds.position_gamma_limit == 0.1
        assert thresholds.position_vega_limit == 50.0
        assert thresholds.portfolio_delta_limit == 5.0

    def test_missing_order_execution_uses_defaults(self):
        """缺少 order_execution 节时使用默认值"""
        config = _load_config("")
        order_cfg = _build_order_config(config)

        assert order_cfg.timeout_seconds == 30
        assert order_cfg.max_retries == 3
        assert order_cfg.slippage_ticks == 2

    def test_partial_config_fills_defaults(self):
        """部分配置时，缺失字段使用默认值"""
        yaml_str = """
greeks_risk:
  position_limits:
    delta: 0.5
order_execution:
  timeout_seconds: 60
"""
        config = _load_config(yaml_str)
        thresholds = _build_risk_thresholds(config)
        order_cfg = _build_order_config(config)

        assert thresholds.position_delta_limit == 0.5
        assert thresholds.position_gamma_limit == 0.1  # default
        assert thresholds.position_vega_limit == 50.0  # default
        assert order_cfg.timeout_seconds == 60
        assert order_cfg.max_retries == 3  # default

    def test_actual_config_file_parseable(self):
        """验证实际的 strategy_config.yaml 可以正确解析"""
        config_path = os.path.join("config", "strategy_config.yaml")
        if not os.path.exists(config_path):
            pytest.skip("config/strategy_config.yaml not found")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        thresholds = _build_risk_thresholds(config)
        order_cfg = _build_order_config(config)

        # 验证配置文件中的值
        assert thresholds.position_delta_limit == 0.8
        assert thresholds.portfolio_delta_limit == 5.0
        assert order_cfg.timeout_seconds == 30
        assert order_cfg.max_retries == 3
