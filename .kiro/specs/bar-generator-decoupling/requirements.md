# 需求文档：K线生成器解耦

## 简介

当前 `StrategyEntry` 中的K线合成逻辑（`PortfolioBarGenerator`）与策略主体紧密耦合，散布在 `__init__`、`on_init`、`on_tick`、`on_bars`、`on_window_bars` 等多个方法中。`bar_window` 和 `bar_interval` 作为策略级参数存在，即使策略不需要K线合成也无法轻松移除。

本次重构的目标是将K线生成器抽取为一个可插拔的独立模块，使策略在需要合成K线时保留该模块，在不需要时（如仅依赖 tick 级别数据或原始1分钟K线）可以轻松删除相关代码，实现"混沌代码"（模块化、松耦合）而非"面条代码"（紧耦合）。

## 术语表

- **StrategyEntry**: 策略入口类，继承自 VnPy 的 `StrategyTemplate`，负责回调入口和领域逻辑编排
- **PortfolioBarGenerator (PBG)**: VnPy 提供的组合K线合成器，将 tick 或1分钟K线合成为指定周期的K线
- **BarPipeline**: 本次重构引入的K线数据流管道抽象，封装从原始数据到业务逻辑处理之间的数据变换链路
- **DirectBarPipeline**: BarPipeline 的直通实现，不做K线合成，直接将1分钟K线传递给业务逻辑
- **SyntheticBarPipeline**: BarPipeline 的合成实现，内部封装 PBG，将 tick 或1分钟K线合成为指定周期K线后传递给业务逻辑
- **bar_callback**: K线处理完成后的回调函数，签名为 `Callable[[Dict[str, BarData]], None]`

## 需求

### 需求 1：K线管道抽象接口

**用户故事：** 作为策略开发者，我希望有一个统一的K线数据流管道接口，以便策略入口无需关心K线是直接传递还是经过合成。

#### 验收标准

1. THE BarPipeline SHALL 定义统一的接口，包含 `handle_tick` 和 `handle_bars` 两个方法以及一个 `bar_callback` 属性
2. WHEN StrategyEntry 调用 BarPipeline 的 `handle_tick` 或 `handle_bars` 方法时，THE BarPipeline SHALL 将处理后的K线数据通过 `bar_callback` 回调传递给业务逻辑
3. THE BarPipeline 接口 SHALL 遵循策略模式（Strategy Pattern），使不同的K线处理策略可以互相替换

### 需求 2：直通管道实现

**用户故事：** 作为策略开发者，当我的策略只需要原始1分钟K线时，我希望使用一个不做任何合成的直通管道，以避免引入不必要的K线合成依赖。

#### 验收标准

1. WHEN DirectBarPipeline 接收到 bars 数据时，THE DirectBarPipeline SHALL 直接将 bars 数据原样传递给 bar_callback
2. WHEN DirectBarPipeline 接收到 tick 数据时，THE DirectBarPipeline SHALL 忽略该 tick 数据，不做任何处理
3. THE DirectBarPipeline SHALL 不依赖 VnPy 的 PortfolioBarGenerator 模块

### 需求 3：合成管道实现

**用户故事：** 作为策略开发者，当我的策略需要合成K线（如15分钟K线）时，我希望使用一个封装了 PBG 的合成管道，以便将K线合成逻辑集中管理。

#### 验收标准

1. WHEN SyntheticBarPipeline 被创建时，THE SyntheticBarPipeline SHALL 接收 `window`、`interval` 和 `bar_callback` 参数，并在内部创建 PortfolioBarGenerator 实例
2. WHEN SyntheticBarPipeline 接收到 tick 数据时，THE SyntheticBarPipeline SHALL 将 tick 数据传递给内部的 PortfolioBarGenerator 进行合成
3. WHEN SyntheticBarPipeline 接收到 bars 数据时，THE SyntheticBarPipeline SHALL 将 bars 数据传递给内部的 PortfolioBarGenerator 进行合成
4. WHEN PortfolioBarGenerator 完成K线合成时，THE SyntheticBarPipeline SHALL 通过 bar_callback 将合成后的K线传递给业务逻辑

### 需求 4：StrategyEntry 重构

**用户故事：** 作为策略开发者，我希望 StrategyEntry 通过 BarPipeline 接口与K线数据流交互，以便在不修改策略核心逻辑的情况下切换K线处理方式。

#### 验收标准

1. WHEN StrategyEntry 初始化时，THE StrategyEntry SHALL 根据配置参数创建对应的 BarPipeline 实现（有 bar_window 配置时创建 SyntheticBarPipeline，否则创建 DirectBarPipeline）
2. WHEN StrategyEntry 接收到 tick 回调时，THE StrategyEntry SHALL 将 tick 数据委托给 BarPipeline 的 `handle_tick` 方法
3. WHEN StrategyEntry 接收到 bars 回调时，THE StrategyEntry SHALL 将 bars 数据委托给 BarPipeline 的 `handle_bars` 方法，同时保留换月检查和补漏检查逻辑
4. THE StrategyEntry SHALL 不再直接持有 PortfolioBarGenerator 实例，也不再直接引用 `on_window_bars` 回调方法
5. WHEN 策略不需要K线合成功能时，THE StrategyEntry 中与K线合成相关的代码 SHALL 可以通过仅删除 SyntheticBarPipeline 文件和修改管道创建逻辑来移除

### 需求 5：历史数据回放兼容

**用户故事：** 作为策略开发者，我希望历史数据回放（warmup）流程能够与新的K线管道架构兼容，以便 warmup 数据也能正确地经过K线合成或直通处理。

#### 验收标准

1. WHEN 实盘 warmup 回放历史K线时，THE HistoryDataRepository SHALL 通过 BarPipeline 的 `handle_bars` 方法推送数据，而非直接调用 `on_bars`
2. WHEN 回测模式加载历史数据时，THE StrategyEntry SHALL 通过 BarPipeline 处理回放的K线数据
3. IF warmup 过程中 BarPipeline 处理数据失败，THEN THE StrategyEntry SHALL 记录错误日志并抛出异常终止初始化

### 需求 6：K线合成参数隔离

**用户故事：** 作为策略开发者，我希望K线合成相关的参数（bar_window、bar_interval）从策略级参数中移除，仅在需要合成K线时由 SyntheticBarPipeline 管理。

#### 验收标准

1. THE StrategyEntry SHALL 将 `bar_window` 和 `bar_interval` 参数从策略级 `parameters` 列表中移除
2. WHEN 使用 SyntheticBarPipeline 时，THE SyntheticBarPipeline SHALL 从策略配置（setting dict）中读取 `bar_window` 和 `bar_interval` 参数
3. WHEN 使用 DirectBarPipeline 时，THE DirectBarPipeline SHALL 不需要任何K线合成相关的参数
