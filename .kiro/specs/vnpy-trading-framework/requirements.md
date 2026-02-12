# Requirements Document

## Introduction

本文档定义了将现有 StockIndexVolatility 项目重构为通用的"基于 VNPY 的期货期权交易框架"的需求。该框架将采用 DDD（领域驱动设计）架构，使开发者能够专注于策略逻辑的实现，而无需关注基础设施细节。

## Glossary

- **System**: VNPY 期货期权交易框架
- **StrategyEngine**: 策略执行引擎（原 VolatilityTrade）
- **GenericStrategyAdapter**: 通用策略适配器（原 MacdTdIndexStrategy）
- **InstrumentManager**: 标的管理器（原 TargetInstrumentAggregate）
- **TargetInstrument**: 标的实体，存储合约信息和指标数据
- **ServiceBundle**: 服务包，包含所有策略所需的服务接口
- **ISignalService**: 信号生成服务接口
- **IIndicatorService**: 指标计算服务接口
- **IPositionSizingService**: 仓位计算服务接口
- **BaseFutureSelector**: 期货标的筛选基类
- **OptionSelectorService**: 期权选择服务
- **SPI**: Service Provider Interface，服务提供者接口

## Requirements

### Requirement 1: 领域层重构 - 实体与聚合根

**User Story:** 作为框架开发者，我希望将领域实体重构为通用模型，以便支持任意策略的实现。

#### Acceptance Criteria

1. THE System SHALL 保留 `position_aggregate.py` 作为核心聚合根，负责订单生命周期和持仓管理
2. THE System SHALL 将 `target_instrument_aggregate.py` 重构为 `InstrumentManager`，移除所有具体指标计算逻辑
3. THE System SHALL 保留 `order.py` 和 `position.py` 作为通用金融实体
4. THE System SHALL 将 `target_instrument.py` 重构为贫血模型，仅保留基础属性和 K 线队列维护逻辑
5. THE System SHALL 在 `TargetInstrument` 中新增 `indicators: Dict[str, Any]` 字典用于存储动态指标
6. THE System SHALL 从 `TargetInstrument` 中删除所有计算方法（如 `update_macd`、`check_dullness`）
7. THE System SHALL 保留 `order_instruction.py`，并将其 `signal` 字段类型修改为 `str`
8. THE System SHALL 废弃 `signal_type.py` 的枚举限制，改用字符串常量定义信号

### Requirement 2: 领域层重构 - 服务接口化

**User Story:** 作为策略开发者，我希望通过实现标准接口来定义策略逻辑，而不是修改框架代码。

#### Acceptance Criteria

1. THE System SHALL 定义 `ISignalService` 接口，包含 `check_open_signal` 和 `check_close_signal` 抽象方法
2. THE System SHALL 定义 `IIndicatorService` 接口，包含 `calculate_bar` 抽象方法
3. THE System SHALL 定义 `IPositionSizingService` 接口，包含 `calculate_open_volume` 和 `calculate_exit_volume` 抽象方法
4. THE System SHALL 将 `future_selection_service.py` 重构为 `BaseFutureSelector` 基类
5. THE System SHALL 在 `BaseFutureSelector` 中提供 `select_dominant_contract` 和 `filter_by_maturity` 方法
6. THE System SHALL 保留并增强 `option_selector_service.py`，支持 CALL/PUT 类型选择
7. THE System SHALL 删除 `calculation_service` 目录下的所有具体实现文件

### Requirement 3: InstrumentManager 重构

**User Story:** 作为框架开发者，我希望 InstrumentManager 成为纯粹的标的容器，不包含任何业务逻辑。

#### Acceptance Criteria

1. THE System SHALL 保留 `InstrumentManager` 的初始化、标的查询和工厂方法
2. THE System SHALL 保留 `set_active_contract`、`get_active_contract` 和 `get_all_active_contracts` 方法
3. THE System SHALL 保留 `update_bar` 方法，仅负责调用 `instrument.append_bar`
4. THE System SHALL 删除 `update_indicators` 方法及其所有参数透传逻辑
5. THE System SHALL 保留所有辅助查询方法（`get_bar_history`、`get_latest_price`、`has_enough_data` 等）
6. THE System SHALL 确保 `InstrumentManager` 不引用任何特定的 SignalType 或指标类型

### Requirement 4: 应用层重构 - StrategyEngine

**User Story:** 作为框架开发者，我希望将 VolatilityTrade 重构为通用的 StrategyEngine，通过依赖注入支持任意策略。

#### Acceptance Criteria

1. THE System SHALL 将 `VolatilityTrade` 重命名为 `StrategyEngine`
2. THE System SHALL 在 `StrategyEngine.__init__` 中接受所有服务接口作为依赖注入参数
3. THE System SHALL 从 `StrategyEngine` 中删除所有硬编码的服务实例化逻辑
4. THE System SHALL 重构 `handle_bar_update` 方法，删除所有具体的 MACD、背离、钝化逻辑
5. THE System SHALL 在 `handle_bar_update` 中调用 `IIndicatorService.calculate_bar` 更新指标
6. THE System SHALL 在 `handle_bar_update` 中调用 `ISignalService.check_open_signal` 和 `check_close_signal` 生成信号
7. THE System SHALL 重构 `_check_and_execute_open` 和 `_check_and_execute_close` 方法，移除具体的期权选择逻辑
8. THE System SHALL 删除 `_select_option`、`_get_option_contracts` 等特定策略方法
9. THE System SHALL 将风控计数逻辑委托给 `IPositionSizingService`
10. THE System SHALL 保留事件发布、告警机制和生命周期管理方法

### Requirement 5: 策略入口改造 - GenericStrategyAdapter

**User Story:** 作为策略开发者，我希望通过继承 GenericStrategyAdapter 并实现 setup_services 方法来快速创建新策略。

#### Acceptance Criteria

1. THE System SHALL 将 `MacdTdIndexStrategy` 重命名为 `GenericStrategyAdapter`
2. THE System SHALL 定义 `ServiceBundle` 数据类，包含所有必需的服务接口字段
3. THE System SHALL 在 `GenericStrategyAdapter` 中定义抽象方法 `setup_services`，返回 `ServiceBundle`
4. THE System SHALL 在 `GenericStrategyAdapter.on_init` 中调用 `setup_services` 获取服务包
5. THE System SHALL 在 `GenericStrategyAdapter.on_init` 中实例化 `StrategyEngine` 并注入所有服务
6. THE System SHALL 从 `GenericStrategyAdapter` 中移除所有策略特定的成员变量和参数
7. THE System SHALL 保留 `GenericStrategyAdapter` 的生命周期方法（`on_start`、`on_stop`）
8. THE System SHALL 保留 `GenericStrategyAdapter` 的行情和交易回报透传方法

### Requirement 6: 运行时环境改造

**User Story:** 作为系统管理员，我希望运行时环境能够动态加载任意符合规范的策略类。

#### Acceptance Criteria

1. THE System SHALL 修改 `child_process.py`，使用固定入口 `StrategyEntry` 加载策略
2. THE System SHALL 约定所有策略必须在 `src/strategy/__init__.py` 中暴露 `StrategyEntry` 类
3. THE System SHALL 从 `parent_process.py` 中移除所有硬编码的策略名称
4. THE System SHALL 保留 `main.py`、`gateway.py` 和 `run_recorder.py` 的原有功能
5. THE System SHALL 增强 `config_loader.py`，使其返回完整的配置字典而不进行字段过滤
6. THE System SHALL 保留 `log_handler.py` 和 `contract_utils.py` 的通用工具功能

### Requirement 7: 回测与配置适配

**User Story:** 作为策略开发者，我希望回测系统能够支持新的策略加载方式。

#### Acceptance Criteria

1. THE System SHALL 修改 `run_backtesting.py`，适配新的 `StrategyEntry` 加载方式
2. THE System SHALL 清理 `strategy_config.yaml`，分离通用配置与策略参数
3. THE System SHALL 确保回测系统能够正确加载和执行基于 `GenericStrategyAdapter` 的策略

### Requirement 8: 文件清理与结构调整

**User Story:** 作为框架维护者，我希望项目结构清晰，只包含框架核心代码。

#### Acceptance Criteria

1. THE System SHALL 删除 `data/` 目录下的所有运行时数据
2. THE System SHALL 保留 `src/`、`config/`、`scripts/` 核心目录
3. THE System SHALL 创建 `src/strategy/domain/interface/` 目录存放 SPI 接口定义
4. THE System SHALL 创建 `src/strategy/domain/impl/` 目录存放示例实现
5. THE System SHALL 删除所有特定策略的值对象文件（`*_value.py`、`*_state.py`）

### Requirement 9: 示例策略实现

**User Story:** 作为新用户，我希望有一个完整的示例策略，展示如何使用框架开发自定义策略。

#### Acceptance Criteria

1. THE System SHALL 提供示例 `IIndicatorService` 实现，展示如何计算指标并更新 `indicators` 字典
2. THE System SHALL 提供示例 `ISignalService` 实现，展示如何读取指标并生成信号
3. THE System SHALL 提供示例 `IPositionSizingService` 实现，展示如何进行仓位计算和风控检查
4. THE System SHALL 提供示例策略入口类，展示如何继承 `GenericStrategyAdapter` 并实现 `setup_services`
5. THE System SHALL 在示例代码中包含详细的注释和文档字符串

### Requirement 10: 信号机制字符串化

**User Story:** 作为策略开发者，我希望能够使用自定义字符串定义信号类型，而不受枚举限制。

#### Acceptance Criteria

1. THE System SHALL 支持使用任意字符串作为信号标识
2. THE System SHALL 在日志、消息推送和数据库中原样记录信号字符串
3. THE System SHALL 在文档中建议使用 `ACTION_REASON_DETAIL` 命名规范
4. THE System SHALL 在示例代码中展示信号字符串的定义方式（如 `SELL_CALL_DIVERGENCE_TD9 = "sell_call_divergence_td9"`）
5. THE System SHALL 确保框架层对信号内容不做解析，仅负责透传

### Requirement 11: 接口文档与开发者指南

**User Story:** 作为策略开发者，我希望有清晰的文档指导我如何使用框架开发策略。

#### Acceptance Criteria

1. THE System SHALL 提供完整的 API 文档，描述所有 SPI 接口的方法签名和职责
2. THE System SHALL 提供开发者指南，说明策略开发的标准流程
3. THE System SHALL 在文档中说明贫血模型的设计理念和使用方式
4. THE System SHALL 在文档中说明 `indicators` 字典的使用约定
5. THE System SHALL 提供配置文件模板和参数说明
