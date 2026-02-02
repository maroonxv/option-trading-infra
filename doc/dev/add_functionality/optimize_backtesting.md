# 回测优化方案：修复合约规格不一致问题

## 问题描述

在当前的 `src/backtesting` 回测框架中，`VtSymbolGenerator` 采用了硬编码的方式生成虚拟合约数据（`ContractData`）。

*   **现状**:
    *   所有生成的合约 `size` (合约乘数) 默认为 `10`。
    *   所有生成的合约 `pricetick` (最小变动价位) 默认为 `1.0` (除 `sc`, `fu` 外)。
*   **对比实盘**:
    *   实盘中，`contract_helper.py` 直接从 CTP 网关获取交易所下发的真实合约数据。
    *   例如：沪深300股指期货 (IF) 的乘数是 300，最小变动是 0.2；中证1000股指期货 (IM) 的乘数是 200。
*   **风险**:
    *   **盈亏计算严重失真**: IF 的波动盈亏被缩小了 30 倍 (300 vs 10)。
    *   **对冲比例失效**: 策略中若涉及“期货对冲期权”，由于两者名义本金计算基于错误的乘数，会导致对冲比例严重偏离设计值。

## 解决方案

### 1. 升级 `VtSymbolGenerator` (`src/backtesting/vt_symbol_generator.py`)

引入 `PRODUCT_SPECS` 配置表，根据品种代码动态匹配正确的规格。

```python
# 品种规格配置 (Size, PriceTick)
PRODUCT_SPECS = {
    # CFFEX - Stock Indices
    "IF": (300, 0.2),  # HS300 Future
    "IH": (300, 0.2),  # SSE50 Future
    "IC": (200, 0.2),  # CSI500 Future
    "IM": (200, 0.2),  # CSI1000 Future
    "IO": (100, 0.2),  # HS300 Option
    "HO": (100, 0.2),  # SSE50 Option
    "MO": (100, 0.2),  # CSI1000 Option
    
    # SHFE
    "rb": (10, 1.0),   # Rebar
    "hc": (10, 1.0),   # Hot Rolled Coil
    "ag": (15, 1.0),   # Silver
    "au": (1000, 0.02),# Gold
    
    # INE
    "sc": (1000, 0.1), # Crude Oil
    
    # DCE
    "m": (10, 1.0),    # Soybean Meal
    "i": (100, 0.5),   # Iron Ore
    
    # CZCE
    "SA": (20, 1.0),   # Soda Ash
    "MA": (10, 1.0),   # Methanol
}
```

修改 `generate_contract_data` 方法，优先从 `PRODUCT_SPECS` 获取 `(size, pricetick)`，未配置品种再回退到默认值。

### 2. 修正 `run_backtesting.py` 参数注入逻辑

目前 `run_backtesting.py` 强行将命令行参数 `--size` (默认 10) 和 `--pricetick` (默认 1.0) 覆盖到所有合约上。

**修改逻辑**:
*   不再使用全局统一的 `sizes` 和 `priceticks` 字典。
*   遍历生成的 `vt_symbols`，从 `engine.get_contract(vt_symbol)` 中读取该合约专属的 `size` 和 `pricetick`。
*   将这些正确的值注入到 `engine.set_parameters()`。

## 预期效果

*   股指期货（IF/IM）的回测盈亏将恢复正常量级。
*   期权与期货的资金配比和对冲逻辑将与实盘保持一致。
*   消除因数据源造假导致的回测失真风险。
