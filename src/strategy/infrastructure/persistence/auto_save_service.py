"""周期性自动保存服务。

在 on_bars 回调中按时间间隔自动保存策略状态到数据库，
避免仅在 on_stop 时保存导致崩溃丢失数据。

设计决策:
- maybe_save 接受 Callable 而非直接接受数据，实现惰性求值
- 使用 time.monotonic() 计时，避免系统时钟调整的影响
- 保存失败时捕获异常并记录日志，不中断策略执行

Requirements: 1.1, 1.2, 1.3, 1.5
"""

import time
from logging import Logger, getLogger
from typing import Any, Callable, Dict, Optional

from src.strategy.infrastructure.persistence.state_repository import StateRepository


class AutoSaveService:
    """周期性自动保存服务"""

    def __init__(
        self,
        state_repository: StateRepository,
        strategy_name: str,
        interval_seconds: float = 60.0,
        logger: Optional[Logger] = None,
    ) -> None:
        self._repository = state_repository
        self._strategy_name = strategy_name
        self._interval_seconds = interval_seconds
        self._logger = logger or getLogger(__name__)
        self._last_save_time: float = time.monotonic()

    def maybe_save(self, snapshot_fn: Callable[[], Dict[str, Any]]) -> None:
        """检查是否到达保存间隔，若到达则保存快照。

        snapshot_fn 是惰性求值，仅在需要保存时才调用，
        避免每次 on_bars 都执行序列化开销。
        """
        now = time.monotonic()
        elapsed = now - self._last_save_time
        if elapsed < self._interval_seconds:
            return

        self._do_save(snapshot_fn)

    def force_save(self, snapshot_fn: Callable[[], Dict[str, Any]]) -> None:
        """强制立即保存（用于 on_stop）。"""
        self._do_save(snapshot_fn)

    def reset(self) -> None:
        """重置计时器。"""
        self._last_save_time = time.monotonic()

    def _do_save(self, snapshot_fn: Callable[[], Dict[str, Any]]) -> None:
        """执行保存操作，失败时记录日志但不中断策略执行。"""
        try:
            data = snapshot_fn()
            self._repository.save(self._strategy_name, data)
            self._last_save_time = time.monotonic()
        except Exception as e:
            self._logger.error(
                f"自动保存失败 [{self._strategy_name}]: {e}",
                exc_info=True,
            )
