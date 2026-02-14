# 实施任务：K线生成器解耦

## 任务 1：创建 BarPipeline 具体类

- [ ] 1.1 创建 `src/strategy/infrastructure/bar_pipeline/` 目录及 `__init__.py`
- [ ] 1.2 创建 `src/strategy/infrastructure/bar_pipeline/bar_pipeline.py`，实现 BarPipeline 具体类
  - 接收 `bar_callback`、`window`、`interval` 参数
  - 内部创建 PortfolioBarGenerator 实例
  - 实现 `handle_tick(tick)` 方法，将 tick 传递给 PBG
  - 实现 `handle_bars(bars)` 方法，将 bars 传递给 PBG
  - PBG 合成完成后通过 `bar_callback` 输出
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

## 任务 2：重构 StrategyEntry

- [ ] 2.1 从 StrategyEntry 的 `parameters` 列表中移除 `bar_window` 和 `bar_interval`
  - **Validates: Requirements 4.1**
- [ ] 2.2 重构 `on_init`：根据 setting 中的 `bar_window` 决定是否创建 BarPipeline
  - `bar_window` 为正整数时创建 BarPipeline 实例（从 setting 读取参数）
  - `bar_window` 为 0 或不存在时不创建任何管道实例
  - **Validates: Requirements 3.1, 4.2, 4.3**
- [ ] 2.3 重构 `on_bars`：根据是否持有 BarPipeline 选择路径
  - 有 BarPipeline 时委托给 `bar_pipeline.handle_bars(bars)`
  - 无 BarPipeline 时直接调用 `_process_bars(bars)`（保留换月检查和补漏检查）
  - **Validates: Requirements 1.1, 3.2**
- [ ] 2.4 重构 `on_tick`：根据是否持有 BarPipeline 选择路径
  - 有 BarPipeline 时委托给 `bar_pipeline.handle_tick(tick)`
  - 无 BarPipeline 时不做任何K线相关处理
  - **Validates: Requirements 1.3, 3.3**
- [ ] 2.5 移除 `on_window_bars` 方法和直接持有的 `self.pbg` 属性
  - **Validates: Requirements 3.4**

## 任务 3：历史数据回放兼容

- [ ] 3.1 重构实盘 warmup 回放路径
  - 有 BarPipeline 时，回放回调通过 `bar_pipeline.handle_bars` 推送数据
  - 无 BarPipeline 时，回放回调直接调用 `on_bars`
  - **Validates: Requirements 5.1, 5.2**
- [ ] 3.2 确认回测模式通过 `on_bars` 路径处理回放K线（`load_bars` 已走 `on_bars`）
  - **Validates: Requirements 5.3**
- [ ] 3.3 在 warmup 过程中添加 BarPipeline 异常处理：记录错误日志并抛出异常终止初始化
  - **Validates: Requirements 5.4**

## 任务 4：单元测试

- [ ] 4.1 编写 BarPipeline 单元测试
  - 构造函数参数验证
  - `handle_tick` 将 tick 委托给 PBG（mock PBG）
  - `handle_bars` 将 bars 委托给 PBG（mock PBG）
  - PBG 回调链路正确性
- [ ] 4.2 编写 StrategyEntry 重构后的单元测试
  - 无 `bar_window` 时 `on_bars` 直接调用 `_process_bars`（mock）
  - 有 `bar_window` 时 `on_bars` 委托给 BarPipeline（mock BarPipeline）
  - 无 `bar_window` 时不持有 BarPipeline 或 PBG 实例
  - `bar_window`/`bar_interval` 不在 `parameters` 列表中

## 任务 5：属性测试（Property-Based Testing）

- [ ] 5.1 Property 1: DirectBarPipeline 恒等传递 — 无 BarPipeline 时 `on_bars` 直接传递 bars 给 `_process_bars`，输入输出完全一致
  - Tag: `Feature: bar-generator-decoupling, Property 1: 直通路径恒等传递`
  - **Validates: Requirements 1.1**
- [ ] 5.2 Property 2: 无 BarPipeline 时忽略 tick — 无 BarPipeline 时 `on_tick` 不触发任何K线回调
  - Tag: `Feature: bar-generator-decoupling, Property 2: 直通路径忽略 tick`
  - **Validates: Requirements 1.3**
- [ ] 5.3 Property 3: BarPipeline 创建条件 — `bar_window` 为正整数时创建 BarPipeline，为 0/负数/不存在时不创建
  - Tag: `Feature: bar-generator-decoupling, Property 3: BarPipeline 创建条件`
  - **Validates: Requirements 3.1, 1.2**
