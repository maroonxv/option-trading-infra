# src/strategy 期权交易基础设施优化方向（基于参考项目 SingleTargetMonitor / retrace-monitor）

## 1. 文档目的

本文件用于完整记录以下三部分优化方向，并作为后续分阶段改造的执行基线：

- 网关基础设施优化
- 交易执行链路优化
- 风控执行链路优化

输入来源：

- `temp/SingleTargetMonitor`
- `temp/retrace-monitor`
- 当前项目 `src/strategy`

对比日期：2026-03-06

## 2. 总体结论

- `SingleTargetMonitor` 更适合借鉴“实盘风控执行闭环”（风险识别 -> 任务生成 -> 下单/撤单 -> 任务推进 -> 通知/可视化）。
- `retrace-monitor` 更适合借鉴“状态机化交易流程 + notify_only 安全开关 + 回调数据归一化”。
- 当前 `src/strategy` 已具备较完整的领域服务和值对象，但主交易流程尚未把这些服务接入真实执行闭环，核心瓶颈不在“算法不足”，而在“编排缺失”。

## 3. 当前 src/strategy 基线与主要缺口

### 3.1 已具备能力

- 已初始化关键领域服务：`PositionSizingService`、`PortfolioRiskAggregator`、`SmartOrderExecutor`。
- 已具备网关层基础：行情、账户、执行、订单、报价、连接、事件等 gateway 类。
- 已有较多领域测试，尤其是风险与执行服务的属性测试。

### 3.2 关键缺口

- `MarketWorkflow` 的开仓/平仓主逻辑仍是“待实现”注释，尚未进入执行闭环。
- `SmartOrderExecutor` 有超时/重试能力，但未与 `on_order/on_trade` 的事件链路打通。
- 网关层缺少“统一订单状态域模型”和“邻近实值合约查询接口”，不利于期权实盘追价与特殊风控。
- 风控服务（止损、流动性、集中度、时间衰减）尚未纳入运行时强约束链路，当前更多是可调用能力。

## 4. 优化方向一：网关基础设施

### 4.1 建立统一 Gateway 装配入口

目标：

- 统一创建 adapter + market + trade + account + order gateway，避免在策略入口分散装配。

借鉴点：

- `retrace-monitor` 的 `GatewayInfrastructure` 与 `init_gateway_infrastructure`。

落地建议：

- 在 `src/strategy/infrastructure/gateway` 新增基础设施装配结构（可命名为 `GatewayInfra`），集中注入：
  - 运行引擎引用
  - 策略上下文引用
  - notify_only 开关

验收标准：

- `LifecycleWorkflow` 不再手工逐个 new 网关，而是单入口初始化。

### 4.2 引入 Adapter 级缓存与数据稳态处理

目标：

- 降低 tick 抖动、空值 tick 对交易决策和风控判断的干扰。

借鉴点：

- `SingleTargetMonitor` 的 `_tick_cache`、`_contract_cache`、`smooth_tick_snapshot`、`apply_open_price_map_to_positions`。

落地建议：

- 在 `VnpyGatewayAdapter` 增加：
  - tick 缓存
  - 合约缓存
  - tick 平滑函数（至少补齐 last/bid1/ask1 的缺失值）
- 对接持仓查询时增加“开仓均价修补”的可插拔策略（默认关闭，CTP 可启用）。

验收标准：

- 连续脏 tick 场景下，风控和下单计算不再频繁出现零价/空价异常。

### 4.3 统一订单状态映射与活动订单查询

目标：

- 让上层编排只处理领域状态，不直接耦合 vnpy 原始状态值。

借鉴点：

- `SingleTargetMonitor` `order_utils._STATUS_MAP` 与 `vnpy_order_to_status`。

落地建议：

- 新增订单状态映射模块，将 vnpy 状态统一映射为：
  - `PENDING`
  - `ACTIVE`
  - `TRADED`
  - `CANCELLED`
  - `REJECTED`
- `VnpyTradeExecutionGateway` 补充：
  - `get_order_status(vt_orderid)`
  - `get_all_active_order_statuses()`

验收标准：

- 上层超时/重试/撤单逻辑不再直接解析 vnpy 枚举字符串。

### 4.4 补齐期权邻近实值合约能力

目标：

- 支持特殊平仓、对冲替代、动态订阅扩展。

借鉴点：

- `SingleTargetMonitor` 的 `build_itm_neighbor_symbols` 与 `get_itm_neighbors`。

落地建议：

- 在当前 `VnpyMarketDataGateway` 增加 `get_itm_neighbors(vt_symbol, depth)`：
  - call 取更低行权价
  - put 取更高行权价
  - 同标的、同月份、同期权类型过滤

验收标准：

- 单测覆盖 call/put、深度不足、跨月份过滤等场景。

### 4.5 增加 notify_only 双保险

目标：

- 演练模式下从架构层保证“永不实单”。

借鉴点：

- `retrace-monitor` 在交易网关层拦截 `send_order/cancel_order`。

落地建议：

- 策略编排层检查一次 notify_only。
- 交易网关再硬拦截一次 notify_only。

验收标准：

- notify_only = true 时，不论上层是否误调用，网关均不向交易通道发单。

## 5. 优化方向二：交易执行链路

### 5.1 把“待实现”的开平仓流程接成闭环

目标：

- 将 `MarketWorkflow.process_bars` 中注释流程改为可执行链路。

落地建议（开仓）：

- 信号触发后执行顺序：
  - 选择期权合约（`OptionSelectorService`）
  - 计算仓位（`PositionSizingService`）
  - Greeks 风控检查（`PortfolioRiskAggregator.check_position_risk`）
  - 发送指令（`exec_gateway.send_order`）
  - 将订单写入 `PositionAggregate.add_pending_order`
  - 将订单注册到 `SmartOrderExecutor.register_order`

落地建议（平仓）：

- 信号触发后执行顺序：
  - 计算平仓指令（`PositionSizingService.calculate_close_volume`）
  - 发单
  - 托管订单生命周期

验收标准：

- 触发真实/模拟信号后可形成“指令 -> 发单 -> 订单/成交回报 -> 持仓更新”的完整闭环。

### 5.2 引入两阶段追价执行策略（QUEUE/TAKER）

目标：

- 在平仓执行上具备稳定成交能力，而非一次性限价单。

借鉴点：

- `SingleTargetMonitor` `LiquidationDecisionService.decide_next_action`
- `retrace-monitor` `_compute_next_close_price`

落地建议：

- 抽象成独立领域策略函数，输入：
  - 上次价格
  - bid1/ask1
  - pricetick
  - 当前模式（QUEUE/TAKER）
- 输出：
  - 本轮委托价
  - 下一模式

验收标准：

- 单测覆盖：
  - 首轮 bid1
  - 追价 +1tick
  - 触及 ask1 后切换 taker 并锁定。

### 5.3 接入超时撤单与重试

目标：

- 将已有 `SmartOrderExecutor` 能力从“存在”变成“运行中生效”。

落地建议：

- 在 tick 或定时器中定期执行：
  - `check_timeouts(now)` 获取待撤单
  - 调用网关撤单
  - `prepare_retry(...)` 生成重试指令并发新单
- 在 `on_order/on_trade` 中更新订单活动状态（filled/cancelled）。

验收标准：

- 订单超时后能自动撤单并重发，达到最大重试次数后触发事件告警。

### 5.4 事件归一化与回调守卫

目标：

- 防止回调数据缺字段或格式漂移导致内部状态异常。

借鉴点：

- `retrace-monitor` 的 `_validate_*` 与 `_normalize_*`。

落地建议：

- 在 `EventBridge` 的 `on_order/on_trade/on_position` 前增加 normalize/validate。
- 对缺失关键字段事件做告警并丢弃。

验收标准：

- 异常回报不会污染 `PositionAggregate` 状态。

## 6. 优化方向三：风控执行链路

### 6.1 风控从“评估”升级为“强约束执行”

目标：

- 让风控结果直接影响开仓/平仓行为，而非仅记录日志。

落地建议：

- 开仓前强制检查：
  - 持仓级 Greeks
  - 组合级 Greeks 预算
  - 流动性阈值
  - 集中度阈值
- 不通过则阻断下单并抛领域事件。

验收标准：

- 任一风控失败时不会发单，且有结构化告警事件。

### 6.2 引入“风险任务”机制（借鉴强平任务模型）

目标：

- 对需要持续执行的风控动作（止损、减仓、强平）提供可跟踪任务状态。

借鉴点：

- `SingleTargetMonitor` 的 `CloseTask` + `active_task` 循环。

落地建议：

- 新增风险任务实体（如 `RiskCloseTask`）字段：
  - target_volume
  - traded_volume
  - active_order_id
  - attempt_count
  - mode
  - status
- 在应用层统一循环处理任务，不把复杂状态塞进单次 signal 流程。

验收标准：

- 风控动作可以跨多个周期持续推进，支持中断/恢复/完成态。

### 6.3 品种维度风险聚合

目标：

- 风险判断从“单腿局部”提升到“品种/组合净敞口”。

借鉴点：

- `SingleTargetMonitor` 的 `evaluate_risk`（品种聚合 + 对冲比例保护）。

落地建议：

- 在现有 `PortfolioRiskAggregator` 之上增加“品种分桶”视图：
  - 每品种净风险 PnL / Greeks
  - 对冲比例保护逻辑
- 当品种敞口恢复安全区时可终止强平任务。

验收标准：

- 同品种对冲头寸不会被误杀，净风险恶化时会触发任务。

### 6.4 缺行情容错与暂停恢复

目标：

- 避免行情缺失时盲目发单。

借鉴点：

- `retrace-monitor` `missing_quote_rounds` + `pause_workflow`。

落地建议：

- 对关键行情字段（bid1/ask1/pricetick）引入连续缺失计数。
- 超阈值后暂停任务，等待恢复后再激活。

验收标准：

- 行情缺失期间不会继续追价发单。

## 7. 可观测性与通知方向

### 7.1 告警分层与节流

目标：

- 控制告警噪音并保留关键信息。

借鉴点：

- `SingleTargetMonitor` warning interval
- `retrace-monitor` trigger/order-intent cooldown

落地建议：

- 告警类型至少分为：
  - 触发告警
  - 意图告警
  - 成交通知
  - 异常告警
- 各类型独立节流窗口。

### 7.2 关键状态持久化（可选增强）

目标：

- 便于回放、监控与事故排查。

借鉴点：

- `retrace-monitor` 的 alert/order/trade/heartbeat 入库模式。

落地建议：

- 对执行链路关键节点落库：
  - 风险任务状态
  - 下单意图
  - 告警发送状态

## 8. 测试优化方向

### 8.1 先补“闭环测试”，再补“算法测试”

当前项目已有较多领域算法测试，但缺少策略运行闭环测试。

建议新增测试优先级：

- P0：
  - 开仓/平仓执行链路集成测试（含回调）
  - 超时撤单重试集成测试
  - notify_only 双保险测试
- P1：
  - 邻近实值合约选择测试
  - QUEUE/TAKER 价格演进测试
  - 缺行情暂停/恢复测试
- P2：
  - 品种聚合风险任务全流程测试

## 9. 分阶段实施计划（建议）

### 阶段 A（先打通）- 交易闭环最小可用

- 完成开平仓主流程编排接线
- 接入 `SmartOrderExecutor` 超时/重试
- 引入统一订单状态映射

交付结果：

- 策略可稳定完成“信号 -> 下单 -> 回报 -> 持仓更新”。

### 阶段 B（再强化）- 风控执行化

- 风控前置强约束
- 风险任务状态机
- 缺行情暂停恢复

交付结果：

- 风控从“计算指标”转为“可执行动作”。

### 阶段 C（可选增强）- 专项优化

- 邻近实值特别平仓逻辑
- 品种聚合风险管理
- 告警持久化与监控看板增强

交付结果：

- 实盘异常场景处理能力显著增强。

## 10. 实施注意事项

- 优先复用现有 `src/strategy/domain/domain_service` 能力，避免重复造轮子。
- 按“先闭环、再细化”的顺序推进，避免长期停留在局部重构。
- 每个阶段都要求“可回归测试 + 可观测日志 + 明确回滚点”。

## 11. 最终目标状态

`src/strategy` 目标架构应满足：

- 网关层：数据稳态、状态统一、可安全演练
- 应用层：存在明确执行状态机与风险任务管理
- 领域层：风控规则可复用、可测试、可解释
- 运维层：关键动作可追踪、可告警、可回放

达到后，策略基础设施即可支撑期权实盘所需的“稳定执行 + 可控风险 + 可运营”三要素。

