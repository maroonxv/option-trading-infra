# 开仓前流动性深度检测设计文档

## 1. 背景与现状
当前 `OptionSelectorService` 仅对期权合约进行了基础的静态阈值过滤（如 `min_bid_volume=10`）。虽然这能过滤掉极度不活跃的合约，但无法保证**当前这一笔特定手数的订单**能以买一价完全成交。

基于对 `vnpy.trader.object.TickData` 源码的分析，我们有完整的 5 档盘口数据可用，必须利用这些数据进行更精确的**刚性兑付**检查。

## 2. 核心问题分析
- **交易方向**：本策略为 **卖出开仓 (Short Open)**，分为两部分：
    1.  **主动成交 (Taker)**：向 **买入队列 (Bid Side)** 抛售 1 手（以买一价成交）。
    2.  **被动挂单 (Maker)**：在 **卖出队列 (Ask Side)** 挂单 1 手（排在卖一价）。
- **风险点**：
    - 对于 **主动成交部分**：若 `TickData.bid_volume_1` (买一量) < 1 手，会导致无法立即成交或滑点。
    - 对于 **被动挂单部分**：主要关注 `Ask` 队列的排队情况，但从风控角度，核心在于**第一手能否立即按预期价格成交**。
- **结论**：必须引入 **盘口深度 (Depth)** 校验，确保 `bid_volume_1 >= 1`（满足第一手主动成交的需求）。

## 3. 完备的“三层漏斗”过滤方案

基于源码分析，`TickData` 提供了我们需要的所有字段。方案如下：

### 3.1 第一层：宏观活跃度 (Activity Filter)
*   **指标**：`TickData.volume` (当日累计成交量)
*   **来源**：`object.py` L43
*   **规则**：`volume >= 100` (可配置)
*   **目的**：排除无人参与的“僵尸合约”。

### 3.2 第二层：微观流动性/深度 (Depth Filter) —— **核心风控**
*   **指标**：买一档挂单量 (`TickData.bid_volume_1`)。
*   **来源**：`object.py` L68
*   **规则**：`bid_volume_1 >= 1`。
*   **目的**：**刚性兑付**。确保策略的第一手主动抛单能被市场买一价完全承接，实现**第一手零滑点**。第二手挂单逻辑则依赖于后续的市场博弈。

### 3.3 第三层：交易成本/价差 (Spread Filter)
*   **指标**：买卖价差
*   **公式**：`(ask_price_1 - bid_price_1) / pricetick`
*   **来源**：
    - `TickData.ask_price_1` (L62)
    - `TickData.bid_price_1` (L56)
    - `ContractData.pricetick` (L243)
*   **规则**：`Spread < 3 Ticks` (可配置)
*   **目的**：控制内含交易成本。如果 `ask_price_1` 为 0 (涨停) 或数据异常，此条件自然无法满足，起到自动熔断作用。

## 4. 介入流程 (Insertion Point)

检查逻辑应嵌入在 `src/strategy/application/volatility_trade.py` 的开仓流程中，位于 **信号确认后**、**下单前** 的阶段。

### 4.1 流程图
1.  **SignalService**: 生成 `Short Open` 信号。
2.  **VolatilityTrade**: 决定开仓模式：**1手主动成交 (Taker) + 1手被动挂单 (Maker)**。
3.  **VolatilityTrade**: 调用 `MarketGateway.get_tick(vt_symbol)` 获取最新 `TickData`。
4.  **OptionSelectorService**: 传入 `TickData` 和 `required_bid_volume=1` 进行筛选。
    *   *Check 1*: `tick.volume >= 100`?
    *   *Check 2*: `tick.bid_volume_1 >= 1`? (确保第一手能成交)
    *   *Check 3*: `(tick.ask_price_1 - tick.bid_price_1) / contract.pricetick < 3`?
5.  **Pass**: 返回合约，执行拆单逻辑：
    - 发送 Order 1: 卖出开仓 1 手，价格 = `bid_price_1` (FAK/FOK 或 Limit)。
    - 发送 Order 2: 卖出开仓 1 手，价格 = `ask_price_1` (Limit Maker)。
6.  **Fail**: 放弃本次开仓，记录日志。

## 5. 数据字段映射表

| 应用层字段 | 源码对应 (`object.py`) | 类型 | 说明 |
| :--- | :--- | :--- | :--- |
| `volume` | `TickData.volume` | float | 当日累计成交量 |
| `bid_volume` | `TickData.bid_volume_1` | float | **买一量** (核心深度指标) |
| `bid_price` | `TickData.bid_price_1` | float | 买一价 |
| `ask_price` | `TickData.ask_price_1` | float | 卖一价 |
| `pricetick` | `ContractData.pricetick` | float | 最小变动价位 |

## 6. 验收标准
1.  **深度测试**: 在 `bid_volume_1 = 0` (跌停或无买单) 的场景下，策略**绝不**发出委托。
2.  **日志验证**: 必须在日志中看到类似 `[Liquidity] Filtered out {vt_symbol}: Depth insufficient (0 < 1)` 的记录。
