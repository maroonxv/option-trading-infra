"""
run_recorder.py - 独立行情录制入口

职责:
1. 初始化 VnPy 引擎 (EventEngine, MainEngine)
2. 加载 DataRecorderApp (行情录制)
3. 连接 CTP 网关
4. 仅录制行情，不运行策略
"""
import os
import sys
import time
import signal
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# VnPy 导入
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy_datarecorder import DataRecorderApp

# 内部模块
from src.main.gateway import GatewayManager
from src.main.utils.config_loader import ConfigLoader
from src.main.utils.log_handler import setup_logging


class RecorderProcess:
    """
    行情录制进程
    """

    def __init__(
        self,
        log_level: str = "INFO",
        log_dir: str = "logs",
    ) -> None:
        self.log_level = log_level
        self.log_dir = log_dir

        self.logger = logging.getLogger(__name__)

        self.event_engine: Optional[EventEngine] = None
        self.main_engine: Optional[MainEngine] = None
        self.gateway_manager: Optional[GatewayManager] = None
        self.recorder_engine: Optional[Any] = None

        self.running: bool = False
        self.gateway_config: Dict[str, Any] = {}

        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum: int, frame) -> None:
        self.logger.info(f"收到信号 {signum}，准备关闭")
        self.running = False

    def run(self) -> None:
        self.running = True
        self.logger.info("行情录制进程启动")

        try:
            self._load_configs()
            self._setup_vnpy_database_settings()
            self._patch_data_recorder_setting_path()
            self._init_engines()
            self._connect_gateways()
            self._wait_for_connection()
            
            self._run_event_loop()
        except Exception as e:
            self.logger.error(f"录制进程异常: {e}", exc_info=True)
            sys.exit(1)
        finally:
            self.shutdown()

    def _load_configs(self) -> None:
        self.logger.info("加载配置...")
        self.gateway_config = ConfigLoader.load_gateway_config()

    def _setup_vnpy_database_settings(self) -> None:
        try:
            from vnpy.trader.setting import SETTINGS
        except Exception as e:
            self.logger.warning(f"加载 vn.py SETTINGS 失败: {e}")
            return

        driver = os.getenv("VNPY_DATABASE_DRIVER", "").strip()
        if not driver:
            self.logger.warning("未配置 VNPY_DATABASE_DRIVER，数据录制可能无法工作")
            return

        SETTINGS["database.driver"] = driver
        SETTINGS["database.name"] = driver
        SETTINGS["database.database"] = os.getenv("VNPY_DATABASE_DATABASE", "").strip()
        SETTINGS["database.host"] = os.getenv("VNPY_DATABASE_HOST", "localhost").strip()
        
        try:
            port = int(os.getenv("VNPY_DATABASE_PORT", "3306").strip())
        except Exception:
            port = 3306
        SETTINGS["database.port"] = port
        
        SETTINGS["database.user"] = os.getenv("VNPY_DATABASE_USER", "").strip()
        SETTINGS["database.password"] = os.getenv("VNPY_DATABASE_PASSWORD", "")

        self.logger.info(f"已注入 vn.py 数据库配置: driver={driver}")

    def _patch_data_recorder_setting_path(self) -> None:
        try:
            import vnpy.trader.utility as vnpy_utility
        except Exception as e:
            self.logger.warning(f"加载 vn.py utility 失败: {e}")
            return

        original_get_file_path = vnpy_utility.get_file_path

        config_path = PROJECT_ROOT / "config" / "general" / "data_recorder_setting.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        if (not config_path.exists()) or config_path.stat().st_size == 0:
            config_path.write_text("{}", encoding="utf-8")

        def patched_get_file_path(filename: str):
            if filename == "data_recorder_setting.json":
                self.logger.info(f"重定向 data_recorder_setting.json 到: {config_path}")
                return config_path
            return original_get_file_path(filename)

        vnpy_utility.get_file_path = patched_get_file_path

    def _init_engines(self) -> None:
        self.logger.info("初始化 VnPy 引擎...")
        self.event_engine = EventEngine()
        self.main_engine = MainEngine(self.event_engine)
        
        self.gateway_manager = GatewayManager(self.main_engine)
        self.gateway_manager.set_config(self.gateway_config)
        self.gateway_manager.add_gateways()

        self.recorder_engine = self.main_engine.add_app(DataRecorderApp)
        self.logger.info("DataRecorder 已加载")

    def _connect_gateways(self) -> None:
        self.logger.info("连接交易网关...")
        self.gateway_manager.connect_all()

    def _wait_for_connection(self, timeout: float = 60.0) -> None:
        self.logger.info(f"等待网关连接 (超时: {timeout}s)...")
        if self.gateway_manager.wait_for_connection(timeout):
            self.logger.info("网关连接成功")
        else:
            raise TimeoutError("网关连接超时")

    def _run_event_loop(self) -> None:
        self.logger.info("进入事件循环")
        while self.running:
            time.sleep(1.0)

    def shutdown(self) -> None:
        self.logger.info("正在关闭...")
        self.running = False
        if self.gateway_manager:
            self.gateway_manager.disconnect_all()
        elif self.main_engine:
            self.main_engine.close()
        self.logger.info("已关闭")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="独立行情录制")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--log-dir", default="data/logs")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.log_level, args.log_dir)
    
    process = RecorderProcess(
        log_level=args.log_level,
        log_dir=args.log_dir
    )
    process.run()
