# 股指期权 MACD-TD 策略

## 一、策略简介

本策略基于 15/30/60 分钟级别的 K 线数据，结合 MACD 钝化、背离及 TD 序列指标，在股指期货及其对应的期权上进行**卖出期权（Short Option）**操作。策略主要包含“卖沽（Sell Put）”和“卖购（Sell Call）”两个子策略。（做虚四档！）

### 1. 卖沽策略（看多震荡/反弹）
适用于判断底部形成或上涨中继阶段。

**（一）钝化 + 低9**
*   **开仓条件**：
    1.  标的 K 线创新低。
    2.  MACD DIFF 值未创新低（底背离雏形/钝化形成）。
    3.  TD 序列出现低 8。
    *   **操作**：卖出当月认沽期权（Sell Put），虚值四档。
*   **平仓条件**：
    *   **止盈**：TD 序列出现高 8，或 DIFF 值形成顶背离。
    *   **止损**：钝化失效（DIFF 值创出新低）。

**（二）底背离**
*   **开仓条件**：
    1.  钝化形成后，下一根 K 线收盘价高于前一根（确认背离形成）。
    *   **操作**：卖出当月认沽期权（Sell Put），虚值四档。
*   **平仓条件**：
    *   **止盈**：TD 序列出现高 8，或 DIFF 值钝化消失。
    *   **止损**：底背离失效（DIFF 值创出新低）。

### 2. 卖购策略（看空震荡/回调）
适用于判断顶部形成或下跌中继阶段。

**（一）钝化 + 高9**
*   **开仓条件**：
    1.  标的 K 线创新高。
    2.  MACD DIFF 值未创新高（顶背离雏形/钝化形成）。
    3.  TD 序列出现高 8。
    *   **操作**：卖出当月认购期权（Sell Call），虚值四档。
*   **平仓条件**：
    *   **止盈**：TD 序列出现低 8，或 DIFF 值形成底背离。
    *   **止损**：钝化失效（DIFF 值创出新高）。

**（二）顶背离**
*   **开仓条件**：
    1.  钝化形成后，下一根 K 线收盘价低于前一根（确认背离形成）。
    *   **操作**：卖出当月认购期权（Sell Call），虚值四档。
*   **平仓条件**：
    *   **止盈**：TD 序列出现低 8，或 DIFF 值钝化消失。
    *   **止损**：顶背离失效（DIFF 值创出新高）。

## 二、Docker 部署指南

本项目推荐使用 Docker 进行容器化部署，以实现环境隔离、一键启动和数据持久化。

### 1. 部署架构
我们采用“统一镜像，多服务编排”的架构，所有服务共享同一个 Docker 镜像：
*   **`mysql-db`**: 数据库服务 (MySQL 8.0)，负责存储行情与交易记录。
*   **`dashboard`**: 监控面板服务，提供 Web 界面查看策略状态 (端口 5007)。
*   **`strategy-15m`**: 15分钟周期策略服务 (示例)。
*   *(可选)*: 如需更多周期 (如 1h)，可直接复制 strategy 服务块并修改配置。

### 2. 快速开始

#### 步骤 1: 准备数据
首次部署前，请联系项目开发人员获取最新的数据库备份文件 `init.sql`（包含基础配置和历史行情数据）。

**操作**：将获取到的 `init.sql` 文件放入项目的 `deploy/init_data/` 目录下。
*(Docker 容器首次启动时会自动检测并执行该目录下的 SQL 文件进行初始化)*

> **注意**：`init.sql` 已被 git 忽略，请务必手动获取并放置。

#### 步骤 2: 启动服务
进入 `deploy` 目录并启动所有服务：

```powershell
cd deploy
docker-compose up -d --build
```

#### 步骤 3: 验证运行
*   **查看状态**: `docker-compose ps` 确保所有容器状态为 `Up`。
*   **访问面板**: 浏览器打开 [http://localhost:5007](http://localhost:5007)。
*   **查看日志**:
    ```powershell
    docker-compose logs -f strategy-15m  # 查看策略日志
    docker-compose logs -f dashboard     # 查看监控面板日志
    ```

### 3. 配置说明
*   **文件位置**: 所有 Docker 相关文件位于 `deploy/` 目录下。
*   **环境变量**: 修改 `deploy/.env` 文件可调整数据库密码等敏感信息。
*   **策略配置**: 宿主机的 `config/` 目录已挂载到容器内。修改本地配置文件后，**重启容器即可生效**，无需重新构建镜像。

---

## 三、运行配置指南

本策略的配置文件位于 `config/` 目录下，分为**基础策略配置**、**交易标的配置**和**多周期差异化配置**三部分。

### 1. 基础策略配置 (`config/strategy_config.yaml`)
此文件定义了策略的**全局默认参数**和**运行时环境**。所有时间周期的策略进程默认都会加载此配置，除非被差异化配置覆盖。

*   **策略参数 (`strategies.setting`)**：
    *   `max_positions`: 策略允许持有的最大合约数量（风控限制）。
    *   `strike_level`: 期权选合约时的虚值档位（OTM Level），例如 `4` 表示虚值四档。
    *   `macd_fast`/`macd_slow`/`macd_signal`: MACD 指标参数。
    *   `ema_fast`/`ema_slow`: EMA 均线参数。

*   **运行时参数 (`runtime`)**：
    *   `trading_periods`: **交易时段**。守护进程会根据此时段自动启动或停止交易子进程。请根据实际交易所时间调整（例如包含夜盘时段）。
    *   `max_restart_count`: 子进程允许的最大异常重启次数。

### 2. 交易标的配置 (`config/general/trading_target.yaml`)
此文件定义了策略需要监控和交易的**股指期货品种代码**。

*   **格式**：YAML 列表格式。
*   **示例**：
    ```yaml
    - IF  # 沪深300股指期货
    - IM  # 中证1000股指期货
    ```
    策略启动时会自动加载这些品种的主力合约，并监控其对应的期权链。

### 3. 多周期差异化配置 (`config/timeframe/*.yaml`)
本策略支持同时运行多个不同时间周期的实例（如 15分钟、30分钟、60分钟等）。
项目采用自动扫描机制，您只需在 `config/timeframe/` 目录下管理配置文件即可。

#### 3.1 启用新周期
只需在 `config/timeframe/` 目录下创建一个新的 `.yaml` 配置文件。
`scripts/run.bat` 启动脚本会自动扫描该目录下所有的 `.yaml` 文件，并为每个文件启动一个独立的策略进程。

**示例**：
如果您想运行 15 分钟和 30分钟两个周期的策略，只需确保目录下存在以下文件：
- `config/timeframe/15m.yaml`
- `config/timeframe/30m.yaml`

#### 3.2 配置文件格式
配置文件内容主要用于覆盖默认配置中的 `strategy_name` 和 `bar_window` 参数。
例如 `15m.yaml` 的内容可以是：
```yaml
strategies:
  - strategy_name: "volatility_strategy_15m"
    setting:
      bar_window: 15
      bar_interval: "MINUTE"
```

#### 3.3 停用周期
若要暂时停用某个周期的策略，直接把对应配置文件删除即可


## 四、代码阅读指南（非技术人员版）

如果您是非技术背景的项目管理者或策略研究员，需要核对策略逻辑的实现细节，请关注以下核心模块。这些文件直接对应策略文档中的关键业务规则。

### 1. 策略配置与流程控制
*   **参数定义：`macd_td_index_strategy.py`**
    *   **位置**：[src/strategy/macd_td_index_strategy.py](src/strategy/macd_td_index_strategy.py)
    *   **功能**：策略的**参数配置中心**。
    *   **关注点**：所有可调整的策略参数均在此定义，包括 MACD 参数 (`macd_fast`, `macd_slow`)、虚值档位 (`strike_level`)、最大持仓限制 (`max_positions`) 等。修改策略参数直接调整此文件。

*   **主流程控制：`volatility_trade.py`**
    *   **位置**：[src/strategy/application/volatility_trade.py](src/strategy/application/volatility_trade.py)
    *   **功能**：策略的**执行协调层**。
    *   **关注点**：负责协调数据获取、指标计算、信号判断和交易执行的完整流程。如果需要了解策略的执行顺序（如：先更新行情 -> 再计算指标 -> 最后判断交易），请查看此文件。

### 2. 核心交易逻辑 (Domain Services)
此目录 (`src/strategy/domain/domain_service/`) 包含策略的具体业务规则实现。

*   **信号决策：`signal_service.py`（核心）**
    *   **位置**：[src/strategy/domain/domain_service/signal_service.py](src/strategy/domain/domain_service/signal_service.py)
    *   **功能**：**买卖点逻辑判断**。
    *   **关注点**：
        *   `check_open_signal`：**开仓条件**。核对代码是否正确实现了“底背离确认”、“钝化+低9”等进场逻辑。
        *   `check_close_signal`：**平仓条件**。核对止盈（如“高9”）和止损（如“背离失效”）的触发条件。

*   **合约筛选：`option_selector_service.py`**
    *   **位置**：[src/strategy/domain/domain_service/option_selector_service.py](src/strategy/domain/domain_service/option_selector_service.py)
    *   **功能**：**期权合约选择规则**。
    *   **关注点**：
        *   **虚值档位**：确认策略如何计算和选择“虚值三档/四档”合约。
        *   **流动性过滤**：检查最小成交量、买卖价差等过滤规则，确保不交易低流动性合约。

*   **指标计算：`indicator_service.py`**
    *   **位置**：[src/strategy/domain/domain_service/indicator_service.py](src/strategy/domain/domain_service/indicator_service.py)
    *   **功能**：**技术指标算法**。
    *   **关注点**：负责 MACD、TD 序列、EMA 等指标的具体计算逻辑。如有对“钝化”或“背离”定义的数学异议，请核对计算公式。

*   **仓位风控：`position_sizing_service.py`**
    *   **位置**：[src/strategy/domain/domain_service/position_sizing_service.py](src/strategy/domain/domain_service/position_sizing_service.py)
    *   **功能**：**交易数量计算与风控**。
    *   **关注点**：计算单次开仓数量（策略定为1手），并执行“单日最大交易次数”、“单品种最大持仓”等风控限制。

*   **主力切换：`future_selection_service.py`**
    *   **位置**：[src/strategy/domain/domain_service/future_selection_service.py](src/strategy/domain/domain_service/future_selection_service.py)
    *   **功能**：**期货主力合约换月**。
    *   **关注点**：定义了何时从当月合约切换到次月合约（例如：距离交割日不足7天时自动切换）。

### 3. 状态与数据管理 (Aggregates)
此目录 (`src/strategy/domain/aggregate/`) 负责维护策略运行时的状态数据。

*   **持仓管理：`position_aggregate.py`**
    *   **位置**：[src/strategy/domain/aggregate/position_aggregate.py](src/strategy/domain/aggregate/position_aggregate.py)
    *   **功能**：**持仓全生命周期管理**。
    *   **关注点**：记录当前持仓详情，追踪在途订单。包含检测**人工手动平仓**的逻辑，确保策略能感知人工干预。

*   **行情数据：`target_instrument_aggregate.py`**
    *   **位置**：[src/strategy/domain/aggregate/target_instrument_aggregate.py](src/strategy/domain/aggregate/target_instrument_aggregate.py)
    *   **功能**：**K线与指标数据容器**。
    *   **关注点**：存储标的物的历史行情数据及计算后的指标状态，供策略随时调用。

---
**快速索引**：
*   **调整参数** -> `macd_td_index_strategy.py`
*   **核对买卖逻辑** -> `signal_service.py`
*   **核对选合约规则** -> `option_selector_service.py`
*   **核对风控限额** -> `position_sizing_service.py`

