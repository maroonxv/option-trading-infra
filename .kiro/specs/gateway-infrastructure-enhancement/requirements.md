# Requirements Document

## Introduction

本文档定义了 vnpy 期货期权策略框架中 Gateway 基础设施层的增强需求。目标是完善 `src/strategy/infrastructure/gateway` 下的网关适配器，使其能够囊括上层策略所需的所有 CTP 接口功能，包括订单查询、持仓查询、开平转换、成交查询、订单类型扩展、账户信息补全、合约筛选、取消订阅、报价/做市、连接管理、事件监听和历史数据查询等能力。

## Glossary

- **Gateway**: 网关适配器，封装 vnpy MainEngine 的底层能力，为上层策略提供统一接口
- **MainEngine**: vnpy 的主引擎，提供交易、行情、账户等核心功能
- **OmsEngine**: vnpy 的订单管理系统引擎，管理订单、成交、持仓、账户等数据
- **OffsetConverter**: vnpy 的开平转换器，处理上期所/能源中心的平今/平昨自动拆分
- **OrderData**: vnpy 订单数据对象，包含订单状态、成交量等信息
- **TradeData**: vnpy 成交数据对象，包含成交价格、成交量等信息
- **PositionData**: vnpy 持仓数据对象，包含持仓量、冻结量、持仓均价、盈亏等信息
- **AccountData**: vnpy 账户数据对象，包含余额、冻结资金、可用资金等信息
- **QuoteData**: vnpy 报价数据对象，用于做市商双边报价
- **ContractData**: vnpy 合约数据对象，包含合约基本信息和交易参数
- **vt_orderid**: vnpy 订单唯一标识，格式为 `{gateway_name}.{orderid}`
- **vt_positionid**: vnpy 持仓唯一标识，格式为 `{gateway_name}.{vt_symbol}.{direction}`
- **vt_symbol**: vnpy 合约唯一标识，格式为 `{symbol}.{exchange}`
- **Product**: 合约产品类型，包括 FUTURES（期货）、OPTION（期权）、SPREAD（组合）
- **OrderType**: 订单类型，包括 LIMIT（限价）、MARKET（市价）、FAK（立即成交剩余撤销）、FOK（全部成交或撤销）

## Requirements

### Requirement 1: 订单查询能力

**User Story:** As a 策略开发者, I want to 查询订单状态和历史订单, so that I can 跟踪订单执行情况并进行风控管理。

#### Acceptance Criteria

1. WHEN 策略调用 `get_order(vt_orderid)` THEN the Gateway SHALL 返回对应的 OrderData 对象或 None
2. WHEN 策略调用 `get_all_orders()` THEN the Gateway SHALL 返回当前交易日所有订单的列表
3. WHEN 策略调用 `get_all_active_orders()` THEN the Gateway SHALL 返回所有活动订单（状态为 SUBMITTING、NOTTRADED、PARTTRADED）的列表
4. IF MainEngine 不可用 THEN the Gateway SHALL 返回空结果并记录日志

### Requirement 2: 持仓查询补全

**User Story:** As a 策略开发者, I want to 获取完整的持仓信息, so that I can 进行仓位管理和风险控制。

#### Acceptance Criteria

1. WHEN 策略调用 `get_position(vt_symbol, direction)` THEN the Gateway SHALL 返回包含 volume、frozen、price、pnl、yd_volume 字段的 PositionSnapshot 对象
2. WHEN 策略调用 `get_all_positions()` THEN the Gateway SHALL 返回所有持仓的 PositionSnapshot 列表
3. WHEN 持仓不存在 THEN the Gateway SHALL 返回 None
4. THE PositionSnapshot SHALL 包含以下字段：vt_symbol、direction、volume（持仓量）、frozen（冻结量）、price（持仓均价）、pnl（持仓盈亏）、yd_volume（昨仓量）

### Requirement 3: 开平转换能力

**User Story:** As a 策略开发者, I want to 自动处理上期所/能源中心的平今平昨拆分, so that I can 简化下单逻辑并避免开平错误。

#### Acceptance Criteria

1. WHEN 策略调用 `convert_order_request(order_request, lock, net)` THEN the Gateway SHALL 返回转换后的订单请求列表
2. WHEN 合约属于上期所或能源中心且需要平仓 THEN the Gateway SHALL 自动拆分为平今和平昨订单
3. WHEN lock 参数为 True THEN the Gateway SHALL 使用锁仓模式进行转换
4. WHEN net 参数为 True THEN the Gateway SHALL 使用净仓模式进行转换
5. IF OffsetConverter 不可用 THEN the Gateway SHALL 返回原始订单请求列表

### Requirement 4: 成交查询能力

**User Story:** As a 策略开发者, I want to 查询成交记录, so that I can 分析交易执行质量和计算实际成本。

#### Acceptance Criteria

1. WHEN 策略调用 `get_trade(vt_tradeid)` THEN the Gateway SHALL 返回对应的 TradeData 对象或 None
2. WHEN 策略调用 `get_all_trades()` THEN the Gateway SHALL 返回当前交易日所有成交记录的列表
3. IF MainEngine 不可用 THEN the Gateway SHALL 返回空结果并记录日志

### Requirement 5: 订单类型扩展

**User Story:** As a 策略开发者, I want to 使用多种订单类型下单, so that I can 根据不同场景选择最优的订单执行方式。

#### Acceptance Criteria

1. WHEN 策略发送 LIMIT 类型订单 THEN the Gateway SHALL 正确设置限价单参数
2. WHEN 策略发送 MARKET 类型订单 THEN the Gateway SHALL 正确设置市价单参数
3. WHEN 策略发送 FAK 类型订单 THEN the Gateway SHALL 正确设置立即成交剩余撤销参数
4. WHEN 策略发送 FOK 类型订单 THEN the Gateway SHALL 正确设置全部成交或撤销参数
5. THE OrderInstruction SHALL 支持 order_type 字段指定订单类型

### Requirement 6: 账户信息补全

**User Story:** As a 策略开发者, I want to 获取完整的账户资金信息, so that I can 进行资金管理和风险控制。

#### Acceptance Criteria

1. THE AccountSnapshot SHALL 包含 frozen 字段表示冻结资金
2. WHEN 策略调用 `get_account_snapshot()` THEN the Gateway SHALL 返回包含 balance、available、frozen 字段的 AccountSnapshot 对象
3. WHEN 策略调用 `get_all_accounts()` THEN the Gateway SHALL 返回所有账户的 AccountSnapshot 列表
4. WHEN 策略调用 `get_account(vt_accountid)` THEN the Gateway SHALL 返回指定账户的 AccountSnapshot 对象

### Requirement 7: 合约筛选能力

**User Story:** As a 策略开发者, I want to 按条件筛选合约, so that I can 快速找到符合策略需求的交易标的。

#### Acceptance Criteria

1. WHEN 策略调用 `get_contracts_by_product(product)` THEN the Gateway SHALL 返回指定产品类型（FUTURES/OPTION/SPREAD）的合约列表
2. WHEN 策略调用 `get_contracts_by_exchange(exchange)` THEN the Gateway SHALL 返回指定交易所的合约列表
3. WHEN 策略调用 `get_contract_trading_params(vt_symbol)` THEN the Gateway SHALL 返回合约的交易参数（size、pricetick、min_volume、max_volume）
4. WHEN 筛选条件无匹配结果 THEN the Gateway SHALL 返回空列表

### Requirement 8: 取消订阅能力

**User Story:** As a 策略开发者, I want to 取消行情订阅, so that I can 减少不必要的数据推送和资源消耗。

#### Acceptance Criteria

1. WHEN 策略调用 `unsubscribe(vt_symbol)` THEN the Gateway SHALL 取消对该合约的行情订阅
2. WHEN 取消订阅成功 THEN the Gateway SHALL 从策略的 symbol_strategy_map 中移除映射
3. WHEN 取消订阅成功 THEN the Gateway SHALL 从策略的 vt_symbols 列表中移除该合约
4. IF 合约未被订阅 THEN the Gateway SHALL 返回 False 并记录日志

### Requirement 9: 报价/做市能力

**User Story:** As a 做市策略开发者, I want to 发送和管理双边报价, so that I can 实现做市策略。

#### Acceptance Criteria

1. WHEN 策略调用 `send_quote(quote_request)` THEN the Gateway SHALL 发送双边报价并返回 vt_quoteid
2. WHEN 策略调用 `cancel_quote(vt_quoteid)` THEN the Gateway SHALL 撤销指定报价
3. WHEN 策略调用 `get_quote(vt_quoteid)` THEN the Gateway SHALL 返回对应的 QuoteData 对象或 None
4. WHEN 策略调用 `get_all_quotes()` THEN the Gateway SHALL 返回所有报价的列表
5. WHEN 策略调用 `get_all_active_quotes()` THEN the Gateway SHALL 返回所有活动报价的列表

### Requirement 10: 连接管理能力

**User Story:** As a 策略开发者, I want to 查询和管理网关连接状态, so that I can 确保交易通道正常并处理断线重连。

#### Acceptance Criteria

1. WHEN 策略调用 `is_connected(gateway_name)` THEN the Gateway SHALL 返回指定网关的连接状态
2. WHEN 策略调用 `get_all_gateway_names()` THEN the Gateway SHALL 返回所有已添加网关的名称列表
3. WHEN 策略调用 `reconnect(gateway_name, setting)` THEN the Gateway SHALL 尝试重新连接指定网关
4. IF 网关不存在 THEN the Gateway SHALL 返回 False 并记录日志

### Requirement 11: 事件监听能力

**User Story:** As a 策略开发者, I want to 注册事件回调, so that I can 实时响应订单、成交、持仓等事件。

#### Acceptance Criteria

1. WHEN 策略调用 `register_event_handler(event_type, handler)` THEN the Gateway SHALL 注册事件处理函数
2. WHEN 策略调用 `unregister_event_handler(event_type, handler)` THEN the Gateway SHALL 取消事件处理函数注册
3. THE Gateway SHALL 支持以下事件类型：EVENT_ORDER、EVENT_TRADE、EVENT_POSITION、EVENT_ACCOUNT
4. WHEN 事件发生 THEN the Gateway SHALL 调用所有已注册的处理函数

### Requirement 12: 历史数据查询

**User Story:** As a 策略开发者, I want to 查询历史K线数据, so that I can 进行技术分析和回测验证。

#### Acceptance Criteria

1. WHEN 策略调用 `query_history(vt_symbol, interval, start, end)` THEN the Gateway SHALL 返回指定时间范围的 BarData 列表
2. WHEN 网关不支持历史数据查询 THEN the Gateway SHALL 返回空列表并记录日志
3. IF 参数无效 THEN the Gateway SHALL 返回空列表并记录错误信息
