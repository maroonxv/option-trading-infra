# Flask 实时可视化监控系统完整方案

## 1. 方案概述

本方案构建了一个**非侵入式、解耦**的实时监控系统。监控服务独立于策略交易进程，通过**双层持久化机制**和**文件轮询**的方式，实现对策略运行状态（K线、指标、信号、订单）的毫秒级（受节流控制）监控，支持回测与实盘模式。

## 2. 系统架构设计

系统采用 **生产者-消费者** 模型，通过文件系统进行松耦合通信。

```mermaid
graph TD
    subgraph "交易/回测进程 (Producer)"
        A[Strategy Engine] -->|Tick/Bar| B(StrategyState)
        B -->|每分钟/每秒| C{保存触发器}
        C -->|关键事件 (成交/停止)| D[主存: data/pickle]
        C -->|每Bar更新 (带1秒节流)| E[监控快照: data/monitor]
    end

    subgraph "可视化进程 (Consumer)"
        E -.->|只读读取| F[DataReader]
        F -->|清洗 & 格式化| G[Flask API]
        G -->|JSON| H[浏览器前端 (ECharts)]
    end
```

## 3. 数据源与埋点 (Strategy Side)

数据直接来源于策略的核心聚合根 `StrategyState`。

### 3.1 数据来源对象
*   **K线与指标**: `self.master_df` (Pandas DataFrame)
    *   **核心**: `datetime`, `open_price`, `high_price`, `low_price`, `close_price`
    *   **MACD**: `macd_dif`, `macd_dea`, `macd_hist`
    *   **TD序列**: `td_buy_count`, `td_sell_count` (9/13)
    *   **信号**: `open_signal`, `close_signal`
*   **订单状态**: `self.orders` (Dict)
    *   包含所有活跃及最近完结的订单详情。

### 3.2 埋点与触发 (Breakpoints)
为了实现实时性且不影响性能，我们在 `src/strategy/domain/strategy_state.py` 中设置了两个保存点：

1.  **高频监控点 (Monitor Snapshot)**:
    *   **位置**: `update_master_df` 方法末尾（每根 K 线生成时触发）。
    *   **逻辑**: 调用 `save_monitor_state()`。
    *   **节流机制**: 内部检查 `time.time() - last_save_time < 1.0s`，防止回测时 IO 爆炸。
    *   **轻量化**: 仅截取最近 **3000 行** 数据写入 `data/monitor/strategy_state_{name}.pkl`。

2.  **低频存档点 (Main Archive)**:
    *   **位置**: `save_state` 方法（在 `on_trade`, `on_order`, `on_stop` 等关键事件触发）。
    *   **逻辑**: 全量保存数据到 `data/pickle/strategy_state_{name}.pkl`，并强制刷新一次监控快照。

## 4. 后端设计 (Flask Side)

后端位于 `src/visualization/`，负责数据读取与 API 暴露。

### 4.1 目录结构
```text
src/visualization/
├── app.py              # Flask 入口
├── reader.py           # 数据读取核心逻辑
├── utils.py            # JSON 序列化工具
└── templates/
    └── index.html      # 前端页面
```

### 4.2 核心逻辑 (`reader.py`)
*   **`get_available_strategies()`**: 扫描 `data/monitor/*.pkl`，按修改时间排序，返回策略列表。
*   **`load_state(filename)`**: 带重试机制（Retry=3）读取 Pickle 文件，防止文件读写冲突。
*   **`get_dashboard_data(filename)`**:
    *   **清洗**: 将 Pandas 的 `NaN`/`Inf` 转换为 Python `None` (JSON 兼容)。
    *   **格式化**:
        *   K线转为二维数组 `[open, close, low, high]`。
        *   提取 `td_buy_count` 为 9 或 13 的点生成标注数据。
        *   提取 `open_signal`/`close_signal` 生成买卖箭头标注。

### 4.3 API 接口
| 方法 | 路径 | 参数 | 描述 |
| :--- | :--- | :--- | :--- |
| GET | `/api/strategies` | 无 | 返回所有可用的监控策略文件列表 |
| GET | `/api/data` | `strategy={filename}` | 返回指定策略的 K 线、指标、订单全量数据 |

## 5. 前端设计 (Frontend)

采用 **Bootstrap 5** 布局 + **ECharts 5** 绘图，风格简洁现代。

### 5.1 页面布局
*   **顶部**: 策略选择下拉框（实时切换不同策略实例，如 15m vs 30m）。
*   **左侧 (75%)**: 交互式图表区域 (高度 700px)。
*   **右侧 (25%)**:
    *   **活跃订单表**: 实时显示 `Order ID`, `方向`, `价格`, `状态`。
    *   **系统信息**: 显示当前 Pickle 文件路径、最后更新时间、自动刷新开关。

### 5.2 图表配置 (ECharts)
图表被配置为两个 Grid（上下排列，共享 X 轴缩放）：

#### Grid 1: 主图 (K线 & 信号)
*   **K线 (Candlestick)**: 红涨绿跌风格。
*   **TD 序列 (Scatter)**:
    *   **底 9/13**: 在 `Low` 下方显示绿色数字 (如 "B9")。
    *   **顶 9/13**: 在 `High` 上方显示红色数字 (如 "S9")。
*   **交易信号 (Scatter)**:
    *   **Open**: 黄色向下箭头（卖出开仓）。
    *   **Close**: 蓝色向上箭头（买入平仓）。

#### Grid 2: 副图 (MACD)
*   **MACD柱 (Bar)**: 红绿柱状图。
*   **DIF/DEA (Line)**:
    *   DIF: 橙色线。
    *   DEA: 蓝色线。

### 5.3 交互逻辑
*   **自动刷新**: `setInterval` 每 3 秒轮询一次 `/api/data`。
*   **策略切换**: 下拉框 `change` 事件触发立即重载数据。
*   **缩放保持**: ECharts 配置了 `dataZoom`，刷新数据时保持用户当前的缩放和滚动位置。

## 6. 使用说明

### 6.1 启动步骤
1.  **启动监控**: 运行根目录下的 `run_dashboard.bat`。
    *   访问地址: `http://localhost:5000`
2.  **运行策略**: 运行 `run_all_config.bat` (回测) 或 `run_paper.bat` (实盘)。

### 6.2 预期行为
*   策略启动后，会自动在 `data/monitor` 生成对应的 `.pkl` 文件。
*   Web 界面下拉框会出现该策略选项。
*   选中后，图表会随着策略运行（回测进度或实盘行情）实时跳动更新。
