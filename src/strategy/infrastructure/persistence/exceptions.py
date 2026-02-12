"""持久化层异常类型定义"""

from typing import List


class CorruptionError(Exception):
    """状态记录损坏异常"""

    def __init__(self, strategy_name: str, original_error: Exception) -> None:
        self.strategy_name = strategy_name
        self.original_error = original_error
        super().__init__(
            f"State record corrupted for strategy: {strategy_name}. "
            f"Original error: {original_error}"
        )


class DatabaseConfigError(Exception):
    """数据库配置错误（缺少环境变量）"""

    def __init__(self, missing_vars: List[str]) -> None:
        self.missing_vars = missing_vars
        super().__init__(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )


class DatabaseConnectionError(Exception):
    """数据库连接失败"""

    def __init__(self, host: str, database: str, original_error: Exception) -> None:
        self.host = host
        self.database = database
        self.original_error = original_error
        super().__init__(
            f"Failed to connect to database {database}@{host}: {original_error}"
        )
