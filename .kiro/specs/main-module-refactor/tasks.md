# Implementation Plan: src/main 模块重构

## Overview

按增量步骤重构 `src/main/`：先创建目录结构和共享模块，再移动文件并更新导入，最后建立向后兼容层。每步结束后代码应可运行。

## Tasks

- [x] 1. 创建子目录结构和 `__init__.py`
  - 创建 `src/main/process/`、`src/main/config/`、`src/main/bootstrap/` 目录
  - 在每个新目录中创建 `__init__.py`
  - 保留现有 `src/main/utils/` 不变
  - _Requirements: 1.1, 1.7_

- [ ] 2. 提取共享模块到 `bootstrap/` 和 `utils/`
  - [x] 2.1 创建 `src/main/bootstrap/engine_factory.py`
    - 提取 `EngineBundle` 数据类和 `create_engines()` 函数
    - 从 `child_process.py._init_engines()` 和 `run_recorder.py._init_engines()` 中提取公共的 EventEngine + MainEngine 创建逻辑
    - _Requirements: 2.1, 2.4_

  - [x] 2.2 创建 `src/main/bootstrap/database_setup.py`
    - 提取 `setup_vnpy_database()` 函数
    - 合并 `child_process.py._setup_vnpy_database_settings()` 和 `run_recorder.py._setup_vnpy_database_settings()` 的逻辑
    - 函数返回 `bool` 表示是否成功注入
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 2.3 为 `database_setup.py` 编写属性测试
    - **Property 2: 数据库配置注入正确性**
    - **Validates: Requirements 3.1, 3.2, 3.3**

  - [x] 2.4 创建 `src/main/bootstrap/recorder_patch.py`
    - 提取 `patch_data_recorder_setting_path()` 函数
    - 合并 `child_process.py._patch_data_recorder_setting_path()` 和 `run_recorder.py._patch_data_recorder_setting_path()` 的逻辑
    - _Requirements: 5.1, 5.3_

  - [x] 2.5 创建 `src/main/utils/signal_handler.py`
    - 提取 `register_shutdown_signals(callback)` 函数
    - _Requirements: 4.1, 4.3_

  - [ ]* 2.6 为 `signal_handler.py` 编写属性测试
    - **Property 3: 信号处理器注册与回调**
    - **Validates: Requirements 4.1, 4.3**

  - [x] 2.7 更新 `src/main/bootstrap/__init__.py` 导出 `create_engines`、`setup_vnpy_database`、`patch_data_recorder_setting_path`
    - _Requirements: 8.3_

- [x] 3. Checkpoint - 确保共享模块可导入
  - 确保所有新模块可以正常 import，ask the user if questions arise.

- [x] 4. 移动并重命名文件
  - [x] 4.1 移动 `src/main/child_process.py` → `src/main/process/child_process.py`
    - 更新内部导入路径，使用 `bootstrap/` 共享模块替换重复代码
    - 用 `create_engines()` 替换内联引擎初始化
    - 用 `setup_vnpy_database()` 替换 `_setup_vnpy_database_settings()`
    - 用 `patch_data_recorder_setting_path()` 替换 `_patch_data_recorder_setting_path()`
    - 用 `register_shutdown_signals()` 替换内联信号注册
    - _Requirements: 1.2, 2.2, 3.4, 4.2, 5.2_

  - [x] 4.2 移动并重命名 `src/main/run_recorder.py` → `src/main/process/recorder_process.py`
    - 更新内部导入路径，使用 `bootstrap/` 共享模块替换重复代码
    - 同 4.1 的共享模块替换
    - _Requirements: 1.2, 2.3, 3.4, 4.2, 5.2, 7.2_

  - [x] 4.3 移动 `src/main/parent_process.py` → `src/main/process/parent_process.py`
    - 更新内部导入路径
    - 用 `register_shutdown_signals()` 替换内联信号注册
    - _Requirements: 1.2, 4.2_

  - [x] 4.4 移动 `src/main/utils/config_loader.py` → `src/main/config/config_loader.py`
    - _Requirements: 1.3_

  - [x] 4.5 移动并重命名 `src/main/gateway.py` → `src/main/config/gateway_manager.py`
    - _Requirements: 1.5, 7.3_

  - [x] 4.6 重命名 `src/main/utils/log_handler.py` → `src/main/utils/logging_setup.py`
    - _Requirements: 7.1_

  - [x] 4.7 更新 `src/main/main.py` 的导入路径
    - 更新对 `child_process`、`parent_process`、`config_loader`、`setup_logging` 的导入
    - 用 `register_shutdown_signals()` 替换内联信号注册
    - _Requirements: 1.6, 4.2_

- [x] 5. Checkpoint - 确保内部导入正确
  - 确保所有 `src/main/` 内部模块的导入路径已更新且无错误，ask the user if questions arise.

- [x] 6. 建立向后兼容重导出层
  - [x] 6.1 创建 `src/main/utils/config_loader.py` 重导出文件
    - 从 `src.main.config.config_loader` 重导出 `ConfigLoader`
    - _Requirements: 6.1, 6.3_

  - [x] 6.2 创建 `src/main/utils/log_handler.py` 重导出文件
    - 从 `src.main.utils.logging_setup` 重导出 `setup_logging`
    - _Requirements: 6.4_

  - [x] 6.3 创建 `src/main/gateway.py` 重导出文件
    - 从 `src.main.config.gateway_manager` 重导出 `GatewayManager`、`GatewayStatus`、`GatewayState`
    - _Requirements: 6.4_

  - [x] 6.4 创建 `src/main/child_process.py` 重导出文件
    - 从 `src.main.process.child_process` 重导出 `ChildProcess`
    - _Requirements: 6.4_

  - [x] 6.5 创建 `src/main/parent_process.py` 重导出文件
    - 从 `src.main.process.parent_process` 重导出 `ParentProcess`
    - _Requirements: 6.4_

  - [x] 6.6 更新 `src/main/process/__init__.py` 和 `src/main/config/__init__.py` 的导出
    - _Requirements: 8.3_

  - [ ]* 6.7 为向后兼容导入编写属性测试
    - **Property 4: 导入路径向后兼容性**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

- [x] 7. Final checkpoint - 确保所有测试通过
  - 确保所有测试通过，验证外部模块（`src/strategy`、`src/backtesting`）的导入无报错，ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 每个任务引用了具体的需求编号以确保可追溯性
- Checkpoints 确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
