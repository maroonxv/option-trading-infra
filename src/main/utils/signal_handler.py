"""
信号处理模块 — 提供统一的进程信号注册功能。

提取自 main.py、child_process.py、parent_process.py、run_recorder.py 中重复的信号注册代码。
"""
import signal
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


def register_shutdown_signals(callback: Callable[[int, Any], None]) -> None:
    """
    注册 SIGTERM 和 SIGINT 信号处理器。
    
    Args:
        callback: 信号回调函数，签名为 (signum, frame) -> None
    """
    signal.signal(signal.SIGTERM, callback)
    signal.signal(signal.SIGINT, callback)
    logger.debug("已注册 SIGTERM/SIGINT 信号处理器")
