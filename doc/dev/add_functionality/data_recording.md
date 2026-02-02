# 行情数据记录方案

本方案详细说明如何利用 `vnpy_datarecorder` 和 `vnpy_mysql` 将策略运行所需的行情信息自动记录到 MySQL 数据库中。

## 1. 方案概述

系统采用 vn.py 的标准组件 `vnpy_datarecorder` (行情记录模块) 和 `vnpy_mysql` (数据库适配器) 实现数据持久化。

在本项目中，数据记录功能已**深度集成**到策略启动流程中，无需人工干预即可实现：
1.  **自动连接数据库**：启动时自动读取 `.env` 配置。
2.  **自动配置存储路径**：通过 Monkey Patch 将配置文件重定向到统一配置目录。
3.  **自动订阅合约**：解析策略配置文件，自动将策略用到的主力合约和期权合约加入录制列表。

---

## 2. 核心代码实现

### 2.1 数据库配置注入 (`src/main/child_process.py`)

在子进程启动时（`ChildProcess.run()`），会读取环境变量并将数据库配置注入到 vn.py 的全局设置 (`SETTINGS`) 中；若未配置 `VNPY_DATABASE_DRIVER`，则数据录制功能会自动降级关闭。

```python
# src/main/child_process.py
def _setup_vnpy_database_settings(self) -> None:
    from vnpy.trader.setting import SETTINGS

    driver = os.getenv("VNPY_DATABASE_DRIVER", "").strip()
    if not driver:
        self.recorder_enabled = False
        return

    SETTINGS["database.driver"] = driver
    SETTINGS["database.name"] = driver
    SETTINGS["database.database"] = os.getenv("VNPY_DATABASE_DATABASE", "").strip()
    SETTINGS["database.host"] = os.getenv("VNPY_DATABASE_HOST", "localhost").strip()
    SETTINGS["database.port"] = int(os.getenv("VNPY_DATABASE_PORT", "3306").strip() or 3306)
    SETTINGS["database.user"] = os.getenv("VNPY_DATABASE_USER", "").strip()
    SETTINGS["database.password"] = os.getenv("VNPY_DATABASE_PASSWORD", "")
    self.recorder_enabled = True
```

### 2.2 配置文件重定向 (`src/main/child_process.py`)

vn.py 默认会在用户根目录查找 `data_recorder_setting.json`。为了保持项目整洁，我们在子进程启动时通过 Hook 方式将其重定向到项目内的统一配置目录：`config/general/data_recorder_setting.json`。

```python
# src/main/child_process.py
def _patch_data_recorder_setting_path(self) -> None:
    import vnpy.trader.utility as vnpy_utility

    original_get_file_path = vnpy_utility.get_file_path
    config_path = PROJECT_ROOT / "config" / "general" / "data_recorder_setting.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if (not config_path.exists()) or config_path.stat().st_size == 0:
        config_path.write_text("{}", encoding="utf-8")

    def patched_get_file_path(filename: str):
        if filename == "data_recorder_setting.json":
            self.logger.info(f"Redirecting data_recorder_setting.json to: {config_path}")
            return config_path
        return original_get_file_path(filename)

    vnpy_utility.get_file_path = patched_get_file_path
```

### 2.3 自动添加录制任务 (`src/main/child_process.py`)

当策略订阅合约时（以及子进程的期权录制补全逻辑订阅合约时），会调用 `recorder_engine.add_bar_recording()` 将合约加入 Bar 录制任务。

```python
# src/main/child_process.py
def _init_data_recorder(self) -> None:
    from vnpy_datarecorder import DataRecorderApp, APP_NAME

    self.main_engine.add_app(DataRecorderApp)
    self.recorder_engine_name = APP_NAME
    self.recorder_engine = self.main_engine.get_engine(APP_NAME)
    self.logger.info("DataRecorder 已加载")

def _subscribe_and_record_bar(self, vt_symbol: str) -> None:
    # ... 订阅合约 ...
    if self.recorder_engine and hasattr(self.recorder_engine, "add_bar_recording"):
        self.recorder_engine.add_bar_recording(vt_symbol)
```

---

## 3. 使用指南

### 3.1 步骤一：安装依赖

确保环境已安装 `vnpy_mysql` 和 `vnpy_datarecorder`。

```bash
pip install vnpy_mysql vnpy_datarecorder cryptography
```

### 3.2 步骤二：配置数据库连接 (.env)

在项目根目录 (`.env`) 添加如下配置：

```ini
VNPY_DATABASE_DRIVER=mysql
VNPY_DATABASE_DATABASE=vnpy_data
VNPY_DATABASE_HOST=127.0.0.1
VNPY_DATABASE_PORT=3306
VNPY_DATABASE_USER=root
VNPY_DATABASE_PASSWORD=your_password
```

### 3.3 步骤三：运行策略

无需做任何额外操作，直接运行策略即可。

```bash
python src/main/main.py --config config/strategy_config.yaml
```

系统启动后，会自动：
1. 连接 MySQL 数据库。
2. 读取 YAML 配置文件中的合约列表。
3. 开始将这些合约的 1分钟 Bar 数据写入数据库表 `db_bar_data`。

---

## 4. 常见问题与验证

### 4.1 怎么确认正在录制？

查看 `data/logs/` 下的日志文件，寻找如下关键字：

```text
2023-12-25 09:30:01.123 [INFO] 加载DataRecorder应用
2023-12-25 09:30:01.125 [INFO] Redirecting data_recorder_setting.json to: ...
2023-12-25 09:30:01.200 [INFO] 开始自动配置DataRecorder，共 2 个标的合约
2023-12-25 09:30:01.205 [INFO] 注册Bar录制任务：IF2312.CFFEX
```

### 4.2 数据库里没有数据？

1.  **检查数据库服务**：确保 MySQL 服务正在运行。
2.  **检查数据库名**：确保 `.env` 中 `VNPY_DATABASE_DATABASE` 指定的数据库（如 `vnpy_data`）已在 MySQL 中创建。
3.  **检查市场时间**：只有在开盘时间，且有行情推送时，才会生成 Bar 数据。
4.  **检查 `data_recorder_setting.json`**：查看 `config/general/data_recorder_setting.json`，确认合约已被自动写入该文件。

### 4.3 是否支持 Tick 录制？

代码中默认注释掉了 Tick 录制以节省空间：

```python
# recorder_engine.add_tick_recording(vt_symbol)
```

如果需要，可以在 `src/main/child_process.py` 中取消该行注释。
