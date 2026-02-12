# Implementation Plan: Gateway Infrastructure Enhancement

## Overview

本实现计划将 Gateway 基础设施增强分解为可执行的编码任务。按照优先级顺序实现，先完成高优先级的核心功能，再实现中低优先级的扩展功能。所有实现使用 Python 语言，遵循现有代码风格。

## Tasks

- [x] 1. 创建新的值对象和增强现有值对象
  - [x] 1.1 创建 PositionSnapshot 值对象
    - 在 `src/strategy/domain/value_object/position_snapshot.py` 创建 dataclass
    - 包含字段: vt_symbol, direction, volume, frozen, price, pnl, yd_volume
    - _Requirements: 2.4_
  - [x] 1.2 增强 AccountSnapshot 值对象
    - 添加 frozen 和 accountid 字段
    - 创建 `src/strategy/domain/value_object/account_snapshot.py` 文件
    - _Requirements: 6.1_
  - [x] 1.3 增强 OrderInstruction 值对象
    - 添加 OrderType 枚举 (LIMIT, MARKET, FAK, FOK)
    - 添加 order_type 字段到 OrderInstruction
    - _Requirements: 5.5_
  - [x] 1.4 创建 ContractParams 值对象
    - 在 `src/strategy/domain/value_object/contract_params.py` 创建 dataclass
    - 包含字段: vt_symbol, size, pricetick, min_volume, max_volume
    - _Requirements: 7.3_
  - [x] 1.5 创建 QuoteRequest 值对象
    - 在 `src/strategy/domain/value_object/quote_request.py` 创建 dataclass
    - 包含字段: vt_symbol, bid_price, bid_volume, ask_price, ask_volume, bid_offset, ask_offset
    - _Requirements: 9.1_

- [x] 2. 实现 VnpyOrderGateway (高优先级)
  - [x] 2.1 创建 VnpyOrderGateway 类
    - 在 `src/strategy/infrastructure/gateway/vnpy_order_gateway.py` 创建类
    - 继承 VnpyGatewayAdapter
    - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2_
  - [x] 2.2 实现 get_order 方法
    - 封装 main_engine.get_order()
    - 处理 MainEngine 不可用的情况
    - _Requirements: 1.1, 1.4_
  - [x] 2.3 实现 get_all_orders 和 get_all_active_orders 方法
    - 封装 main_engine.get_all_orders() 和 get_all_active_orders()
    - _Requirements: 1.2, 1.3_
  - [x] 2.4 实现 get_trade 和 get_all_trades 方法
    - 封装 main_engine.get_trade() 和 get_all_trades()
    - _Requirements: 4.1, 4.2, 4.3_
  - [ ]* 2.5 编写 VnpyOrderGateway 属性测试
    - **Property 1: 查询结果一致性**
    - **Property 2: 活动状态筛选正确性**
    - **Validates: Requirements 1.1, 1.2, 1.3, 4.1, 4.2**

- [x] 3. 增强 VnpyAccountGateway (高优先级)
  - [x] 3.1 增强 get_account_snapshot 方法
    - 返回包含 frozen 字段的 AccountSnapshot
    - _Requirements: 6.2_
  - [x] 3.2 实现 get_account 方法
    - 按 vt_accountid 查询指定账户
    - _Requirements: 6.4_
  - [x] 3.3 实现 get_all_accounts 方法
    - 返回所有账户的 AccountSnapshot 列表
    - _Requirements: 6.3_
  - [x] 3.4 完善 get_position 方法
    - 返回完整的 PositionSnapshot 对象
    - 包含 volume, frozen, price, pnl, yd_volume 字段
    - _Requirements: 2.1, 2.3_
  - [x] 3.5 增强 get_all_positions 方法
    - 返回 PositionSnapshot 列表
    - _Requirements: 2.2_
  - [ ]* 3.6 编写 VnpyAccountGateway 属性测试
    - **Property 3: 持仓快照完整性**
    - **Validates: Requirements 2.1, 2.2, 6.2, 6.3, 6.4**

- [x] 4. 增强 VnpyTradeExecutionGateway (高优先级)
  - [x] 4.1 实现 convert_order_request 方法
    - 封装 main_engine.convert_order_request()
    - 支持 lock 和 net 参数
    - 处理 OffsetConverter 不可用的情况
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 4.2 增强 send_order 方法支持订单类型
    - 根据 order_type 设置 OrderPriceType, TimeCondition, VolumeCondition
    - 支持 LIMIT, MARKET, FAK, FOK 类型
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [ ]* 4.3 编写 VnpyTradeExecutionGateway 属性测试
    - **Property 4: 开平转换正确性**
    - **Property 5: 订单类型映射正确性**
    - **Validates: Requirements 3.1, 3.2, 5.1, 5.2, 5.3, 5.4**

- [x] 5. Checkpoint - 高优先级功能验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. 增强 VnpyMarketDataGateway (中优先级)
  - [x] 6.1 实现 unsubscribe 方法
    - 从 symbol_strategy_map 移除映射
    - 从 vt_symbols 列表移除合约
    - 返回操作结果
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x] 6.2 实现 get_contracts_by_product 方法
    - 按产品类型 (FUTURES/OPTION/SPREAD) 筛选合约
    - _Requirements: 7.1_
  - [x] 6.3 实现 get_contracts_by_exchange 方法
    - 按交易所筛选合约
    - _Requirements: 7.2_
  - [x] 6.4 实现 get_contract_trading_params 方法
    - 返回 ContractParams 值对象
    - _Requirements: 7.3, 7.4_
  - [x] 6.5 实现 query_history 方法
    - 封装 main_engine.query_history()
    - 处理不支持历史数据的情况
    - _Requirements: 12.1, 12.2, 12.3_
  - [ ]* 6.6 编写 VnpyMarketDataGateway 属性测试
    - **Property 6: 合约筛选正确性**
    - **Property 7: 取消订阅状态一致性**
    - **Validates: Requirements 7.1, 7.2, 8.1, 8.2, 8.3**

- [x] 7. Checkpoint - 中优先级功能验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. 实现 VnpyQuoteGateway (低优先级)
  - [x] 8.1 创建 VnpyQuoteGateway 类
    - 在 `src/strategy/infrastructure/gateway/vnpy_quote_gateway.py` 创建类
    - 继承 VnpyGatewayAdapter
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  - [x] 8.2 实现 send_quote 方法
    - 将 QuoteRequest 转换为 vnpy QuoteRequest
    - 调用 main_engine.send_quote()
    - _Requirements: 9.1_
  - [x] 8.3 实现 cancel_quote 方法
    - 封装 main_engine.cancel_quote()
    - _Requirements: 9.2_
  - [x] 8.4 实现报价查询方法
    - get_quote, get_all_quotes, get_all_active_quotes
    - _Requirements: 9.3, 9.4, 9.5_
  - [ ]* 8.5 编写 VnpyQuoteGateway 属性测试
    - **Property 9: 报价发送/撤销正确性**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

- [x] 9. 实现 VnpyConnectionGateway (低优先级)
  - [x] 9.1 创建 VnpyConnectionGateway 类
    - 在 `src/strategy/infrastructure/gateway/vnpy_connection_gateway.py` 创建类
    - 继承 VnpyGatewayAdapter
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  - [x] 9.2 实现 is_connected 方法
    - 检查指定网关的连接状态
    - _Requirements: 10.1_
  - [x] 9.3 实现 get_all_gateway_names 方法
    - 封装 main_engine.get_all_gateway_names()
    - _Requirements: 10.2_
  - [x] 9.4 实现 reconnect 方法
    - 封装 main_engine.connect()
    - _Requirements: 10.3, 10.4_

- [x] 10. 实现 VnpyEventGateway (低优先级)
  - [x] 10.1 创建 VnpyEventGateway 类
    - 在 `src/strategy/infrastructure/gateway/vnpy_event_gateway.py` 创建类
    - 继承 VnpyGatewayAdapter
    - _Requirements: 11.1, 11.2, 11.3, 11.4_
  - [x] 10.2 实现 register_event_handler 方法
    - 封装 event_engine.register()
    - 支持 EVENT_ORDER, EVENT_TRADE, EVENT_POSITION, EVENT_ACCOUNT
    - _Requirements: 11.1, 11.3_
  - [x] 10.3 实现 unregister_event_handler 方法
    - 封装 event_engine.unregister()
    - _Requirements: 11.2_
  - [ ]* 10.4 编写 VnpyEventGateway 属性测试
    - **Property 8: 事件处理注册/触发正确性**
    - **Validates: Requirements 11.1, 11.2, 11.4**

- [x] 11. Final checkpoint - 全部功能验证
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. 更新模块导出和文档
  - [x] 12.1 更新 gateway 模块的 __init__.py
    - 导出所有新增的 Gateway 类
  - [x] 12.2 更新 value_object 模块的 __init__.py
    - 导出所有新增的值对象

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- 所有 Gateway 方法在 MainEngine 不可用时应提供合理的降级行为（返回空结果，不抛异常）
