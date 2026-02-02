# mysql_flask_socketio：信号快照入库 + Flask-SocketIO 实时前端

## 1. 背景与目标

### 1.1 背景
- 当前 Web 监控（`src/interface/web`）通过读取 `data/monitor/snapshot_*.pkl` 展示策略状态；前端用轮询拉取 `/api/data/<variant>`。
- Pickle 作为“进程间数据传输介质”存在问题：
  - 反序列化风险与兼容性问题（依赖类定义、路径、版本）
  - 无法天然支持多机部署/多实例并行
  - 扩展实时推送（多客户端）时会放大轮询成本

### 1.2 目标
- **策略直接输出信号**，Web/前端只负责展示，不在 Web 侧重算信号。
- **MySQL 存信号快照**：用 1 张快照表承载“当前态”，用 1 张事件表承载“发生过什么”。
- 行情与信号解耦：
  - 行情：从 VnPy MySQL Bar 数据按需取（缩放/分页/区间查询）
  - 信号：从策略快照/事件流取（状态灯、列表、告警、信号点位）
- 使用 **Flask-SocketIO** 将“客户端轮询”升级为“服务端推送”，支持多客户端实时展示。

### 1.3 非目标
- 不改变交易逻辑、指标公式与信号定义。
- 不将交易执行/风控决策迁移到 Web 服务。
- 不要求一次性改完所有 UI；先保证链路正确与可扩展。

---

## 2. 设计总览

### 2.1 数据流（推荐形态）
- **策略进程（VnPy 策略）**
  - 计算：bars -> 指标 -> 状态 -> 信号
  - 输出：
    - 写入 MySQL：`monitor_signal_snapshot`（当前态）
    - 写入 MySQL：`monitor_signal_event`（事件流）
- **Web 服务（Flask + SocketIO）**
  - 读 MySQL 快照与事件
  - 对外：
    - REST：按需查询（bars、事件历史、初始快照）
    - SocketIO：将“快照更新/新事件”推送给订阅的前端
- **浏览器前端**
  - 首屏：拉一次“最新快照”渲染状态与列表
  - 图表：按需拉 bars + 同区间事件点位叠加
  - 实时：SocketIO 接收更新并增量刷新

### 2.2 为什么要“两张表”
- **快照表**：解决“当前状态是什么”（状态灯/列表/摘要），一条记录覆盖一个策略实例的最新态，支持首屏快速渲染。
- **事件表**：解决“发生过什么”（可回看/可画点位/可审计），只记录状态翻转与信号产生，避免重复刷屏。

---

## 3. MySQL 表设计

> 说明：以下表独立于 VnPy 的 Bar 表（如 `dbbardata`）。Bar 表继续由 VnPy 侧维护；监控表只存“信号与状态”。

### 3.1 命名与主键策略
- `variant`：策略变体/实例名称（当前代码中的 `variant_name` / `strategy_name`）。
- `instance_id`：同一个 `variant` 在多机/多进程并行时的实例标识。
  - 单机单实例可填固定值（如 `default`），但建议从一开始就保留字段以避免未来数据串写。

### 3.2 快照表：monitor_signal_snapshot

#### 3.2.1 表结构（DDL 草案）
```sql
CREATE TABLE IF NOT EXISTS monitor_signal_snapshot (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  variant VARCHAR(64) NOT NULL,
  instance_id VARCHAR(64) NOT NULL,
  updated_at DATETIME(6) NOT NULL,
  bar_dt DATETIME(6) NULL,
  bar_interval VARCHAR(16) NULL,
  bar_window INT NULL,
  payload_json JSON NOT NULL,
  UNIQUE KEY uk_variant_instance (variant, instance_id),
  KEY idx_updated_at (updated_at),
  KEY idx_bar_dt (bar_dt)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 3.2.2 payload_json（推荐 schema）
- 顶层字段（建议固定）：
  - `timestamp`：快照生成时间（字符串或 datetime）
  - `variant`：同表字段冗余一份（便于调试）
  - `calc`：计算上下文
    - `bar_dt`：本次计算对应的 window bar 时间
    - `bar_interval` / `bar_window`
  - `instruments`：`vt_symbol -> instrument_state`
  - `positions_summary`：持仓摘要（数量、方向汇总等）
  - `orders_summary`：挂单摘要（数量、拒单等）
  - `alerts_summary`：可选（最近 N 条告警摘要）

#### 3.2.3 instrument_state（建议字段）
- `vt_symbol`
- `calc_bar_dt`：该合约最新计算的 bar_dt（可与全局 bar_dt 一致或略有差异）
- `status`
  - `dull_top`, `dull_bottom`, `div_top`, `div_bottom`
  - 其它未来状态（如 potential）可扩展
- `td_count`：TD 计数（用于列表排序/高亮）
- `last_signal`
  - `signal_type`：对应 `SignalType.value`
  - `reason`：简短原因（用于 tooltip）
  - `bar_dt`
- `last_price`：可选（用于列表展示）

#### 3.2.4 快照大小约束（强约束）
- 快照表只承载“最新态摘要”，不要塞入完整 K 线数组、长指标序列等。
- 任何“时间序列展示（图表）”都走 bars 表或事件表的区间查询。

### 3.3 事件表：monitor_signal_event

#### 3.3.1 表结构（DDL 草案）
```sql
CREATE TABLE IF NOT EXISTS monitor_signal_event (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  variant VARCHAR(64) NOT NULL,
  instance_id VARCHAR(64) NOT NULL,
  vt_symbol VARCHAR(64) NOT NULL,
  bar_dt DATETIME(6) NULL,
  event_type VARCHAR(32) NOT NULL,
  event_key VARCHAR(192) NOT NULL,
  created_at DATETIME(6) NOT NULL,
  payload_json JSON NOT NULL,
  UNIQUE KEY uk_event_key (event_key),
  KEY idx_variant_created (variant, created_at),
  KEY idx_symbol_bar (vt_symbol, bar_dt),
  KEY idx_type_created (event_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 3.3.2 event_type 约定
- `signal`：开/平仓信号生成（离散事件）
- `state_change`：状态翻转（如 div_top false→true）
- `alert`：告警（如手动开平仓、风控触发）
- `order`：订单相关（可选）

#### 3.3.3 event_key（幂等与去重）
事件落库必须幂等，否则重启/回放/重复推送会造成事件爆炸。

推荐 event_key 组合：
- `signal`：`{variant}|{instance}|{vt_symbol}|{bar_dt}|{signal_type}`
- `state_change`：`{variant}|{instance}|{vt_symbol}|{bar_dt}|{state_name}|{old}->{new}`
- `alert`：`{variant}|{instance}|{vt_symbol}|{timestamp}|{alert_type}`

#### 3.3.4 payload_json（推荐）
- `signal`
  - `signal_type`（SignalType.value）
  - `reason`
  - `bar_dt`
  - `price_hint`（可选）
- `state_change`
  - `state_name`（如 div_top）
  - `old_value` / `new_value`
  - `bar_dt`
- `alert`
  - `alert_type` / `message` / `timestamp`
  - `vt_symbol` / `volume` / `extra`

---

## 4. 策略侧：写入快照与事件的时机

### 4.1 快照写入时机（建议）
- **按“计算完成”写入**：每次 window bar 更新、指标与状态完成更新后，写一次快照。
- **按“交易状态变化”补写**：订单/成交/持仓更新后也写快照，但建议做节流（例如 0.5~1s 合并）以减少 DB 写放大。

### 4.2 事件写入时机（建议）
- `signal`：检测到开/平仓信号时写入（对齐 `SignalType`）。
- `state_change`：状态翻转时写入（例如背离确认从 false→true）。
- `alert`：已有告警发布点可复用（策略内部已有 `StrategyAlertData`/`EVENT_STRATEGY_ALERT`）。

### 4.3 关键一致性：bar_dt 对齐
- 快照和事件都应带 `bar_dt`，且优先使用“window bar 的 datetime”（而不是 `now()`）。
- 前端画点位时以 bars 的 datetime 轴对齐事件 `bar_dt`，避免“信号点漂移”。

---

## 5. Web 侧：REST + SocketIO 的职责边界

### 5.1 REST 接口（建议最小集合）
- `GET /api/snapshot/<variant>`：返回快照表中该 variant 的最新快照（首屏用）
- `GET /api/events/<variant>?vt_symbol=&start=&end=&type=`：区间查询事件（画点位/告警列表）
- `GET /api/bars?vt_symbol=&start=&end=&interval=`：区间查询行情 bars（缩放/分页/按需）

### 5.2 SocketIO 推送（建议事件）
- `snapshot_update`：当某个 variant 的快照更新时推送（payload = 最新快照摘要或完整 payload_json）
- `event_new`：当写入新事件时推送（payload = 单条事件）

### 5.3 room 设计（建议）
- 基础：按 `variant` 分 room
  - 客户端订阅某个 variant：加入 `room:variant:<variant>`
- 可选：按 `variant + vt_symbol` 分 room（当图表拆分、只看少数合约时再做）

---

## 6. SocketIO 的两种实现方式（推荐从简单开始）

### 6.1 方式 A：Web 服务轮询 DB（简单稳）
- Web 启动一个后台任务：
  - 定期检查 `monitor_signal_snapshot.updated_at` 是否变化
  - 变化则向对应 room emit `snapshot_update`
  - 同时可按 `monitor_signal_event.id` 增量扫新事件并 emit `event_new`
- 优点：
  - 策略不需要知道 Web 地址与连接管理
  - 支持策略与 Web 分机部署（只要连同一个 MySQL）
- 注意：
  - 轮询频率建议 0.5~2s；用“版本号/时间戳”避免每次都拉大 payload

### 6.2 方式 B：策略直推 Web（更实时但耦合）
- 策略在写 DB 的同时，作为 SocketIO client 连接 Web 服务并 emit 更新
- 优点：延迟更低
- 缺点：策略侧要处理断线重连、鉴权、Web 地址配置；部署与排障复杂度更高

---

## 7. 运行与扩展注意事项

### 7.1 多进程/多机部署
- Web 若采用多进程（例如 gunicorn workers），SocketIO 广播通常需要消息队列（如 Redis）做跨进程 fanout。
- 单机开发阶段可先单进程运行，待需要扩展再引入 Redis。

### 7.2 数据保留与清理
- 快照表：每个 `(variant, instance_id)` 仅保留最新 1 行（UPSERT 覆盖）。
- 事件表：按时间保留（如 30/90 天），定期清理或分区。

### 7.3 安全
- Web 的 REST 与 SocketIO 若暴露到公网，需要鉴权（token / session）。
- 事件 payload 避免包含敏感凭证/账户信息；只存业务摘要。

---

## 8. 迁移路径（从 pickle 快照到 MySQL 快照）

### 8.1 迁移阶段建议
1) 新增 MySQL 两张表（快照 + 事件）
2) 策略侧在现有 `_dump_snapshot` 逻辑旁路写入 MySQL（短期可“双写”）
3) Web 侧新增读取 MySQL 的 SnapshotReader，并与现有 pickle 读取并行（灰度切换）
4) 前端从轮询切到 SocketIO（仍保留手动刷新兜底）
5) 删除/停用 `snapshot_*.pkl` 写入与读取（最终态）

### 8.2 验证顺序建议
- 先验证快照链路：策略写入 -> Web 读取 -> 前端展示“状态灯/列表”
- 再验证事件链路：信号产生 -> 事件入库 -> 图表叠加点位
- 最后切 SocketIO：多客户端同时在线，更新延迟与负载符合预期

---

## 9. 验收标准

- 正确性
  - 前端显示的状态灯（钝化/背离/TD）与策略日志/运行状态一致
  - 信号点位与 bars 时间轴对齐（无明显漂移）
- 幂等性
  - 重启策略/重复推送不导致事件表重复插入（event_key 唯一约束生效）
- 性能
  - 多客户端在线时无“请求风暴”（SocketIO 推送取代客户端轮询）
  - 快照 payload 体积稳定，不随运行天数线性增长
- 可运维
  - 快照表始终只保留每个实例最新一条
  - 事件表可按时间清理，查询索引可满足常用筛选
