# 设计文档

## 概述

本次重构将 `src/strategy/domain/domain_service/` 下的 12 个领域服务文件按职责分类到 6 个子目录中。这是纯文件组织重构，不涉及任何业务逻辑变更。

重构范围：
- 创建 6 个子目录并添加 `__init__.py`
- 移动 12 个 `.py` 文件到对应子目录
- 更新 `strategy_entry.py` 中的 8 条导入路径
- 更新 `tests/strategy/domain/domain_service/` 下 9 个测试文件中的导入路径（`test_config_integration.py` 不涉及领域服务导入，无需修改）

## 架构

### 重构前目录结构

```
domain_service/
├── calculation_service/
│   └── __init__.py
├── advanced_order_scheduler.py
├── delta_hedging_engine.py
├── future_selection_service.py
├── gamma_scalping_engine.py
├── greeks_calculator.py
├── indicator_service.py
├── option_selector_service.py
├── portfolio_risk_aggregator.py
├── position_sizing_service.py
├── signal_service.py
├── smart_order_executor.py
└── vol_surface_builder.py
```

### 重构后目录结构

```
domain_service/
├── calculation_service/
│   └── __init__.py
├── pricing/
│   ├── __init__.py
│   ├── greeks_calculator.py
│   └── vol_surface_builder.py
├── hedging/
│   ├── __init__.py
│   ├── delta_hedging_engine.py
│   └── gamma_scalping_engine.py
├── execution/
│   ├── __init__.py
│   ├── smart_order_executor.py
│   └── advanced_order_scheduler.py
├── selection/
│   ├── __init__.py
│   ├── option_selector_service.py
│   └── future_selection_service.py
├── risk/
│   ├── __init__.py
│   ├── portfolio_risk_aggregator.py
│   └── position_sizing_service.py
└── signal/
    ├── __init__.py
    ├── signal_service.py
    └── indicator_service.py
```

## 组件与接口

### 文件移动映射表

| 原路径 | 目标子目录 | 分类依据 |
|--------|-----------|---------|
| `greeks_calculator.py` | `pricing/` | Black-Scholes 定价计算 |
| `vol_surface_builder.py` | `pricing/` | 波动率曲面构建，定价基础设施 |
| `delta_hedging_engine.py` | `hedging/` | Delta 对冲逻辑 |
| `gamma_scalping_engine.py` | `hedging/` | Gamma Scalping 对冲逻辑 |
| `smart_order_executor.py` | `execution/` | 智能订单执行 |
| `advanced_order_scheduler.py` | `execution/` | 冰山单/TWAP/VWAP 拆单调度 |
| `option_selector_service.py` | `selection/` | 期权合约筛选 |
| `future_selection_service.py` | `selection/` | 期货合约选择 |
| `portfolio_risk_aggregator.py` | `risk/` | 组合风险聚合与风控 |
| `position_sizing_service.py` | `risk/` | 仓位计算与风控 |
| `signal_service.py` | `signal/` | 信号生成模板 |
| `indicator_service.py` | `signal/` | 指标计算模板 |

### 导入路径变更映射

#### strategy_entry.py（8 条导入）

| 原导入路径 | 新导入路径 |
|-----------|-----------|
| `.domain.domain_service.indicator_service` | `.domain.domain_service.signal.indicator_service` |
| `.domain.domain_service.signal_service` | `.domain.domain_service.signal.signal_service` |
| `.domain.domain_service.position_sizing_service` | `.domain.domain_service.risk.position_sizing_service` |
| `.domain.domain_service.option_selector_service` | `.domain.domain_service.selection.option_selector_service` |
| `.domain.domain_service.future_selection_service` | `.domain.domain_service.selection.future_selection_service` |
| `.domain.domain_service.greeks_calculator` | `.domain.domain_service.pricing.greeks_calculator` |
| `.domain.domain_service.portfolio_risk_aggregator` | `.domain.domain_service.risk.portfolio_risk_aggregator` |
| `.domain.domain_service.smart_order_executor` | `.domain.domain_service.execution.smart_order_executor` |

#### 测试文件（9 个文件）

| 测试文件 | 原导入路径 | 新导入路径 |
|---------|-----------|-----------|
| `test_greeks_calculator.py` | `...domain_service.greeks_calculator` | `...domain_service.pricing.greeks_calculator` |
| `test_vol_surface_builder.py` | `...domain_service.vol_surface_builder` | `...domain_service.pricing.vol_surface_builder` |
| `test_delta_hedging_engine.py` | `...domain_service.delta_hedging_engine` | `...domain_service.hedging.delta_hedging_engine` |
| `test_gamma_scalping_engine.py` | `...domain_service.gamma_scalping_engine` | `...domain_service.hedging.gamma_scalping_engine` |
| `test_smart_order_executor.py` | `...domain_service.smart_order_executor` | `...domain_service.execution.smart_order_executor` |
| `test_advanced_order_scheduler.py` | `...domain_service.advanced_order_scheduler` | `...domain_service.execution.advanced_order_scheduler` |
| `test_order_splitting.py` | `...domain_service.advanced_order_scheduler` | `...domain_service.execution.advanced_order_scheduler` |
| `test_base_future_selector.py` | `...domain_service.future_selection_service` | `...domain_service.selection.future_selection_service` |
| `test_portfolio_risk_aggregator.py` | `...domain_service.portfolio_risk_aggregator` | `...domain_service.risk.portfolio_risk_aggregator` |

注意：`test_config_integration.py` 不导入任何领域服务，无需修改。

### 服务文件内部导入

所有 12 个服务文件使用相对导入引用 `value_object`、`entity`、`event` 等同级包。文件移动到子目录后，相对导入的层级需要调整：

- 原路径（从 `domain_service/` 出发）：`from ..value_object.xxx import ...`
- 新路径（从 `domain_service/pricing/` 等出发）：`from ...value_object.xxx import ...`（多一层 `..`）

特殊情况：
- `advanced_order_scheduler.py` 和 `future_selection_service.py` 使用绝对导入（`from src.strategy.domain...`），无需修改相对路径层级

## 数据模型

本次重构不涉及数据模型变更。所有类、接口、函数签名保持不变。


## 正确性属性

*正确性属性是一种在系统所有有效执行中都应成立的特征或行为——本质上是关于系统应该做什么的形式化陈述。属性是人类可读规范与机器可验证正确性保证之间的桥梁。*

本次重构是纯文件组织变更，所有验收标准都是具体的结构性检查（example-based），不涉及需要属性测试（property-based testing）的通用性质。验证方式以具体示例测试为主。

### 示例测试（Example-Based Tests）

**示例 1：子目录结构完整性**
验证 6 个子目录（pricing、hedging、execution、selection、risk、signal）均存在且各自包含 `__init__.py`，同时 `calculation_service/` 保持不变。
**验证：需求 1.1, 1.2, 1.3**

**示例 2：文件归位正确性**
验证全部 12 个服务文件存在于各自预期的子目录中，且 Domain_Service_Root 下不再有散落的 `.py` 文件。
**验证：需求 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

**示例 3：导入路径可解析**
验证 `strategy_entry.py` 和所有测试文件中的导入语句能正确解析到目标模块。
**验证：需求 3.1, 3.2, 4.1**

**示例 4：全量测试通过**
运行项目全部现有测试，确认无回归。
**验证：需求 4.2, 5.1, 5.2, 5.3**

## 错误处理

本次重构不引入新的错误处理逻辑。主要风险及应对：

| 风险 | 应对措施 |
|------|---------|
| 相对导入层级错误（`..` vs `...`） | 移动文件后逐一检查相对导入，确保层级正确 |
| 遗漏某个导入路径更新 | 通过 grep 全局搜索旧路径，确保无遗漏 |
| `__init__.py` 缺失导致 ImportError | 每个子目录创建时立即添加 `__init__.py` |

## 测试策略

### 验证方式

由于本次是纯重构（无新业务逻辑），不需要属性测试。验证策略如下：

1. **结构验证**：确认文件和目录在预期位置
2. **导入验证**：确认所有 import 语句可正确解析
3. **回归测试**：运行全部现有测试套件，确认无回归

### 具体步骤

1. 每移动一批文件后，运行对应的测试文件确认导入正确
2. 全部移动完成后，运行 `pytest tests/strategy/domain/domain_service/` 确认所有领域服务测试通过
3. 运行 `pytest tests/strategy/` 确认策略模块整体无回归
