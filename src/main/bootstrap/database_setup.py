"""
database_setup.py - VnPy 数据库配置注入

职责:
从环境变量读取数据库配置并注入到 VnPy SETTINGS 中。
合并自 child_process.py._setup_vnpy_database_settings() 和
run_recorder.py._setup_vnpy_database_settings() 的公共逻辑。
"""
import os
import logging

logger = logging.getLogger(__name__)


def setup_vnpy_database() -> bool:
    """
    从环境变量读取数据库配置并注入到 VnPy SETTINGS。
    
    环境变量:
        VNPY_DATABASE_DRIVER: 数据库驱动 (必需，如 "mysql", "postgresql")
        VNPY_DATABASE_DATABASE: 数据库名称
        VNPY_DATABASE_HOST: 数据库主机 (默认: "localhost")
        VNPY_DATABASE_PORT: 数据库端口 (默认: 3306)
        VNPY_DATABASE_USER: 数据库用户名
        VNPY_DATABASE_PASSWORD: 数据库密码
    
    Returns:
        True 如果配置成功注入，False 如果未配置或加载失败
    """
    try:
        from vnpy.trader.setting import SETTINGS
    except Exception as e:
        logger.warning(f"加载 vn.py SETTINGS 失败: {e}")
        return False

    driver = os.getenv("VNPY_DATABASE_DRIVER", "").strip()
    if not driver:
        logger.warning("未配置 VNPY_DATABASE_DRIVER")
        return False

    SETTINGS["database.driver"] = driver
    SETTINGS["database.name"] = driver
    SETTINGS["database.database"] = os.getenv("VNPY_DATABASE_DATABASE", "").strip()
    SETTINGS["database.host"] = os.getenv("VNPY_DATABASE_HOST", "localhost").strip()

    try:
        port = int(os.getenv("VNPY_DATABASE_PORT", "3306").strip())
    except (ValueError, TypeError):
        port = 3306
    SETTINGS["database.port"] = port

    SETTINGS["database.user"] = os.getenv("VNPY_DATABASE_USER", "").strip()
    SETTINGS["database.password"] = os.getenv("VNPY_DATABASE_PASSWORD", "")

    logger.info(f"已注入 vn.py 数据库配置: driver={driver}")
    return True
