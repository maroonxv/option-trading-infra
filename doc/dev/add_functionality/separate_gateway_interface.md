# 网关接口分离重构设计方案

## 1. 重构背景与目标

重构前 `src/strategy/infrastructure/gateway` 下的网关实现（`VnpyTradeGateway`）承担了过多的职责，包括行情获取、账户查询和交易执行。这违反了 **接口隔离原则 (ISP)**，导致：
1.  **耦合度高**: 只需要查询资金的逻辑被迫依赖交易接口。
2.  **测试困难**: 难以单独 Mock 资金查询或行情获取功能。
3.  **扩展性差**: 未来如果需要混合使用不同渠道（如：CTP做交易，RQData做行情），难以拆分。

**目标**: 将网关拆分为三个同等地位的独立接口，并在应用层 (`VolatilityTrade`) 通过组合模式使用。

## 2. 总体架构

### 2.1 接口层级 (Domain Layer)

在 `src/strategy/domain/demand_interface/` 下定义三个抽象基类 (ABC)：

1.  **IMarketDataGateway**: 负责行情订阅、快照查询、合约查询。
2.  **IAccountGateway**: 负责资金查询、持仓查询。
3.  **ITradeExecutionGateway**: 负责下单、撤单。

### 2.2 实现层级 (Infrastructure Layer)

在 `src/strategy/infrastructure/gateway/` 下基于 VnPy 上下文实现上述接口：

1.  **VnpyMarketDataGateway**: 实现 `IMarketDataGateway`。
2.  **VnpyAccountGateway**: 实现 `IAccountGateway`。
3.  **VnpyTradeExecutionGateway**: 实现 `ITradeExecutionGateway`。

### 2.3 应用层级 (Application Layer)

`VolatilityTrade` 不再持有单一的 `gateway` 对象，而是持有上述三个具体的网关实例。

## 3. 详细接口定义

### 3.1 IMarketDataGateway (市场数据)

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Any

class IMarketDataGateway(ABC):
    @abstractmethod
    def subscribe(self, vt_symbol: str) -> None:
        """订阅行情"""
        pass

    @abstractmethod
    def get_tick(self, vt_symbol: str) -> Optional[Any]:
        """获取最新 Tick 快照"""
        pass

    @abstractmethod
    def get_contract(self, vt_symbol: str) -> Optional[Any]:
        """获取合约详情"""
        pass

    @abstractmethod
    def get_all_contracts(self) -> List[Any]:
        """获取所有合约"""
        pass
```

### 3.2 IAccountGateway (账户资金)

```python
from abc import ABC, abstractmethod
from typing import List, Any

class IAccountGateway(ABC):
    @abstractmethod
    def get_balance(self) -> float:
        """获取可用资金"""
        pass

    @abstractmethod
    def get_position(self, vt_symbol: str, direction: Any) -> Optional[Any]:
        """获取特定持仓"""
        pass

    @abstractmethod
    def get_all_positions(self) -> List[Any]:
        """获取所有持仓"""
        pass
```

### 3.3 ITradeExecutionGateway (交易执行)

```python
from abc import ABC, abstractmethod
from typing import List
from ..value_object.order_instruction import OrderInstruction

class ITradeExecutionGateway(ABC):
    @abstractmethod
    def send_order(self, instruction: OrderInstruction) -> List[str]:
        """发送订单，返回 OrderID 列表"""
        pass

    @abstractmethod
    def cancel_order(self, vt_orderid: str) -> None:
        """撤销订单"""
        pass

    @abstractmethod
    def cancel_all_orders(self) -> None:
        """撤销所有订单"""
        pass
```

## 4. 基础设施实现方案

所有 VnPy 的网关实现都需要依赖 `strategy_context` (即策略实例本身，用于访问 `main_engine` 或 `strategy_engine`)。

我们可以创建一个基础适配器类来持有 context，然后让三个具体网关继承它。

```python
class VnpyGatewayAdapter:
    def __init__(self, strategy_context: Any):
        self.context = strategy_context
        
        # 提取引擎引用
        self.main_engine = None
        if hasattr(strategy_context, "strategy_engine"):
            if hasattr(strategy_context.strategy_engine, "main_engine"):
                self.main_engine = strategy_context.strategy_engine.main_engine

# --- 具体实现 ---

class VnpyMarketDataGateway(VnpyGatewayAdapter, IMarketDataGateway):
    def subscribe(self, vt_symbol: str) -> None:
        if hasattr(self.main_engine, "subscribe"):
            # 需构造 SubscribeRequest 或直接调用
            pass 
            
    def get_tick(self, vt_symbol: str) -> Optional[Any]:
        if self.main_engine:
            return self.main_engine.get_tick(vt_symbol)
        return None
    # ... 实现其他方法

class VnpyAccountGateway(VnpyGatewayAdapter, IAccountGateway):
    def get_balance(self) -> float:
        # 实现获取资金逻辑
        pass
    # ... 实现其他方法

class VnpyTradeExecutionGateway(VnpyGatewayAdapter, ITradeExecutionGateway):
    def send_order(self, instruction: OrderInstruction) -> List[str]:
        # 调用 context.buy/sell/short/cover 或 engine.send_order
        pass
    # ... 实现其他方法
```

## 5. 应用层改造 (VolatilityTrade)

`VolatilityTrade` 将成为一个 **Facade (门面)**，组合这些网关。

```python
class VolatilityTrade:
    def __init__(
        self,
        strategy_context: Any,
        # ... 其他服务
    ) -> None:
        
        # 1. 初始化独立的网关适配器
        self.market_gateway = VnpyMarketDataGateway(strategy_context)
        self.account_gateway = VnpyAccountGateway(strategy_context)
        self.exec_gateway = VnpyTradeExecutionGateway(strategy_context)
        
        # ... 其他初始化
```

### 5.1 调用点修改示例

**场景1：期权筛选 (需要行情)**
*   旧代码: `self.gateway.get_all_contracts()` (假设有)
*   新代码: `self.market_gateway.get_all_contracts()`

**场景2：仓位计算 (需要资金)**
*   旧代码: `self.gateway.get_account_balance()`
*   新代码: `self.account_gateway.get_balance()`

**场景3：执行交易 (需要下单)**
*   旧代码: `self.gateway.send_order(instruction)`
*   新代码: `self.exec_gateway.send_order(instruction)`

## 6. 实施步骤

1.  **定义接口**: 在 `src/strategy/domain/demand_interface/` 下定义三个 ABC（已完成）。
2.  **实现适配器**: 在 `src/strategy/infrastructure/gateway/` 下实现三个具体网关（已完成）。
3.  **改造应用层**: `VolatilityTrade` 组合使用三个网关，替换旧的单体网关调用（已完成）。
4.  **清理**: 旧的单体网关文件已移除（已完成）。
5.  **验证**: 运行回测/实盘联调验证行为一致。

## 7. 优势总结

通过此次重构：
1.  **OptionSelectorService** 可以明确它只需要 `IMarketDataGateway`（如果未来我们决定将网关注入服务）。
2.  **PositionSizingService** 可以明确它只需要 `IAccountGateway` 的数据。
3.  **单元测试** 可以轻松模拟：
    *   "资金充足但交易所接口宕机" (Mock Account OK, Mock Exec Fail)。
    *   "行情中断但持仓可见" (Mock Market Fail, Mock Account OK)。
