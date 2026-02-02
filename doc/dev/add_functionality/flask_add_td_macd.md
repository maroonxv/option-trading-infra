# Flask 监控增强方案：集成 TD 序列与 MACD 信号

## 1. 目标
在现有的 Flask K线监控图表基础上，叠加显示 **TD 序列 (9/13)** 和 **MACD 状态**，以便直观判断策略的入场条件。

## 2. 需求分析

### 2.1 TD 序列可视化
*   **TD Setup (9)**: 在 K 线的高点或低点上方/下方显示数字 1-9。
    *   **买入结构 (Buy Setup)**: 连续 9 根收盘价低于 4 根前的收盘价 -> **底 9** (通常显示在 Low 下方)。
    *   **卖出结构 (Sell Setup)**: 连续 9 根收盘价高于 4 根前的收盘价 -> **顶 9** (通常显示在 High 上方)。
*   **TD Countdown (13)**: 在 K 线的高点或低点显示计数 1-13 (可选，视策略复杂度而定，目前主要关注 Setup 9)。
*   **展示形式**: ECharts `custom` 系列或 `scatter` 系列，在 K 线对应位置标注数字。

### 2.2 MACD 信号可视化
*   **MACD 柱状图**: 已经在副图中显示。
*   **背离信号 (Divergence)**:
    *   **底背离**: 价格创新低但 MACD 未创新低。
    *   **顶背离**: 价格创新高但 MACD 未创新高。
    *   **展示形式**: 在副图 MACD 或主图 K 线特定位置画**箭头**或**垂直线**标记。
*   **钝化信号 (Dullness)**:
    *   **顶部钝化/底部钝化**: 指示当前趋势可能衰竭。
    *   **展示形式**: 可以在副图区域用背景色块，或者在 K 线图顶部/底部显示状态条。

## 3. 实现方案

### 3.1 后端数据增强 (`reader.py`)

目前 `TargetInstrument.bars` DataFrame 中已经包含了 `td_count`, `td_setup` 等列 (参见 `src/strategy/domain/entity/target_instrument.py`)。

需要修改 `reader.py` 的 `_parse_instruments` 方法，提取这些列并打包给前端。

```python
# reader.py 伪代码
ohlc = []
td_marks = []  # 新增: TD 标记
macd_signals = [] # 新增: MACD 信号标记

for idx, row in bars_df.iterrows():
    # ... 原有 OHLC 提取 ...
    
    # 提取 TD
    td_count = row.get("td_count", 0)
    td_setup = row.get("td_setup", 0)
    
    # 简单处理：只提取 9 和 13，或者提取非零值
    if td_count != 0:
        td_marks.append({
            "coord": [dt_str, row["high"] if td_count > 0 else row["low"]],
            "value": int(td_count),
            "position": "top" if td_count > 0 else "bottom"
        })
```

### 3.2 前端 ECharts 改造 (`monitor.js`)

1.  **新增 Series (TD 标记)**:
    使用 `scatter` (散点图) 类型，将 symbol 设置为 `pin` 或纯文本，显示在 K 线上方/下方。

    ```javascript
    {
        name: 'TD Setup',
        type: 'scatter',
        data: td_data, // [{coord: ['2023-12-01 10:00', 3500], value: 9, ...}]
        symbolSize: 10,
        label: {
            show: true,
            formatter: '{@value}',
            position: 'top' // 动态调整
        }
    }
    ```

2.  **增强 Series (MACD 背离)**:
    使用 `markPoint` 在 MACD 图表上标注背离点。

    ```javascript
    series: [
        // ... MACD Bar ...
        {
            name: 'MACD',
            type: 'bar',
            // ...
            markPoint: {
                data: [
                    { name: '底背离', coord: ['2023-12-01 10:00', -5], itemStyle: {color: 'red'} }
                ]
            }
        }
    ]
    ```

## 4. 开发计划

1.  **修改 `reader.py`**:
    *   从 DataFrame 中读取 `td_count`, `td_setup` 列。
    *   将这些数据格式化为 ECharts 友好的 JSON 结构。
    *   (可选) 如果 DataFrame 中没有存具体的背离点，可能需要根据 `divergence_states` 简单反推或在快照中增加记录。

2.  **修改 `monitor.js`**:
    *   在 `renderChart` 函数中增加 TD 序列的 `series` 配置。
    *   优化 MACD 副图的显示，增加背离标记。

3.  **验证**:
    *   使用 `convert_pickle_to_snapshot.py` 生成包含 TD 数据的快照（确保源数据里有 TD 数据）。
    *   启动 Web 查看效果。


# Flask 监控增强方案：集成 TD 序列与 MACD 信号

## 1. 目标
在现有的 Flask K线监控图表基础上，叠加显示 **TD 序列 (9/13)** 和 **MACD 状态**，以便直观判断策略的入场条件。

## 2. 需求分析

### 2.1 TD 序列可视化
*   **TD Setup (9)**: 在 K 线的高点或低点上方/下方显示数字 1-9。
    *   **买入结构 (Buy Setup)**: 连续 9 根收盘价低于 4 根前的收盘价 -> **底 9** (通常显示在 Low 下方)。
    *   **卖出结构 (Sell Setup)**: 连续 9 根收盘价高于 4 根前的收盘价 -> **顶 9** (通常显示在 High 上方)。
*   **TD Countdown (13)**: 在 K 线的高点或低点显示计数 1-13 (可选，视策略复杂度而定，目前主要关注 Setup 9)。
*   **展示形式**: ECharts `custom` 系列或 `scatter` 系列，在 K 线对应位置标注数字。

### 2.2 MACD 信号可视化
*   **MACD 柱状图**: 已经在副图中显示。
*   **背离信号 (Divergence)**:
    *   **底背离**: 价格创新低但 MACD 未创新低。
    *   **顶背离**: 价格创新高但 MACD 未创新高。
    *   **展示形式**: 在副图 MACD 或主图 K 线特定位置画**箭头**或**垂直线**标记。
*   **钝化信号 (Dullness)**:
    *   **顶部钝化/底部钝化**: 指示当前趋势可能衰竭。
    *   **展示形式**: 可以在副图区域用背景色块，或者在 K 线图顶部/底部显示状态条。

## 3. 实现方案

### 3.1 后端数据增强 (`reader.py`)

目前 `TargetInstrument.bars` DataFrame 中已经包含了 `td_count`, `td_setup` 等列 (参见 `src/strategy/domain/entity/target_instrument.py`)。

需要修改 `reader.py` 的 `_parse_instruments` 方法，提取这些列并打包给前端。

```python
# reader.py 伪代码
ohlc = []
td_marks = []  # 新增: TD 标记
macd_signals = [] # 新增: MACD 信号标记

for idx, row in bars_df.iterrows():
    # ... 原有 OHLC 提取 ...
    
    # 提取 TD
    td_count = row.get("td_count", 0)
    td_setup = row.get("td_setup", 0)
    
    # 简单处理：只提取 9 和 13，或者提取非零值
    if td_count != 0:
        td_marks.append({
            "coord": [dt_str, row["high"] if td_count > 0 else row["low"]],
            "value": int(td_count),
            "position": "top" if td_count > 0 else "bottom"
        })
```

### 3.2 前端 ECharts 改造 (`monitor.js`)

1.  **新增 Series (TD 标记)**:
    使用 `scatter` (散点图) 类型，将 symbol 设置为 `pin` 或纯文本，显示在 K 线上方/下方。

    ```javascript
    {
        name: 'TD Setup',
        type: 'scatter',
        data: td_data, // [{coord: ['2023-12-01 10:00', 3500], value: 9, ...}]
        symbolSize: 10,
        label: {
            show: true,
            formatter: '{@value}',
            position: 'top' // 动态调整
        }
    }
    ```

2.  **增强 Series (MACD 背离)**:
    使用 `markPoint` 在 MACD 图表上标注背离点。

    ```javascript
    series: [
        // ... MACD Bar ...
        {
            name: 'MACD',
            type: 'bar',
            // ...
            markPoint: {
                data: [
                    { name: '底背离', coord: ['2023-12-01 10:00', -5], itemStyle: {color: 'red'} }
                ]
            }
        }
    ]
    ```

## 4. 开发计划

1.  **修改 `reader.py`**:
    *   从 DataFrame 中读取 `td_count`, `td_setup` 列。
    *   将这些数据格式化为 ECharts 友好的 JSON 结构。
    *   (可选) 如果 DataFrame 中没有存具体的背离点，可能需要根据 `divergence_states` 简单反推或在快照中增加记录。

2.  **修改 `monitor.js`**:
    *   在 `renderChart` 函数中增加 TD 序列的 `series` 配置。
    *   优化 MACD 副图的显示，增加背离标记。

3.  **验证**:
    *   使用 `convert_pickle_to_snapshot.py` 生成包含 TD 数据的快照（确保源数据里有 TD 数据）。
    *   启动 Web 查看效果。
