# 独立行情录制工具方案

本方案旨在创建一个独立的行情录制工具，允许在不运行任何交易策略的情况下，单独启动程序进行行情数据（Tick/Bar）的录制。这对于数据积累、盘后分析以及减少生产环境策略进程的负载非常有价值。

## 1. 目标

创建一个独立的启动脚本和批处理文件，实现以下功能：
1.  **独立运行**：不依赖策略引擎，仅运行主引擎、事件引擎、CTP网关和行情记录模块。
2.  **环境复用**：复用现有的 `.env` 网关配置和 `data_recorder_setting.json` 录制配置。
3.  **轻量级**：仅订阅必要的合约，降低系统资源消耗。

## 2. 详细设计

### 2.1 Python 启动脚本 (`src/main/run_recorder.py`)

我们将创建一个新的 Python 入口文件 `src/main/run_recorder.py`。该脚本将执行以下步骤：

1.  **初始化环境**：
    *   设置日志记录 (`setup_logging`)。
    *   加载 `.env` 文件中的网关配置。
    *   注入数据库配置到 `vnpy.trader.setting.SETTINGS`。

2.  **创建引擎**：
    *   实例化 `EventEngine`。
    *   实例化 `MainEngine`。
    *   加载 `DataRecorderApp` (vnpy_datarecorder)。

3.  **配置重定向**：
    *   使用 Monkey Patch 技术（类似 `ChildProcess` 中的实现），将 vn.py 默认的 `data_recorder_setting.json` 路径重定向到项目配置文件路径 `config/general/data_recorder_setting.json`。

4.  **连接网关**：
    *   实例化 `CtpGateway` 并添加到主引擎。
    *   根据 `.env` 配置连接 CTP 前置机。
    *   等待网关连接成功及合约查询完成。

5.  **启动录制**：
    *   `DataRecorderApp` 会自动读取 `data_recorder_setting.json` 中的配置。
    *   在网关连接且合约就绪后，`RecorderEngine` 会自动订阅配置中的合约并开始录制。
    *   脚本将进入无限循环（`while True: sleep(1)`）以保持进程活跃。

### 2.2 批处理文件 (`run_datarecorder.bat`)

在项目根目录下创建一个批处理文件，用于一键启动录制进程。

**文件内容示例：**

```batch
@echo off
set PYTHONPATH=%cd%
call .venv\Scripts\activate.bat
python src\main\run_recorder.py --log-level INFO
pause
```

### 2.3 配置文件说明

*   **网关配置**：继续使用项目根目录下的 `.env` 文件。
*   **录制配置**：继续使用 `config/general/data_recorder_setting.json`。
    *   该文件是一个 JSON 对象，包含 `tick` 和 `bar` 两个列表，分别存储需要录制的合约代码。
    *   **注意**：由于独立录制器不加载策略，因此无法像主程序那样“自动发现”策略需要的合约。用户需要确保 `data_recorder_setting.json` 中已经包含了所有需要录制的合约。或者，我们可以编写一个小工具脚本，根据策略配置更新这个 JSON 文件。

## 3. 实现步骤

1.  **编写 `src/main/run_recorder.py`**：
    *   参考 `src/main/child_process.py` 中的引擎初始化、网关连接和配置重定向逻辑。
    *   剥离掉策略相关的逻辑。

2.  **编写 `run_datarecorder.bat`**：
    *   确保正确设置 `PYTHONPATH` 和虚拟环境。

3.  **测试验证**：
    *   启动 `run_datarecorder.bat`。
    *   观察日志确认 CTP 连接成功。
    *   观察日志确认 DataRecorder 模块加载成功且读取了配置文件。
    *   检查数据库确认数据正在写入。

## 4. 优势

*   **解耦**：录制与交易分离，降低单点故障风险。
*   **灵活**：可以在非交易时段（如周末测试连接）或仅需收集数据时单独运行。
*   **稳定**：减少了策略计算逻辑的干扰，录制进程更加稳定。
