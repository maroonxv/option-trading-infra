# 需求文档

## 简介

将 `src/strategy/domain/domain_service/` 目录下散落的 12 个领域服务文件按职责分类整理到逻辑子目录中。这是一次纯重构操作，不改变任何业务逻辑，仅改善代码组织结构，提升可维护性和可读性。

## 术语表

- **Domain_Service_Root**: `src/strategy/domain/domain_service/` 目录，所有领域服务文件的根目录
- **子目录**: Domain_Service_Root 下按职责划分的逻辑分组目录
- **导入路径**: Python 模块中 `from ... import ...` 语句所引用的模块路径
- **strategy_entry**: `src/strategy/strategy_entry.py`，策略入口文件，导入了 8 个领域服务
- **测试目录**: `tests/strategy/domain/domain_service/`，领域服务对应的测试文件目录
- **__init__.py**: Python 包标识文件，使目录成为可导入的 Python 包

## 需求

### 需求 1：按职责创建子目录结构

**用户故事：** 作为开发者，我希望领域服务按职责分类到子目录中，以便快速定位和理解各服务的归属。

#### 验收标准

1. THE 重构 SHALL 在 Domain_Service_Root 下创建以下 6 个子目录：`pricing/`、`hedging/`、`execution/`、`selection/`、`risk/`、`signal/`
2. THE 重构 SHALL 为每个新建子目录创建 `__init__.py` 文件，使其成为合法的 Python 包
3. THE 重构 SHALL 保留已有的 `calculation_service/` 子目录不做任何修改

### 需求 2：将服务文件移动到对应子目录

**用户故事：** 作为开发者，我希望每个领域服务文件归入正确的职责子目录，以便代码结构清晰反映领域划分。

#### 验收标准

1. THE 重构 SHALL 将 `greeks_calculator.py` 和 `vol_surface_builder.py` 移动到 `pricing/` 子目录
2. THE 重构 SHALL 将 `delta_hedging_engine.py` 和 `gamma_scalping_engine.py` 移动到 `hedging/` 子目录
3. THE 重构 SHALL 将 `smart_order_executor.py` 和 `advanced_order_scheduler.py` 移动到 `execution/` 子目录
4. THE 重构 SHALL 将 `option_selector_service.py` 和 `future_selection_service.py` 移动到 `selection/` 子目录
5. THE 重构 SHALL 将 `portfolio_risk_aggregator.py` 和 `position_sizing_service.py` 移动到 `risk/` 子目录
6. THE 重构 SHALL 将 `signal_service.py` 和 `indicator_service.py` 移动到 `signal/` 子目录
7. WHEN 所有文件移动完成后，THE Domain_Service_Root SHALL 不再包含任何散落的 `.py` 服务文件（仅保留子目录）

### 需求 3：更新源码导入路径

**用户故事：** 作为开发者，我希望所有源码中的导入路径在重构后保持正确，以便项目能正常运行。

#### 验收标准

1. WHEN 文件移动完成后，THE strategy_entry SHALL 更新所有 8 个领域服务的导入路径以反映新的子目录位置
2. WHEN 文件移动完成后，THE 项目中所有引用领域服务的源码文件 SHALL 使用更新后的完整导入路径
3. IF 存在领域服务文件之间的交叉导入，THEN THE 重构 SHALL 同步更新这些内部导入路径

### 需求 4：更新测试文件导入路径

**用户故事：** 作为开发者，我希望测试文件的导入路径在重构后保持正确，以便所有测试能正常通过。

#### 验收标准

1. WHEN 文件移动完成后，THE 测试目录下所有测试文件 SHALL 更新导入路径以反映新的子目录位置
2. WHEN 所有导入路径更新完成后，THE 项目中所有现有测试 SHALL 保持通过状态

### 需求 5：保持业务逻辑不变

**用户故事：** 作为开发者，我希望重构仅改变文件组织结构，不引入任何业务逻辑变更，以确保系统行为完全一致。

#### 验收标准

1. THE 重构 SHALL 不修改任何领域服务文件的内部实现代码
2. THE 重构 SHALL 不修改任何类、函数、接口的签名或行为
3. THE 重构 SHALL 仅修改文件位置和导入路径
