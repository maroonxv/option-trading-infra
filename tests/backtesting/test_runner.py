"""BacktestRunner unit tests. Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5"""
import sys
from enum import Enum
from unittest.mock import MagicMock, patch


class _Exchange(str, Enum):
    SHFE = "SHFE"
    CFFEX = "CFFEX"
    DCE = "DCE"
    CZCE = "CZCE"
    INE = "INE"


class _Product(str, Enum):
    FUTURES = "FUTURES"
    OPTION = "OPTION"


class _OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class _Interval(str, Enum):
    MINUTE = "1m"


class _ContractData:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def vt_symbol(self):
        return f"{self.symbol}.{self.exchange.value}"


_cm = MagicMock()
_cm.Exchange = _Exchange
_cm.Product = _Product
_cm.OptionType = _OptionType
_cm.Interval = _Interval
_om = MagicMock()
_om.ContractData = _ContractData
for _n in [
    "vnpy", "vnpy.event", "vnpy.event.engine",
    "vnpy.trader", "vnpy.trader.setting", "vnpy.trader.engine",
    "vnpy.trader.database", "vnpy_mysql",
    "vnpy_portfoliostrategy", "vnpy_portfoliostrategy.utility",
]:
    if _n not in sys.modules:
        sys.modules[_n] = MagicMock()
sys.modules["vnpy.trader.constant"] = _cm
sys.modules["vnpy.trader.object"] = _om
sys.modules["src.strategy.strategy_entry"] = MagicMock()

import pytest  # noqa: E402
from src.backtesting.config import BacktestConfig  # noqa: E402
from src.backtesting.runner import BacktestRunner  # noqa: E402


@pytest.fixture
def cfg():
    return BacktestConfig(
        config_path="config/strategy_config.yaml",
        start_date="2025-01-01",
        end_date="2025-06-30",
        capital=1_000_000,
        show_chart=False,
    )


@pytest.fixture
def yaml_cfg():
    return {"strategies": [{"class_name": "S", "strategy_name": "t", "vt_symbols": ["rb"], "setting": {"p": 1}}]}


@pytest.fixture
def yaml_empty():
    return {"strategies": [{"class_name": "S", "strategy_name": "t", "vt_symbols": [], "setting": {}}]}


def _mock_reg(runner):
    runner.registry = MagicMock()
    runner.registry.register_many.return_value = 1
    c = MagicMock()
    c.size = 10
    c.pricetick = 1.0
    runner.registry.get.return_value = c


class TestInit:
    def test_stores_config(self, cfg):
        assert BacktestRunner(cfg).config is cfg

    def test_creates_registry(self, cfg):
        assert BacktestRunner(cfg).registry.get_all() == []


class TestEmptySymbols:
    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_terminates(self, cl, sg, od, cfg, yaml_cfg):
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = []
        od.discover.return_value = []
        BacktestRunner(cfg).run()

    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_loads_target(self, cl, sg, od, cfg, yaml_empty):
        cl.load_yaml.return_value = yaml_empty
        cl.load_target_products.return_value = ["rb"]
        sg.generate_recent.return_value = []
        od.discover.return_value = []
        BacktestRunner(cfg).run()
        cl.load_target_products.assert_called_once()


class TestNoStrategies:
    @patch("src.backtesting.runner.ConfigLoader")
    def test_returns_early(self, cl, cfg):
        cl.load_yaml.return_value = {"strategies": []}
        BacktestRunner(cfg).run()


class TestFullFlow:
    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_engine_methods(self, cl, sg, od, cfg, yaml_cfg):
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = ["rb2501.SHFE"]
        od.discover.return_value = []
        engine = MagicMock()
        with patch("vnpy_portfoliostrategy.BacktestingEngine", return_value=engine):
            r = BacktestRunner(cfg)
            _mock_reg(r)
            r.run()
        r.registry.inject_into_engine.assert_called_once_with(engine)
        engine.set_parameters.assert_called_once()
        engine.add_strategy.assert_called_once()
        engine.load_data.assert_called_once()
        engine.run_backtesting.assert_called_once()
        engine.calculate_result.assert_called_once()
        engine.calculate_statistics.assert_called_once()

    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_show_chart(self, cl, sg, od, yaml_cfg):
        c = BacktestConfig(start_date="2025-01-01", end_date="2025-06-30", show_chart=True)
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = ["rb2501.SHFE"]
        od.discover.return_value = []
        engine = MagicMock()
        with patch("vnpy_portfoliostrategy.BacktestingEngine", return_value=engine):
            r = BacktestRunner(c)
            _mock_reg(r)
            r.run()
        engine.show_chart.assert_called_once()

    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_no_chart(self, cl, sg, od, yaml_cfg):
        c = BacktestConfig(start_date="2025-01-01", end_date="2025-06-30", show_chart=False)
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = ["rb2501.SHFE"]
        od.discover.return_value = []
        engine = MagicMock()
        with patch("vnpy_portfoliostrategy.BacktestingEngine", return_value=engine):
            r = BacktestRunner(c)
            _mock_reg(r)
            r.run()
        engine.show_chart.assert_not_called()


class TestRegistry:
    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_inject(self, cl, sg, od, cfg, yaml_cfg):
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = ["rb2501.SHFE"]
        od.discover.return_value = []
        engine = MagicMock()
        with patch("vnpy_portfoliostrategy.BacktestingEngine", return_value=engine):
            r = BacktestRunner(cfg)
            _mock_reg(r)
            r.run()
        r.registry.register_many.assert_called_once_with(["rb2501.SHFE"])
        r.registry.inject_into_engine.assert_called_once_with(engine)

    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_options_included(self, cl, sg, od, cfg, yaml_cfg):
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = ["IF2501.CFFEX"]
        od.discover.return_value = ["IO2501-C-4000.CFFEX"]
        engine = MagicMock()
        with patch("vnpy_portfoliostrategy.BacktestingEngine", return_value=engine):
            r = BacktestRunner(cfg)
            _mock_reg(r)
            r.registry.register_many.return_value = 2
            r.run()
        syms = r.registry.register_many.call_args[0][0]
        assert "IF2501.CFFEX" in syms
        assert "IO2501-C-4000.CFFEX" in syms


class TestEngineParams:
    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_end_date_none(self, cl, sg, od, yaml_cfg):
        c = BacktestConfig(start_date="2025-01-01", end_date=None, show_chart=False)
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = ["rb2501.SHFE"]
        od.discover.return_value = []
        engine = MagicMock()
        with patch("vnpy_portfoliostrategy.BacktestingEngine", return_value=engine):
            r = BacktestRunner(c)
            _mock_reg(r)
            r.run()
        engine.set_parameters.assert_called_once()

    @patch("src.backtesting.runner.OptionDiscoveryService")
    @patch("src.backtesting.runner.SymbolGenerator")
    @patch("src.backtesting.runner.ConfigLoader")
    def test_backtesting_flag(self, cl, sg, od, cfg, yaml_cfg):
        cl.load_yaml.return_value = yaml_cfg
        sg.generate_recent.return_value = ["rb2501.SHFE"]
        od.discover.return_value = []
        engine = MagicMock()
        with patch("vnpy_portfoliostrategy.BacktestingEngine", return_value=engine):
            r = BacktestRunner(cfg)
            _mock_reg(r)
            r.run()
        setting = engine.add_strategy.call_args[1]["setting"]
        assert setting["backtesting"] is True
