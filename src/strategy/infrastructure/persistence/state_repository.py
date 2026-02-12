"""策略状态仓库 — 基于 MySQL JSON 存储。

职责:
- 保存策略状态快照到 strategy_state 表（INSERT 追加）
- 加载最新快照（ORDER BY saved_at DESC LIMIT 1）
- 区分"无记录"(ArchiveNotFound) 和"记录损坏"(CorruptionError)
- 验证记录完整性（JSON 可解析且包含 schema_version）
- 清理旧快照

Requirements: 1.4, 2.1, 2.2, 2.4, 2.5, 4.1, 4.8
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from logging import Logger
from typing import Any, Dict, Optional, Union

from src.main.bootstrap.database_factory import DatabaseFactory
from src.strategy.infrastructure.persistence.exceptions import CorruptionError
from src.strategy.infrastructure.persistence.json_serializer import (
    CURRENT_SCHEMA_VERSION,
    JsonSerializer,
)
from src.strategy.infrastructure.persistence.strategy_state_model import (
    StrategyStateModel,
)


@dataclass
class ArchiveNotFound:
    """表示数据库中无该策略状态记录的结果类型"""

    strategy_name: str


class StateRepository:
    """策略状态仓库 — 基于 MySQL JSON 存储。"""

    def __init__(
        self,
        serializer: JsonSerializer,
        database_factory: DatabaseFactory,
        logger: Optional[Logger] = None,
    ) -> None:
        self._serializer = serializer
        self._database_factory = database_factory
        self._logger = logger

    def save(self, strategy_name: str, data: Dict[str, Any]) -> None:
        """保存状态到数据库（INSERT 追加）。

        序列化为 JSON 后插入 strategy_state 表，保留所有历史快照。
        """
        json_str = self._serializer.serialize(data)

        db = self._database_factory.get_peewee_db()
        StrategyStateModel._meta.database = db

        StrategyStateModel.create(
            strategy_name=strategy_name,
            snapshot_json=json_str,
            schema_version=CURRENT_SCHEMA_VERSION,
            saved_at=datetime.now(),
        )

        if self._logger:
            self._logger.info(f"策略状态已保存: {strategy_name}")

    def load(
        self, strategy_name: str
    ) -> Union[Dict[str, Any], ArchiveNotFound]:
        """从数据库加载最新状态。

        - 无记录 → 返回 ArchiveNotFound
        - 记录存在但 JSON 反序列化失败 → 抛出 CorruptionError
        - 成功 → 返回 Dict
        """
        db = self._database_factory.get_peewee_db()
        StrategyStateModel._meta.database = db

        record = (
            StrategyStateModel.select()
            .where(StrategyStateModel.strategy_name == strategy_name)
            .order_by(StrategyStateModel.saved_at.desc())
            .first()
        )

        if record is None:
            if self._logger:
                self._logger.info(f"未找到策略状态记录: {strategy_name}")
            return ArchiveNotFound(strategy_name=strategy_name)

        try:
            data = self._serializer.deserialize(record.snapshot_json)
        except Exception as e:
            raise CorruptionError(
                strategy_name=strategy_name, original_error=e
            ) from e

        if self._logger:
            self._logger.info(f"策略状态已加载: {strategy_name}")
        return data

    def verify_integrity(self, strategy_name: str) -> bool:
        """验证最新记录完整性：检查 JSON 可解析且包含 schema_version。"""
        db = self._database_factory.get_peewee_db()
        StrategyStateModel._meta.database = db

        record = (
            StrategyStateModel.select()
            .where(StrategyStateModel.strategy_name == strategy_name)
            .order_by(StrategyStateModel.saved_at.desc())
            .first()
        )

        if record is None:
            return False

        try:
            parsed = json.loads(record.snapshot_json)
        except (json.JSONDecodeError, TypeError):
            return False

        return "schema_version" in parsed

    def cleanup(self, strategy_name: str, keep_days: int = 7) -> int:
        """清理旧快照。删除 saved_at 早于 keep_days 天前的记录。返回删除的记录数。"""
        db = self._database_factory.get_peewee_db()
        StrategyStateModel._meta.database = db

        cutoff = datetime.now() - timedelta(days=keep_days)

        deleted = (
            StrategyStateModel.delete()
            .where(
                (StrategyStateModel.strategy_name == strategy_name)
                & (StrategyStateModel.saved_at < cutoff)
            )
            .execute()
        )

        if self._logger:
            self._logger.info(
                f"清理旧快照: {strategy_name}, 删除 {deleted} 条记录"
            )
        return deleted
