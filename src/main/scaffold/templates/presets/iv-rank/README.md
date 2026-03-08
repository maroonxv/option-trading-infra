# iv_rank

演示如何让指标服务读取统一期权链模型里的隐波数据，并输出 `iv_rank`。
- 指标：从 `context.option_chain` 提取平均 IV，滚动计算 IV Rank
- 开仓：IV Rank 高于阈值时发出开仓信号
- 平仓：IV Rank 回落时发出平仓信号
