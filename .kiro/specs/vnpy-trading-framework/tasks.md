# Implementation Plan: VNPY 期货期权交易框架

## Overview

本实施计划将现有 StockIndexVolatility 项目重构为通用的 VNPY 期货期权交易框架。重构采用增量方式，优先建立核心接口和数据结构，然后逐步迁移现有功能，最后提供示例实现和文档。

## Tasks

- [x] 1. 创建核心 SPI 接口定义
  - 创建 `src/strategy/domain/interface/` 目录
  - 定义 `IIndicatorService`、`ISignalService`、`IPositionSizingService` 接口
  - 定义 `ServiceBundle` 数据类
  - _Requirements: 2.1, 2.2, 2.3, 5.2_

- [x] 1.1 编写接口定义的单元测试
  - 测试接口是否可被正确继承
  - 测试 ServiceBundle 的字段完整性
  - _Requirements: 5.2_

- [x] 2. 重构 TargetInstrument 实体为贫血模型
  - [x] 2.1 在 TargetInstrument 中添加 `indicators: Dict[str, Any]` 字段
    - 修改 `src/strategy/domain/entity/target_instrument.py`
    - 删除所有计算方法（update_macd, check_dullness 等）
    - 保留基础属性和 K 线队列方法
    - _Requirements: 1.4, 1.5, 1.6_

  - [x] 2.2 编写 TargetInstrument 的属性测试
    - **Property 2: TargetInstrument indicators 字典可写入**
    - **Validates: Requirements 1.5**

- [ ] 3. 重构 InstrumentManager（原 TargetInstrumentAggregate）
  - [x] 3.1 重命名类并清理方法
    - 将 `TargetInstrumentAggregate` 重命名为 `InstrumentManager`
    - 删除 `update_indicators` 方法
    - 确保不引用任何特定的 SignalType
    - _Requirements: 1.2, 3.4, 3.6_

  - [ ]* 3.2 编写 InstrumentManager 的属性测试
    - **Property 1: InstrumentManager 合约管理一致性**
    - **Validates: Requirements 3.2**
    - **Property 6: InstrumentManager K 线更新**
    - **Validates: Requirements 3.3**

- [x] 4. 修改 OrderInstruction 信号字段类型
  - 将 `signal_type` 字段改为 `signal: str`
  - 更新所有引用该字段的代码
  - _Requirements: 1.7, 1.8_

- [ ]* 4.1 编写信号字符串透传的属性测试
  - **Property 3: 信号字符串透传**
  - **Validates: Requirements 10.1, 10.2, 10.5**

- [x] 5. Checkpoint - 确保领域层重构完成
  - 确保所有测试通过，询问用户是否有问题

- [ ] 6. 重构 BaseFutureSelector 基类
  - [x] 6.1 将 `FutureSelectionService` 重构为 `BaseFutureSelector`
    - 保留 `select_dominant_contract` 和 `filter_by_maturity` 方法
    - 移除特定策略逻辑
    - _Requirements: 2.4, 2.5_

  - [ ]* 6.2 编写 BaseFutureSelector 的属性测试
    - **Property 7: BaseFutureSelector 主力合约选择**
    - **Validates: Requirements 2.5**

- [ ] 7. 增强 OptionSelectorService
  - [x] 7.1 添加 CALL/PUT 类型选择支持
    - 修改 `select_option` 方法签名
    - 支持 option_type 参数（"CALL" | "PUT"）
    - _Requirements: 2.6_

  - [ ]* 7.2 编写 OptionSelectorService 的属性测试
    - **Property 8: OptionSelectorService 类型支持**
    - **Validates: Requirements 2.6**

- [ ] 8. 重构 StrategyEngine（原 VolatilityTrade）
  - [x] 8.1 重命名类并修改构造函数
    - 将 `VolatilityTrade` 重命名为 `StrategyEngine`
    - 修改 `__init__` 接受服务接口作为依赖注入
    - 删除硬编码的服务实例化
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 8.2 重构 handle_bar_update 方法
    - 删除具体的 MACD、背离、钝化计算逻辑
    - 调用 `IIndicatorService.calculate_bar`
    - 调用 `ISignalService.check_open_signal` 和 `check_close_signal`
    - _Requirements: 4.4, 4.5, 4.6_

  - [x] 8.3 重构开平仓方法
    - 简化 `_check_and_execute_open` 和 `_check_and_execute_close`
    - 删除 `_select_option`、`_get_option_contracts` 方法
    - 将风控逻辑委托给 `IPositionSizingService`
    - _Requirements: 4.7, 4.8, 4.9_

  - [ ]* 8.4 编写 StrategyEngine 的属性测试
    - **Property 5: StrategyEngine 服务调用**
    - **Validates: Requirements 4.5, 4.6**

- [x] 9. Checkpoint - 确保应用层重构完成
  - 确保所有测试通过，询问用户是否有问题

- [ ] 10. 创建 GenericStrategyAdapter 基类
  - [x] 10.1 重命名并实现抽象方法
    - 将 `StrategyEntry` 重命名为 `GenericStrategyAdapter`
    - 定义抽象方法 `setup_services() -> ServiceBundle`
    - 实现 `on_init` 方法，调用 `setup_services` 并实例化 `StrategyEngine`
    - 删除所有策略特定的成员变量
    - _Requirements: 5.1, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 10.2 编写 GenericStrategyAdapter 的单元测试
    - 测试 `on_init` 是否正确调用 `setup_services`
    - 测试 `StrategyEngine` 是否被正确实例化
    - _Requirements: 5.4, 5.5_

- [ ] 11. 修改运行时环境
  - [x] 11.1 修改 child_process.py
    - 使用固定入口 `StrategyEntry` 加载策略
    - 删除硬编码的策略类导入
    - _Requirements: 6.1_

  - [x] 11.2 修改 parent_process.py
    - 移除硬编码的策略名称
    - _Requirements: 6.3_

  - [x] 11.3 增强 config_loader.py
    - 修改 `load_strategy_config` 返回完整配置字典
    - 不进行字段过滤
    - _Requirements: 6.5_

  - [ ]* 11.4 编写配置加载的属性测试
    - **Property 12: 配置加载完整性**
    - **Validates: Requirements 6.5**

- [ ] 12. 修改回测系统
  - [x] 12.1 适配 run_backtesting.py
    - 使用 `StrategyEntry` 加载策略
    - _Requirements: 7.1_

  - [ ]* 12.2 编写回测系统的集成测试
    - **Property 13: 回测系统策略加载**
    - **Validates: Requirements 7.3**

- [x] 13. Checkpoint - 确保运行时环境改造完成
  - 确保所有测试通过，询问用户是否有问题

- [ ] 14. 创建示例实现
  - [x] 14.1 创建 `src/strategy/domain/impl/` 目录
    - _Requirements: 8.4_

  - [x] 14.2 实现示例 IIndicatorService
    - 创建 `demo_indicator_service.py`
    - 实现 MACD 指标计算
    - 更新 `instrument.indicators` 字典
    - 包含详细注释
    - _Requirements: 9.1, 9.5_

  - [ ]* 14.3 编写示例 IIndicatorService 的属性测试
    - **Property 9: 示例 IIndicatorService 正确性**
    - **Validates: Requirements 9.1**

  - [x] 14.4 实现示例 ISignalService
    - 创建 `demo_signal_service.py`
    - 从 `indicators` 字典读取数据
    - 生成信号字符串
    - 包含详细注释
    - _Requirements: 9.2, 9.5_

  - [ ]* 14.5 编写示例 ISignalService 的属性测试
    - **Property 10: 示例 ISignalService 正确性**
    - **Validates: Requirements 9.2**

  - [x] 14.6 实现示例 IPositionSizingService
    - 创建 `demo_position_sizing_service.py`
    - 实现固定手数或比例仓位计算
    - 包含风控检查逻辑
    - 包含详细注释
    - _Requirements: 9.3, 9.5_

  - [ ]* 14.7 编写示例 IPositionSizingService 的属性测试
    - **Property 11: 示例 IPositionSizingService 正确性**
    - **Validates: Requirements 9.3**

  - [x] 14.8 创建示例策略入口类
    - 创建 `demo_strategy.py`
    - 继承 `GenericStrategyAdapter`
    - 实现 `setup_services` 方法
    - 在 `src/strategy/__init__.py` 中暴露为 `StrategyEntry`
    - 包含详细注释
    - _Requirements: 9.4, 9.5, 6.2_

  - [ ]* 14.9 编写示例策略的集成测试
    - 测试示例策略是否能正常初始化
    - 测试示例策略是否能处理 K 线数据
    - _Requirements: 9.4_

- [ ] 15. 文件清理
  - [x] 15.1 删除特定策略的值对象文件
    - 删除 `macd_value.py`、`td_value.py`、`ema_state.py`
    - 删除 `dullness_state.py`、`divergence_state.py`
    - 删除 `signal_type.py`（枚举）
    - _Requirements: 1.8, 8.5_

  - [x] 15.2 删除 calculation_service 目录
    - 删除 `src/strategy/domain/domain_service/calculation_service/`
    - _Requirements: 2.7_

  - [x] 15.3 清理运行时数据
    - 删除 `data/` 目录下的运行时数据（保留目录结构）
    - _Requirements: 8.1_

- [ ] 16. 最终集成测试
  - [x] 16.1 端到端测试
    - 测试示例策略能否在实际环境中运行
    - 测试回测系统能否正确执行示例策略
    - 测试配置加载和服务注入流程

  - [x] 16.2 性能测试
    - 测试框架开销是否在可接受范围内
    - 测试 indicators 字典的读写性能

- [x] 17. Final Checkpoint
  - 确保所有测试通过，询问用户是否有问题

## Notes

- 任务标记 `*` 的为可选测试任务，可根据需要跳过以加快 MVP 开发
- 每个任务都引用了具体的需求编号，确保可追溯性
- Checkpoint 任务确保增量验证，及时发现问题
- 属性测试使用 Hypothesis 库，每个测试至少运行 100 次迭代
- 单元测试使用 pytest 框架
- 重构过程中保持代码可运行，避免长时间的不可用状态
