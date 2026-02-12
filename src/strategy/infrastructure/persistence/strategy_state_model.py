"""策略状态 Peewee 模型定义。

保留所有历史快照，每次保存都是 INSERT 追加。
加载时查询 WHERE strategy_name = ? ORDER BY saved_at DESC LIMIT 1 取最新记录。

Requirements: 1.4
"""

from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    IntegerField,
    Model,
    TextField,
)


class StrategyStateModel(Model):
    """策略状态 Peewee 模型"""

    id = AutoField(primary_key=True)
    strategy_name = CharField(max_length=128, index=True)
    snapshot_json = TextField()
    schema_version = IntegerField(default=1)
    saved_at = DateTimeField(index=True)

    class Meta:
        table_name = "strategy_state"
        indexes = (
            (("strategy_name", "saved_at"), False),
        )
