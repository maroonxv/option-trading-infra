# 需求文档：src/main 模块重构

## 简介

`src/main/` 目录是项目的进程编排层，负责 CLI 入口、子进程/守护进程管理、网关连接和配置加载。当前该目录结构扁平、文件职责不清晰，且存在大量重复代码（引擎初始化、数据库配置、信号处理、数据录制路径补丁等）。本次重构旨在建立清晰的子目录结构，提取重复代码为共享模块，重命名文件以提高可读性，同时保持外部模块（`src/strategy`、`src/backtesting`）的导入兼容性。

## 术语表

- **Main_Module**: `src/main/` 目录下的进程编排层代码
- **ChildProcess**: 工作子进程，负责初始化 VnPy 引擎、加载策略、运行事件循环
- **ParentProcess**: 守护父进程，负责监控子进程、自动重启、交易时段调度
- **RecorderProcess**: 独立行情录制进程，仅录制行情不运行策略
- **GatewayManager**: 网关管理器，负责 CTP 网关的配置、连接和状态管理
- **ConfigLoader**: 配置加载器，支持 YAML 配置和环境变量加载
- **ContractUtils**: 合约工具类，解析合约代码中的到期日
- **VnPy_Engine**: VnPy 框架的 EventEngine 和 MainEngine 组合
- **Engine_Factory**: 待提取的共享模块，封装 VnPy 引擎初始化逻辑
- **Signal_Handler**: 待提取的共享模块，封装进程信号处理逻辑
- **Database_Setup**: 待提取的共享模块，封装 VnPy 数据库配置注入逻辑
- **Recorder_Patch**: 待提取的共享模块，封装 data_recorder_setting.json 路径重定向逻辑

## 需求

### 需求 1：建立子目录结构

**用户故事：** 作为开发者，我希望 `src/main/` 按职责划分为清晰的子目录，以便快速定位和理解各模块的功能。

#### 验收标准

1. WHEN 重构完成后查看 `src/main/` 目录结构，THE Main_Module SHALL 包含以下子目录：`process/`（进程管理）、`config/`（配置加载）、`utils/`（通用工具）、`bootstrap/`（引擎初始化与共享启动逻辑）
2. WHEN 进程相关文件被移动后，THE Main_Module SHALL 将 `child_process.py`、`parent_process.py`、`run_recorder.py` 放置在 `process/` 子目录下
3. WHEN 配置相关文件被移动后，THE Main_Module SHALL 将 `config_loader.py` 放置在 `config/` 子目录下
4. WHEN 工具文件被移动后，THE Main_Module SHALL 将 `contract_utils.py` 保留在 `utils/` 子目录下
5. WHEN 网关管理文件被移动后，THE Main_Module SHALL 将 `gateway.py` 放置在 `config/` 子目录下（因其职责是进程级网关配置与连接管理）
6. WHEN `main.py` 作为 CLI 入口，THE Main_Module SHALL 将 `main.py` 保留在 `src/main/` 根目录下
7. WHEN 每个子目录被创建后，THE Main_Module SHALL 在每个子目录中包含 `__init__.py` 文件以确保 Python 包结构完整

### 需求 2：提取重复的引擎初始化代码

**用户故事：** 作为开发者，我希望 VnPy 引擎初始化逻辑被提取到一个共享模块中，以消除 `child_process.py` 和 `run_recorder.py` 之间的代码重复。

#### 验收标准

1. WHEN Engine_Factory 模块被创建后，THE Engine_Factory SHALL 提供一个函数，接受配置参数并返回已初始化的 EventEngine 和 MainEngine 实例
2. WHEN ChildProcess 使用 Engine_Factory 初始化引擎时，THE ChildProcess SHALL 调用 Engine_Factory 而非内联初始化代码
3. WHEN RecorderProcess 使用 Engine_Factory 初始化引擎时，THE RecorderProcess SHALL 调用 Engine_Factory 而非内联初始化代码
4. WHEN Engine_Factory 初始化引擎后，THE Engine_Factory SHALL 返回的引擎实例与原有内联代码产生的实例功能等价

### 需求 3：提取重复的数据库配置代码

**用户故事：** 作为开发者，我希望 VnPy 数据库配置注入逻辑被提取到一个共享模块中，以消除 `child_process.py`、`run_recorder.py` 以及 `src/backtesting/run_backtesting.py` 之间的代码重复。

#### 验收标准

1. WHEN Database_Setup 模块被创建后，THE Database_Setup SHALL 提供一个函数，从环境变量读取数据库配置并注入到 VnPy SETTINGS 中
2. WHEN Database_Setup 函数被调用时，THE Database_Setup SHALL 返回一个布尔值表示数据库配置是否成功注入
3. WHEN 环境变量 `VNPY_DATABASE_DRIVER` 未配置时，THE Database_Setup SHALL 返回 False 并记录警告日志
4. WHEN ChildProcess 和 RecorderProcess 配置数据库时，THE ChildProcess 和 RecorderProcess SHALL 调用 Database_Setup 共享函数而非各自的内联实现

### 需求 4：提取重复的信号处理代码

**用户故事：** 作为开发者，我希望进程信号处理逻辑被提取到一个共享模块中，以消除 `main.py`、`child_process.py`、`parent_process.py`、`run_recorder.py` 之间的重复信号注册代码。

#### 验收标准

1. WHEN Signal_Handler 模块被创建后，THE Signal_Handler SHALL 提供一个函数，接受回调函数并注册 SIGTERM 和 SIGINT 信号处理器
2. WHEN 各进程模块使用 Signal_Handler 时，THE Main_Module SHALL 在 `main.py`、ChildProcess、ParentProcess、RecorderProcess 中统一调用 Signal_Handler 而非各自内联注册信号处理器
3. WHEN 信号被触发时，THE Signal_Handler SHALL 调用注册的回调函数并传递信号编号

### 需求 5：提取重复的数据录制路径补丁代码

**用户故事：** 作为开发者，我希望 `data_recorder_setting.json` 路径重定向逻辑被提取到一个共享模块中，以消除 `child_process.py` 和 `run_recorder.py` 之间的重复代码。

#### 验收标准

1. WHEN Recorder_Patch 模块被创建后，THE Recorder_Patch SHALL 提供一个函数，将 VnPy 的 `data_recorder_setting.json` 文件路径重定向到项目的 `config/general/` 目录
2. WHEN ChildProcess 和 RecorderProcess 需要路径补丁时，THE ChildProcess 和 RecorderProcess SHALL 调用 Recorder_Patch 共享函数而非各自的内联实现
3. WHEN 目标配置文件不存在时，THE Recorder_Patch SHALL 自动创建空 JSON 文件 `{}`

### 需求 6：保持外部导入的向后兼容性

**用户故事：** 作为开发者，我希望重构后 `src/strategy` 和 `src/backtesting` 模块的现有导入路径继续有效，以避免重构引发连锁修改。

#### 验收标准

1. WHEN `src/strategy/strategy_entry.py` 导入 `ConfigLoader.load_target_products()` 时，THE Main_Module SHALL 通过 `src/main/` 包的 `__init__.py` 或兼容导入路径确保该导入继续有效
2. WHEN `src/strategy/domain/domain_service/future_selection_service.py` 导入 `ContractUtils.get_expiry_from_symbol()` 时，THE Main_Module SHALL 确保该导入继续有效
3. WHEN `src/backtesting/run_backtesting.py` 导入 `ConfigLoader.load_yaml()` 和 `ConfigLoader.load_target_products()` 时，THE Main_Module SHALL 确保该导入继续有效
4. WHEN `src/main/` 内部模块之间相互导入时，THE Main_Module SHALL 更新所有内部导入路径以匹配新的目录结构

### 需求 7：文件重命名以提高可读性

**用户故事：** 作为开发者，我希望文件名能清晰反映其职责，以便在浏览目录时快速理解每个文件的用途。

#### 验收标准

1. WHEN `log_handler.py` 被移动到 `utils/` 目录后，THE Main_Module SHALL 将其重命名为 `logging_setup.py` 以更准确地反映其"配置日志系统"的职责
2. WHEN `run_recorder.py` 被移动到 `process/` 目录后，THE Main_Module SHALL 将其重命名为 `recorder_process.py` 以与 `child_process.py` 和 `parent_process.py` 的命名风格保持一致
3. WHEN `gateway.py` 被移动到 `config/` 目录后，THE Main_Module SHALL 将其重命名为 `gateway_manager.py` 以更准确地反映其"网关管理器"的职责

### 需求 8：确保重构后的结构符合项目 DDD 架构原则

**用户故事：** 作为开发者，我希望重构后的 `src/main/` 结构与项目整体的 DDD 分层架构保持一致，职责边界清晰。

#### 验收标准

1. THE Main_Module SHALL 保持进程编排层的职责定位，不包含领域逻辑或策略业务代码
2. WHEN `src/main/config/gateway_manager.py` 管理进程级网关连接时，THE GatewayManager SHALL 仅负责网关的配置加载、连接建立和状态查询，不涉及策略层的网关适配器逻辑（该逻辑已在 `src/strategy/infrastructure/gateway/` 中实现）
3. WHEN `bootstrap/` 目录中的共享模块被其他层引用时，THE Main_Module SHALL 通过清晰的包导出接口暴露共享功能，避免外部模块直接依赖内部实现细节
