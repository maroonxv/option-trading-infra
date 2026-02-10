"""
logging_setup.py - 日志处理模块

负责配置全局日志系统，支持控制台和文件输出。
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(log_level: str, log_dir: str, log_name: str = "strategy.log") -> None:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        log_name: 日志文件名 (默认: strategy.log)
    """
    
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    log_file = log_path / log_name
    
    # 移除所有现有的 handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in list(root.handlers):
            handler.close()
            root.removeHandler(handler)
    
    # 每天一个日志文件，保留 30 天
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True
    )
    file_handler.suffix = "%Y%m%d"  # 设置后缀格式
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )
