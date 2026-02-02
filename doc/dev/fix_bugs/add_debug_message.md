# 增加详细调试信息方案

为了验证 `README.md` (1-45行) 中描述的“商品卖权震荡策略”是否按预期运行，特别是 **MACD计算**、**九转序列(TD)信号**、**底背离判断** 以及 **自动开平仓逻辑**，我们需要在关键路径增加结构化的调试日志。

## 1. 调试目标

1.  **验证指标准确性**: 确认 MACD (Diff, DEA, Bar) 和 TD 9转计数是否与文华财经/通达信等软件一致。
2.  **验证信号触发逻辑**: 明确记录为何产生（或未产生）“钝化”和“背离”信号。
3.  **验证期权选择**: 确认是否选中了正确的虚值档位期权。
4.  **验证交易执行**: 记录开平仓条件的判断过程。

## 2. 日志增强详细设计

我们将引入统一的日志前缀 `[DEBUG]` 以便在海量日志中快速筛选。

### 2.1 领域服务层：指标计算 (IndicatorService)

**文件**: `src/strategy/domain/domain_service/indicator_service.py`

在 `calculate_all` 方法返回结果前，打印计算出的核心指标数值。

**新增日志内容**:
```text
[DEBUG-IND] {vt_symbol} {interval} | Close: {close}
[DEBUG-IND] {vt_symbol} MACD | Diff: {diff:.3f}, DEA: {dea:.3f}, MACD: {macd:.3f}
[DEBUG-IND] {vt_symbol} TD   | Count: {td_count}, Setup: {td_setup}, Flags: {flags}
[DEBUG-IND] {vt_symbol} EMA  | Fast: {ema_fast:.3f}, Slow: {ema_slow:.3f}
```

### 2.2 领域服务层：信号判断 (SignalService)

这是策略的核心逻辑，需要详细记录“为什么”触发或不触发。

**文件**: `src/strategy/domain/domain_service/signal_service.py`

由于 `SignalService` 是无状态静态类，需要在方法签名中增加 `log_func` 参数。

#### 2.2.1 钝化检测 (check_dullness)
在判断金叉/死叉及价格创新低/新高时记录：

**新增日志内容**:
```text
[DEBUG-SIG] {vt_symbol} 钝化检查 | 当前Diff: {current_diff}, 上次金叉Diff: {last_gold_cross_diff}
[DEBUG-SIG] {vt_symbol} 钝化状态 | 底背离钝化: {is_bottom_dull}, 顶背离钝化: {is_top_dull}
```

#### 2.2.2 背离检测 (check_divergence)
在钝化状态下，DIF 拐头或交叉时记录：

**新增日志内容**:
```text
[DEBUG-SIG] {vt_symbol} 背离确认 | 钝化中... 判断DIF拐头: 当前{curr} vs 前值{prev}
[DEBUG-SIG] {vt_symbol} 结构形成! | 底背离: {bottom_confirmed}, 顶背离: {top_confirmed}
```

#### 2.2.3 开仓信号 (check_open_signal)
记录所有开仓条件的检查结果 (AND 逻辑)。

**新增日志内容**:
```text
[DEBUG-DECISION] {vt_symbol} 开仓检查:
  1. TD信号: {td_signal} (预期: TD9/TD13)
  2. 背离状态: {divergence_state} (预期: 底背离)
  3. 均线过滤: {ema_filter} (预期: 收盘价 > EMA慢线)
  -> 最终结果: {result}
```

### 2.3 应用服务层：流程编排 (VolatilityTrade)

**文件**: `src/strategy/application/volatility_trade.py`

`VolatilityTrade` 持有 `strategy_context`，可以调用 `self._log()`。它需要将此日志方法传递给领域服务。

#### 2.3.1 期权选择 (Option Selection)
在 `_select_option` 方法中，记录筛选过程，特别是为了排查“所有合约被过滤”的问题。

**新增日志内容**:
```text
[DEBUG-OPT] 标的: {underlying} 价格: {price} | 开始筛选 {option_type} 期权
[DEBUG-OPT] 初步筛选数量: {count}
[DEBUG-OPT] 流动性过滤后: {count} (MinBid: {min_bid})
[DEBUG-OPT] 虚值排序前5:
  1. {symbol} Diff1: {diff1:.2%} Bid: {bid}
  2. ...
[DEBUG-OPT] 最终选中: {target_symbol} (虚值第{level}档)
```

#### 2.3.2 交易执行
在 `_check_and_execute_open` 和 `close` 中。

**新增日志内容**:
```text
[DEBUG-EXEC] 触发开仓 | 信号: {signal}, 标的: {underlying} -> 期权: {option}
[DEBUG-EXEC] 资金计算 | 余额: {balance}, 保证金/手: {margin}, 计划手数: {volume}
```

## 3. 实施计划

1.  **修改 `IndicatorService`**: 引入 `logging` 模块 (或接受 logger)，在计算逻辑末尾添加 `[DEBUG-IND]` 日志。
2.  **修改 `SignalService`**: 修改 `check_open_signal`, `check_dullness`, `check_divergence` 方法签名，增加 `log_func: Optional[Callable] = None` 参数。
3.  **修改 `VolatilityTrade`**:
    - 在调用 `IndicatorService.calculate_all` 时传入 log function (如果支持)。
    - 在调用 `SignalService` 的方法时，传入 `self._log`。
4.  **修改 `OptionSelectorService`**: 在筛选链条中打印每一步剩余的合约数量和被剔除的原因。
5.  **运行回测**: 使用 `src/backtesting/run_backtesting.py` 运行一小段区间（如1个月），将日志输出重定向到文件。
6.  **日志分析**: 搜索 `[DEBUG` 关键字，逐条比对策略逻辑与执行结果。

## 4. 示例代码片段 (SignalService)

```python
    @staticmethod
    def check_open_signal(
        instrument: TargetInstrument, 
        log_func: Optional[callable] = None
    ) -> Optional[SignalType]:
        
        td = instrument.td_value
        dullness = instrument.dullness_state
        divergence = instrument.divergence_state
        
        # 1. 检查 TD 9
        # is_td_buy = (td.td_count == 9 and td.td_setup) # 注意: td_setup 是 int, 需确认逻辑
        is_td_buy = td.has_buy_8_9 # 使用封装好的属性
        
        if log_func: 
            log_func(f"[DEBUG-DECISION] {instrument.vt_symbol} TD Check: Buy8/9={is_td_buy}, Count={td.td_count}")
        
        if not is_td_buy:
            # return None # 暂时不返回，继续检查背离，或者根据逻辑
            pass
            
        # ...
```