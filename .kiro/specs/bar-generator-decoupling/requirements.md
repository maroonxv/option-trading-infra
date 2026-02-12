# 需求文档：K线生成器解耦

## 简介

当前 `StrategyEntry` 中的K线合成逻辑（`PortfolioBarGenerator`）与策略主体紧密耦合，散布在 `__init__`、`on_init`、`on_tick`、`on_bars`、`on_window_bars` 等多个方法中。`bar_window` 和 `bar_interval` 作为策略级参数存在，即使策略不需要K线合成也无法轻松移除。

本次重构的目标是将K线合成逻辑从 StrategyEntry 中解耦，使其成为"混沌代码"（模块化、松耦合）而非"面条代码"（紧耦合）：

- **不需要K线合成时**：`on_bars()` 直接调用 `_process_bars()`，没有任何中间层
- **需要K线合成时**：使用一个具体的 `BarPipeline` 类（非抽象基类），放在基础设施层，封装 `PortfolioBarGenerator`
- 没有抽象基类、没有继承体系、没有工厂函数

## 术语表

- **StrategyEntry**: 策略入口类，继承自 VnPy 的 `StrategyTemplate`，负责回调入口和领域逻辑编排
- **PortfolioBarGenerator (PBG)**: VnPy 提供的组合K线合成器，将 tick 或1分钟K线合成为指定周期的K线
- **BarPipeline**: 基础设施层的一个具体类（非抽象基类），封装 PBG，提供K线合成功能
- **bar_callback**: K线处理完成后的回调函数，签名为 `Callable[[Dict[str, BarData]], None]`

## 需求

### 需求 1：无K线合成的直通路径

**用户故事：** 作为策略开发者，当我的策略只需要原始1分钟K线时，我希望 `on_bars()` 直接调用 `_process_bars()`，没有任何中间层或额外抽象。

#### 验收标准

1. WHEN StrategyEntry 未配置K线合成参数（无 `bar_window` 或 `bar_window` 为 0）时，THE StrategyEntry 的 `on_bars()` SHALL 在完成换月检查和补漏检查后直接调用 `_process_bars(bars)`
2. WHEN StrategyEntry 未配置K线合成时，THE StrategyEntry SHALL 不持有任何 BarPipeline 或 PortfolioBarGenerator 实例
3. WHEN StrategyEntry 未配置K线合成时，THE StrategyEntry 的 `on_tick()` SHALL 不做任何K线相关处理

### 需求 2：BarPipeline 具体实现

**用户故事：** 作为策略开发者，当我的策略需要自定义时间窗口K线（如15分钟K线）时，我希望使用一个具体的 BarPipeline 类来封装 PBG，而不需要抽象基类或继承体系。

#### 验收标准

1. THE BarPipeline SHALL 作为一个具体类（非抽象基类）实现，放置在基础设施层
2. WHEN BarPipeline 被创建时，THE BarPipeline SHALL 接收 `bar_callback`、`window` 和 `interval` 参数，并在内部创建 PortfolioBarGenerator 实例
3. WHEN BarPipeline 接收到 tick 数据时，THE BarPipeline SHALL 将 tick 数据传递给内部的 PortfolioBarGenerator 进行处理
4. WHEN BarPipeline 接收到 bars 数据时，THE BarPipeline SHALL 将 bars 数据传递给内部的 PortfolioBarGenerator 进行合成
5. WHEN PortfolioBarGenerator 完成K线合成时，THE BarPipeline SHALL 通过 bar_callback 将合成后的K线传递给业务逻辑

### 需求 3：StrategyEntry 重构

**用户故事：** 作为策略开发者，我希望 StrategyEntry 根据是否需要K线合成来选择直通路径或使用 BarPipeline，以便代码结构清晰且易于维护。

#### 验收标准

1. WHEN StrategyEntry 配置了有效的 `bar_window`（正整数）时，THE StrategyEntry SHALL 在 `on_init` 中创建 BarPipeline 实例
2. WHEN StrategyEntry 配置了 BarPipeline 时，THE StrategyEntry 的 `on_bars()` SHALL 将 bars 数据委托给 BarPipeline 的 `handle_bars` 方法
3. WHEN StrategyEntry 配置了 BarPipeline 时，THE StrategyEntry 的 `on_tick()` SHALL 将 tick 数据委托给 BarPipeline 的 `handle_tick` 方法
4. THE StrategyEntry SHALL 不再直接持有 PortfolioBarGenerator 实例，也不再定义 `on_window_bars` 回调方法
5. WHEN 策略不需要K线合成功能时，THE StrategyEntry 中与K线合成相关的代码 SHALL 可以通过删除 BarPipeline 文件和移除 `on_init` 中的创建逻辑来完全移除

### 需求 4：K线合成参数隔离

**用户故事：** 作为策略开发者，我希望K线合成相关的参数（bar_window、bar_interval）从策略级参数中移除，仅在需要合成K线时由 BarPipeline 管理。

#### 验收标准

1. THE StrategyEntry SHALL 将 `bar_window` 和 `bar_interval` 参数从策略级 `parameters` 列表中移除
2. WHEN 使用 BarPipeline 时，THE BarPipeline SHALL 从策略配置（setting dict）中读取 `bar_window` 和 `bar_interval` 参数
3. WHEN 不使用 BarPipeline 时，THE StrategyEntry SHALL 不需要任何K线合成相关的参数

### 需求 5：历史数据回放兼容

**用户故事：** 作为策略开发者，我希望历史数据回放（warmup）流程能够与新的K线架构兼容，以便 warmup 数据也能正确地经过K线合成或直通处理。

#### 验收标准

1. WHEN 实盘 warmup 回放历史K线且配置了 BarPipeline 时，THE HistoryDataRepository 的回放回调 SHALL 通过 BarPipeline 的 `handle_bars` 方法推送数据
2. WHEN 实盘 warmup 回放历史K线且未配置 BarPipeline 时，THE HistoryDataRepository 的回放回调 SHALL 直接调用 `on_bars`
3. WHEN 回测模式加载历史数据时，THE StrategyEntry SHALL 通过与实盘相同的 `on_bars` 路径处理回放的K线数据
4. IF warmup 过程中 BarPipeline 处理数据失败，THEN THE StrategyEntry SHALL 记录错误日志并抛出异常终止初始化
