# Design Document: Gateway Infrastructure Enhancement

## Overview

本设计文档描述了 vnpy 期货期权策略框架中 Gateway 基础设施层的增强方案。设计目标是在现有的 Gateway 适配器架构基础上，扩展完整的 CTP 接口能力，同时保持与回测模式的兼容性。

设计遵循以下原则：
1. **适配器模式**: 继续使用 VnpyGatewayAdapter 基类封装 MainEngine 访问
2. **职责分离**: 按功能领域划分不同的 Gateway 类
3. **回测兼容**: 所有方法在 MainEngine 不可用时提供合理的降级行为
4. **类型安全**: 使用 dataclass 定义值对象，提供清晰的类型提示

## Architecture

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     Strategy Layer (上层策略)                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Gateway Facade (统一入口)                      │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ OrderGateway │PositionGateway│ MarketGateway│ QuoteGateway │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  VnpyGatewayAdapter (基类)                       │
│              - context: strategy_context                         │
│              - main_engine: MainEngine                           │
│              - logger: Logger                                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VnPy MainEngine / OmsEngine                   │
└─────────────────────────────────────────────────────────────────┘
```

### 模块划分

```
src/strategy/infrastructure/gateway/
├── vnpy_gateway_adapter.py      # 基类 (已存在)
├── vnpy_account_gateway.py      # 账户/持仓网关 (增强)
├── vnpy_market_data_gateway.py  # 行情/合约网关 (增强)
├── vnpy_trade_execution_gateway.py  # 交易执行网关 (增强)
├── vnpy_order_gateway.py        # 订单查询网关 (新增)
├── vnpy_quote_gateway.py        # 报价/做市网关 (新增)
├── vnpy_connection_gateway.py   # 连接管理网关 (新增)
└── vnpy_event_gateway.py        # 事件监听网关 (新增)

src/strategy/domain/value_object/
├── order_instruction.py         # 交易指令 (增强 - 添加 order_type)
├── account_snapshot.py          # 账户快照 (增强 - 添加 frozen)
├── position_snapshot.py         # 持仓快照 (新增)
├── contract_params.py           # 合约参数 (新增)
└── quote_request.py             # 报价请求 (新增)
```

## Components and Interfaces

### 1. VnpyOrderGateway (新增)

订单查询网关，封装订单和成交查询能力。

```python
class VnpyOrderGateway(VnpyGatewayAdapter):
    """订单查询网关"""
    
    def get_order(self, vt_orderid: str) -> Optional[OrderData]:
        """获取指定订单"""
        pass
    
    def get_all_orders(self) -> List[OrderData]:
        """获取所有订单"""
        pass
    
    def get_all_active_orders(self) -> List[OrderData]:
        """获取所有活动订单"""
        pass
    
    def get_trade(self, vt_tradeid: str) -> Optional[TradeData]:
        """获取指定成交"""
        pass
    
    def get_all_trades(self) -> List[TradeData]:
        """获取所有成交"""
        pass
```

### 2. VnpyAccountGateway (增强)

账户和持仓查询网关，增强持仓查询和多账户支持。

```python
class VnpyAccountGateway(VnpyGatewayAdapter):
    """账户/持仓网关"""
    
    def get_account_snapshot(self) -> Optional[AccountSnapshot]:
        """获取账户快照 (增强: 包含 frozen)"""
        pass
    
    def get_account(self, vt_accountid: str) -> Optional[AccountSnapshot]:
        """获取指定账户"""
        pass
    
    def get_all_accounts(self) -> List[AccountSnapshot]:
        """获取所有账户"""
        pass
    
    def get_position(self, vt_symbol: str, direction: Direction) -> Optional[PositionSnapshot]:
        """获取指定持仓 (增强: 返回完整 PositionSnapshot)"""
        pass
    
    def get_all_positions(self) -> List[PositionSnapshot]:
        """获取所有持仓"""
        pass
```

### 3. VnpyTradeExecutionGateway (增强)

交易执行网关，增强订单类型支持和开平转换能力。

```python
class VnpyTradeExecutionGateway(VnpyGatewayAdapter):
    """交易执行网关"""
    
    def send_order(self, instruction: OrderInstruction) -> List[str]:
        """发送订单 (增强: 支持 order_type)"""
        pass
    
    def cancel_order(self, vt_orderid: str) -> None:
        """撤销订单"""
        pass
    
    def cancel_all_orders(self) -> None:
        """撤销所有订单"""
        pass
    
    def convert_order_request(
        self, 
        order_request: OrderRequest, 
        lock: bool = False, 
        net: bool = False
    ) -> List[OrderRequest]:
        """转换订单请求 (新增: 开平转换)"""
        pass
```

### 4. VnpyMarketDataGateway (增强)

行情和合约网关，增强合约筛选和取消订阅能力。

```python
class VnpyMarketDataGateway(VnpyGatewayAdapter):
    """行情/合约网关"""
    
    def subscribe(self, vt_symbol: str) -> bool:
        """订阅行情"""
        pass
    
    def unsubscribe(self, vt_symbol: str) -> bool:
        """取消订阅 (新增)"""
        pass
    
    def get_contracts_by_product(self, product: Product) -> List[ContractData]:
        """按产品类型筛选合约 (新增)"""
        pass
    
    def get_contracts_by_exchange(self, exchange: Exchange) -> List[ContractData]:
        """按交易所筛选合约 (新增)"""
        pass
    
    def get_contract_trading_params(self, vt_symbol: str) -> Optional[ContractParams]:
        """获取合约交易参数 (新增)"""
        pass
    
    def query_history(
        self, 
        vt_symbol: str, 
        interval: Interval, 
        start: datetime, 
        end: datetime
    ) -> List[BarData]:
        """查询历史数据 (新增)"""
        pass
```

### 5. VnpyQuoteGateway (新增)

报价/做市网关，封装双边报价能力。

```python
class VnpyQuoteGateway(VnpyGatewayAdapter):
    """报价/做市网关"""
    
    def send_quote(self, quote_request: QuoteRequest) -> str:
        """发送报价"""
        pass
    
    def cancel_quote(self, vt_quoteid: str) -> None:
        """撤销报价"""
        pass
    
    def get_quote(self, vt_quoteid: str) -> Optional[QuoteData]:
        """获取指定报价"""
        pass
    
    def get_all_quotes(self) -> List[QuoteData]:
        """获取所有报价"""
        pass
    
    def get_all_active_quotes(self) -> List[QuoteData]:
        """获取所有活动报价"""
        pass
```

### 6. VnpyConnectionGateway (新增)

连接管理网关，封装连接状态查询和重连能力。

```python
class VnpyConnectionGateway(VnpyGatewayAdapter):
    """连接管理网关"""
    
    def is_connected(self, gateway_name: str) -> bool:
        """检查网关连接状态"""
        pass
    
    def get_all_gateway_names(self) -> List[str]:
        """获取所有网关名称"""
        pass
    
    def reconnect(self, gateway_name: str, setting: dict) -> bool:
        """重新连接网关"""
        pass
```

### 7. VnpyEventGateway (新增)

事件监听网关，封装事件订阅和回调注册能力。

```python
class VnpyEventGateway(VnpyGatewayAdapter):
    """事件监听网关"""
    
    def register_event_handler(
        self, 
        event_type: str, 
        handler: Callable[[Event], None]
    ) -> None:
        """注册事件处理函数"""
        pass
    
    def unregister_event_handler(
        self, 
        event_type: str, 
        handler: Callable[[Event], None]
    ) -> None:
        """取消事件处理函数注册"""
        pass
```

## Data Models

### 1. AccountSnapshot (增强)

```python
@dataclass(frozen=True)
class AccountSnapshot:
    """账户快照值对象"""
    balance: float      # 账户总资金
    available: float    # 可用资金
    frozen: float = 0.0 # 冻结资金 (新增)
    accountid: str = "" # 账户ID (新增，用于多账户)
```

### 2. PositionSnapshot (新增)

```python
@dataclass(frozen=True)
class PositionSnapshot:
    """持仓快照值对象"""
    vt_symbol: str          # 合约代码
    direction: Direction    # 持仓方向
    volume: float           # 持仓量
    frozen: float = 0.0     # 冻结量
    price: float = 0.0      # 持仓均价
    pnl: float = 0.0        # 持仓盈亏
    yd_volume: float = 0.0  # 昨仓量
```

### 3. ContractParams (新增)

```python
@dataclass(frozen=True)
class ContractParams:
    """合约交易参数值对象"""
    vt_symbol: str          # 合约代码
    size: float             # 合约乘数
    pricetick: float        # 最小价格变动
    min_volume: float = 1   # 最小下单量
    max_volume: Optional[float] = None  # 最大下单量
```

### 4. QuoteRequest (新增)

```python
@dataclass(frozen=True)
class QuoteRequest:
    """报价请求值对象"""
    vt_symbol: str          # 合约代码
    bid_price: float        # 买价
    bid_volume: int         # 买量
    ask_price: float        # 卖价
    ask_volume: int         # 卖量
    bid_offset: Offset = Offset.NONE  # 买开平
    ask_offset: Offset = Offset.NONE  # 卖开平
```

### 5. OrderInstruction (增强)

```python
class OrderType(Enum):
    """订单类型"""
    LIMIT = "limit"         # 限价单
    MARKET = "market"       # 市价单
    FAK = "fak"             # 立即成交剩余撤销
    FOK = "fok"             # 全部成交或撤销

@dataclass(frozen=True)
class OrderInstruction:
    """交易指令值对象 (增强)"""
    vt_symbol: str
    direction: Direction
    offset: Offset
    volume: int
    price: float = 0.0
    signal: str = ""
    order_type: OrderType = OrderType.LIMIT  # 新增: 订单类型
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*



### Property 1: 查询结果一致性

*For any* vt_orderid/vt_tradeid/vt_accountid/vt_quoteid，Gateway 的查询方法返回的结果应与 MainEngine 中存储的数据一致。如果 ID 存在，返回对应对象；如果不存在，返回 None。

**Validates: Requirements 1.1, 1.2, 4.1, 4.2, 6.2, 6.3, 6.4, 9.3, 9.4**

### Property 2: 活动状态筛选正确性

*For any* 订单/报价列表，`get_all_active_orders()` 和 `get_all_active_quotes()` 返回的列表应只包含状态为 SUBMITTING、NOTTRADED 或 PARTTRADED 的项目。

**Validates: Requirements 1.3, 9.5**

### Property 3: 持仓快照完整性

*For any* 有效的 vt_symbol 和 direction 组合，`get_position()` 返回的 PositionSnapshot 应包含所有必需字段（volume、frozen、price、pnl、yd_volume），且值与 MainEngine 中的 PositionData 一致。

**Validates: Requirements 2.1, 2.2**

### Property 4: 开平转换正确性

*For any* 上期所或能源中心的平仓订单请求，`convert_order_request()` 应根据持仓情况正确拆分为平今和平昨订单。拆分后的订单总量应等于原始订单量。

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

### Property 5: 订单类型映射正确性

*For any* OrderInstruction，发送订单时应根据 order_type 字段正确设置 vnpy 的 OrderPriceType、TimeCondition 和 VolumeCondition 参数。

**Validates: Requirements 5.1, 5.2, 5.3, 5.4**

### Property 6: 合约筛选正确性

*For any* 产品类型或交易所筛选条件，返回的合约列表应只包含符合条件的合约，且不遗漏任何符合条件的合约。

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 7: 取消订阅状态一致性

*For any* 已订阅的 vt_symbol，调用 `unsubscribe()` 后，该合约应从 symbol_strategy_map 和 vt_symbols 列表中移除，且方法返回 True。

**Validates: Requirements 8.1, 8.2, 8.3**

### Property 8: 事件处理注册/触发正确性

*For any* 事件类型和处理函数，注册后当对应事件发生时处理函数应被调用；取消注册后处理函数不应被调用。

**Validates: Requirements 11.1, 11.2, 11.4**

### Property 9: 报价发送/撤销正确性

*For any* 有效的 QuoteRequest，`send_quote()` 应返回非空的 vt_quoteid；对于有效的 vt_quoteid，`cancel_quote()` 应成功撤销报价。

**Validates: Requirements 9.1, 9.2**

## Error Handling

### 1. MainEngine 不可用

当 MainEngine 为 None 时（如回测模式），所有查询方法应：
- 返回空结果（空列表或 None）
- 记录警告日志
- 不抛出异常

```python
def get_order(self, vt_orderid: str) -> Optional[OrderData]:
    if not self.main_engine:
        self._log("MainEngine 不可用，无法查询订单")
        return None
    return self.main_engine.get_order(vt_orderid)
```

### 2. 参数无效

当传入无效参数时，方法应：
- 返回空结果或 False
- 记录错误日志
- 不抛出异常

### 3. 网关不存在

当查询不存在的网关时，方法应：
- 返回 False 或 None
- 记录警告日志

### 4. OffsetConverter 不可用

当 OffsetConverter 不可用时，`convert_order_request()` 应：
- 返回原始订单请求列表（不做转换）
- 记录警告日志

## Testing Strategy

### 单元测试

单元测试应覆盖以下场景：

1. **正常场景**: 验证各方法在正常输入下的行为
2. **边界条件**: 验证空输入、不存在的 ID、无匹配结果等情况
3. **错误处理**: 验证 MainEngine 不可用时的降级行为

### 属性测试

使用 `hypothesis` 库进行属性测试，每个属性测试至少运行 100 次迭代。

**测试配置**:
```python
from hypothesis import given, settings, strategies as st

@settings(max_examples=100)
@given(...)
def test_property_xxx(...):
    # Feature: gateway-infrastructure-enhancement, Property N: xxx
    pass
```

**属性测试覆盖**:

1. **Property 1 (查询一致性)**: 生成随机 ID，验证查询结果与模拟数据一致
2. **Property 2 (活动状态筛选)**: 生成随机状态的订单/报价列表，验证筛选结果
3. **Property 3 (持仓快照完整性)**: 生成随机持仓数据，验证转换后的 PositionSnapshot
4. **Property 4 (开平转换)**: 生成随机订单请求，验证拆分后的订单总量
5. **Property 5 (订单类型映射)**: 生成随机订单类型，验证参数映射
6. **Property 6 (合约筛选)**: 生成随机合约列表，验证筛选结果
7. **Property 7 (取消订阅)**: 验证取消订阅后的状态变化
8. **Property 8 (事件处理)**: 验证事件注册/触发机制
9. **Property 9 (报价操作)**: 验证报价发送/撤销的正确性

### Mock 策略

由于 Gateway 依赖 vnpy 的 MainEngine，测试时需要使用 Mock：

```python
from unittest.mock import Mock, MagicMock

def create_mock_main_engine():
    """创建模拟的 MainEngine"""
    engine = Mock()
    engine.get_order = Mock(return_value=None)
    engine.get_all_orders = Mock(return_value=[])
    # ... 其他方法
    return engine
```

### 测试文件结构

```
tests/strategy/infrastructure/gateway/
├── test_vnpy_order_gateway.py
├── test_vnpy_account_gateway.py
├── test_vnpy_trade_execution_gateway.py
├── test_vnpy_market_data_gateway.py
├── test_vnpy_quote_gateway.py
├── test_vnpy_connection_gateway.py
├── test_vnpy_event_gateway.py
└── conftest.py  # 共享的 fixtures
```
