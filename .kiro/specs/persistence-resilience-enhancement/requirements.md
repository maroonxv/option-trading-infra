# Requirements Document

## Introduction

本文档定义了 VnPy 交易系统持久化架构增强的需求。当前架构存在多个脆弱点：pickle 序列化对类结构变更敏感、状态仅在 on_stop 时保存导致崩溃丢失数据、数据库配置注入缺乏连接验证、回测使用 monkey-patch 等。本增强旨在提升系统的容错性、可恢复性和可维护性。

## Glossary

- **State_Repository**: 负责策略状态持久化的基础设施组件（当前实现位于 `src/strategy/infrastructure/persistence/state_repository.py`）
- **Strategy_Entry**: VnPy 策略模板实现，策略的入口类（`src/strategy/strategy_entry.py`）
- **Aggregate_Snapshot**: 聚合根的状态快照，包含 InstrumentManager 和 PositionAggregate 的序列化数据
- **Auto_Save_Service**: 周期性自动保存策略状态的服务
- **Schema_Version**: 序列化数据的版本号，用于支持向后兼容的迁移
- **Migration_Chain**: 从旧版本数据迁移到新版本的转换函数链
- **Database_Factory**: 统一的数据库连接工厂，负责创建和验证数据库连接（当前初始化逻辑位于 `src/main/bootstrap/database_setup.py`）
- **Corruption_Error**: 状态文件存在但无法正确反序列化的错误类型
- **Archive_Not_Found**: 状态文件不存在的情况（正常的首次启动）

## Requirements

### Requirement 1: Periodic Auto-Save

**User Story:** As a trader, I want the strategy state to be automatically saved periodically, so that I don't lose position information if the process crashes unexpectedly.

#### Acceptance Criteria

1. GIVEN the strategy is running in live trading mode, WHEN on_bars is called AND the configured auto-save interval has elapsed since the last save, THEN the Auto_Save_Service SHALL save the current Aggregate_Snapshot to disk
2. GIVEN the Auto_Save_Service is initialized, WHEN no custom interval is provided, THEN the Auto_Save_Service SHALL use a default interval of 60 seconds for auto-save frequency
3. GIVEN on_bars is called at high frequency, WHEN the time since last save is less than the configured interval, THEN the Auto_Save_Service SHALL skip the save to prevent excessive disk I/O
4. GIVEN auto-save is triggered, WHEN writing the Aggregate_Snapshot to disk, THEN the Auto_Save_Service SHALL write to a temporary file first and then atomically rename it to the target path
5. GIVEN auto-save is triggered, WHEN the file write operation fails, THEN the Auto_Save_Service SHALL log the error and continue strategy execution without interruption
6. GIVEN the strategy is running in backtesting mode, WHEN on_bars is called, THEN the Auto_Save_Service SHALL NOT perform any disk write operations

### Requirement 2: Fail-Fast on State Load Error

**User Story:** As a trader, I want the system to distinguish between "no archive" and "corrupted archive" scenarios, so that I can take appropriate action when state recovery fails.

#### Acceptance Criteria

1. GIVEN the strategy is initializing, WHEN loading state AND the archive file does not exist, THEN the State_Repository SHALL return a distinct Archive_Not_Found result and allow the strategy to continue with empty state
2. GIVEN the strategy is initializing, WHEN loading state AND the archive file exists but deserialization fails, THEN the State_Repository SHALL raise a Corruption_Error with detailed error information
3. GIVEN a Corruption_Error is raised during on_init, WHEN the Strategy_Entry receives the error, THEN the Strategy_Entry SHALL fail-fast and prevent the strategy from starting with potentially inconsistent state
4. GIVEN a Corruption_Error occurs, WHEN constructing the error, THEN the State_Repository SHALL include the original exception details and file path in the error message
5. GIVEN an archive file exists, WHEN integrity check is requested, THEN the State_Repository SHALL provide a method to verify archive integrity without fully loading the state into memory

### Requirement 3: Database Connection Validation

**User Story:** As a system administrator, I want the system to validate database connectivity at startup, so that configuration errors are detected early rather than causing silent data loss.

#### Acceptance Criteria

1. GIVEN the application is starting, WHEN database initialization is invoked, THEN the Database_Factory SHALL attempt to connect to the configured MySQL database
2. GIVEN the application is starting, WHEN the database connection fails within the timeout period (default: 5 seconds), THEN the Database_Factory SHALL raise a connection error and prevent application startup
3. GIVEN the application is starting, WHEN required environment variables (VNPY_DATABASE_DRIVER, VNPY_DATABASE_HOST, VNPY_DATABASE_DATABASE, VNPY_DATABASE_USER, VNPY_DATABASE_PASSWORD) are missing, THEN the Database_Factory SHALL raise a configuration error with a clear message indicating which variables are missing
4. GIVEN VNPY_DATABASE_DRIVER is set to "mysql", WHEN the MySQL connection fails, THEN the Database_Factory SHALL NOT silently fall back to SQLite
5. GIVEN the database connection is validated successfully, WHEN startup completes, THEN the Database_Factory SHALL log the connection details (host, database name) for operational visibility

### Requirement 4: JSON Serialization with Versioning

**User Story:** As a developer, I want the state serialization to use JSON with schema versioning, so that class structure changes don't break state recovery.

#### Acceptance Criteria

1. GIVEN an Aggregate_Snapshot needs to be persisted, WHEN the State_Repository serializes it, THEN the output SHALL be in JSON format instead of pickle
2. GIVEN the State_Repository is serializing state, WHEN producing JSON output, THEN the output SHALL include a schema_version field at the top level
3. GIVEN the State_Repository is deserializing state, WHEN the schema_version in the file does not match the current version, THEN the State_Repository SHALL apply the Migration_Chain to transform the data to the current version
4. GIVEN a new schema version is introduced, WHEN a migration function is added to the Migration_Chain, THEN existing migration functions SHALL remain unchanged and backward compatibility SHALL be preserved
5. GIVEN an Aggregate_Snapshot contains pandas DataFrame fields, WHEN serializing, THEN the State_Repository SHALL convert DataFrames to records format (list of dicts)
6. GIVEN JSON state data contains DataFrame fields in records format, WHEN deserializing, THEN the State_Repository SHALL reconstruct pandas DataFrames from the records
7. GIVEN an existing pickle-format state file is present, WHEN the State_Repository loads state during the transition period, THEN it SHALL detect the pickle format and load it successfully for backward compatibility
8. GIVEN any valid Aggregate_Snapshot object, WHEN it is serialized and then deserialized, THEN the resulting object SHALL be equivalent to the original (round-trip property)

### Requirement 5: Unified Database Factory

**User Story:** As a developer, I want a unified database factory module, so that database initialization logic is not duplicated across live trading and backtesting code.

#### Acceptance Criteria

1. GIVEN any module in the system needs database access, WHEN requesting a connection, THEN the Database_Factory SHALL provide a single entry point for obtaining database connections
2. GIVEN the backtesting module needs database access, WHEN requesting a connection, THEN the Database_Factory SHALL provide the same MySQL connection without requiring monkey-patch of VnPy internals
3. GIVEN the Database_Factory is initialized, WHEN table name configuration is needed, THEN the Database_Factory SHALL encapsulate the table name configuration (dbbardata, dbtickdata) internally
4. GIVEN a VnPy version upgrade changes database initialization APIs, WHEN the Database_Factory is updated, THEN the changes SHALL be isolated to the Database_Factory module only
5. GIVEN the Database_Factory is configured, WHEN initialization is requested, THEN it SHALL support both eager (synchronous) and lazy initialization patterns
6. GIVEN multiple modules request database connections concurrently, WHEN the Database_Factory provides connections, THEN it SHALL return the same singleton instance
