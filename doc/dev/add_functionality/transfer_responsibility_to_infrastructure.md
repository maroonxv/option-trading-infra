# 职责转移重构计划：Application -> Infrastructure

为了解决 `src/strategy/application/volatility_trade.py` 类体积过大、职责过多（God Class）的问题，计划将非核心交易逻辑（监控、持久化）剥离至基础设施层。

## 1. 剥离监控与快照逻辑 (StrategyMonitor)

目前 `VolatilityTrade` 中包含大量直接操作 MySQL 和生成前端监控快照 (`.pkl`) 的代码。这些属于观测性（Observability）基础设施。

### 目标组件
*   **路径**: `src/strategy/infrastructure/monitoring/strategy_monitor.py`
*   **类名**: `StrategyMonitor`

### 迁移内容
将以下方法和相关属性移入 `StrategyMonitor`:
*   `_monitor_db_connect`: 数据库连接管理
*   `_ensure_monitor_tables`: 数据库表结构初始化
*   `_upsert_monitor_snapshot`: 写入快照数据到 DB
*   `_insert_monitor_event`: 写入事件数据到 DB
*   `_dump_snapshot`: 生成前端需要的复杂 JSON/Pickle 结构
*   **属性**: `monitor_db_enabled`, `_monitor_db_config`, `snapshot_path`, `_last_status_map` 等

### 交互方式
`VolatilityTrade` 在初始化时实例化 `StrategyMonitor`。在 `handle_bar_update` 或状态变更时调用：
```python
# 示例调用
self.monitor.record_snapshot(
    target_aggregate=self.target_aggregate,
    position_aggregate=self.position_aggregate,
    indicators={...},
    variant_name=self.variant_name
)
```

## 2. 剥离状态持久化逻辑 (StateRepository)

策略的停止保存 (`dump_state`) 和启动恢复 (`load_state`) 属于持久化机制，不应与业务逻辑混杂。

### 目标组件
*   **路径**: `src/strategy/infrastructure/persistence/state_repository.py`
*   **类名**: `StateRepository` (或 `FileStateRepository` 实现接口)

### 迁移内容
将以下方法移入仓库类:
*   `dump_state(file_path, data)`: 负责原子写入
*   `load_state(file_path)`: 负责读取并处理版本兼容性

### 交互方式
`VolatilityTrade` 仅负责收集需要保存的数据字典，然后委托给 Repository：
```python
# Save
state_data = {
    "version": 2,
    "active_contracts": ...,
    "position_aggregate": ...
}
self.state_repository.save(self.state_file_path, state_data)

# Load
state_data = self.state_repository.load(self.state_file_path)
if state_data:
    self._restore_from_data(state_data)
```

## 预期收益
1.  **代码瘦身**: 预计减少 `VolatilityTrade` 约 300-400 行代码。
2.  **关注点分离**: 交易逻辑与基础设施解耦，便于独立测试交易逻辑。
3.  **可维护性**: 修改监控数据格式或数据库 schema 时，只需修改 `StrategyMonitor`，不影响核心策略文件。
