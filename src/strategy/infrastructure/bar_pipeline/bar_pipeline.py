"""BarPipeline — 封装 PortfolioBarGenerator 的K线合成管道。

这是一个具体类（非抽象基类），不使用 ABC、不使用继承体系。
当策略需要自定义时间窗口K线（如15分钟K线）时，使用此类封装 PBG。
"""

from typing import Callable, Dict

from vnpy.trader.constant import Interval
from vnpy.trader.object import BarData, TickData
from vnpy_portfoliostrategy.utility import PortfolioBarGenerator


class BarPipeline:
    """K线合成管道 — 封装 PortfolioBarGenerator。"""

    def __init__(
        self,
        bar_callback: Callable[[Dict[str, "BarData"]], None],
        window: int,
        interval: Interval,
    ) -> None:
        self._bar_callback = bar_callback
        self._pbg = PortfolioBarGenerator(
            on_bars=self._on_intermediate_bars,
            window=window,
            on_window_bars=self._on_window_bars,
            interval=interval,
        )

    def _on_intermediate_bars(self, bars: Dict[str, BarData]) -> None:
        """PBG 内部中间回调（不对外暴露）。"""
        pass

    def _on_window_bars(self, bars: Dict[str, BarData]) -> None:
        """PBG 合成完成后调用 bar_callback。"""
        self._bar_callback(bars)

    def handle_tick(self, tick: TickData) -> None:
        """处理 tick 数据 — 委托给 PBG。"""
        self._pbg.update_tick(tick)

    def handle_bars(self, bars: Dict[str, BarData]) -> None:
        """处理 bars 数据 — 委托给 PBG 进行合成。"""
        self._pbg.update_bars(bars)
