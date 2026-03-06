import calendar
import math
from datetime import date
from typing import Callable, Dict, List, Optional, Tuple

from vnpy.trader.object import ContractData

from src.strategy.domain.value_object.selection.selection import MarketData
from src.strategy.infrastructure.parsing.contract_helper import ContractHelper


class FutureSelectionService:
    """
    期货合约选择服务。

    职责:
    - select_dominant_contract: 基于成交量/持仓量加权得分选择主力合约（无行情则报错）
    - select_by_expiration: 基于到期日范围筛选合约
    - check_rollover: 检查当前合约剩余天数是否大于阈值（返回 bool）
    """

    def __init__(self, config: Optional["FutureSelectorConfig"] = None):
        from src.strategy.domain.value_object.config.future_selector_config import FutureSelectorConfig

        self._config = config or FutureSelectorConfig()

    def select_dominant_contract(
        self,
        contracts: List[ContractData],
        current_date: date,
        market_data: Optional[Dict[str, MarketData]] = None,
        log_func: Optional[Callable[[str], None]] = None,
    ) -> Optional[ContractData]:
        """
        基于成交量/持仓量加权得分选择主力合约。

        规则:
        - 空合约列表返回 None
        - 必须提供完整的 market_data（每个候选合约都要有 volume/open_interest）
        - 若缺少数据，抛出 ValueError
        """
        _ = current_date  # 保留参数以保持调用兼容

        if not contracts:
            return None

        if not market_data:
            raise ValueError("缺少成交量/持仓量数据: market_data 不能为空")

        volume_weight = self._config.volume_weight
        oi_weight = self._config.oi_weight

        scores: List[Tuple[ContractData, float]] = []
        for contract in contracts:
            md = market_data.get(contract.vt_symbol)
            if md is None:
                raise ValueError(f"缺少合约 {contract.vt_symbol} 的成交量/持仓量数据")

            try:
                volume = float(md.volume)
                open_interest = float(md.open_interest)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"合约 {contract.vt_symbol} 的成交量/持仓量数据无效"
                ) from exc

            if not math.isfinite(volume) or not math.isfinite(open_interest):
                raise ValueError(f"合约 {contract.vt_symbol} 的成交量/持仓量数据无效")

            score = volume * volume_weight + open_interest * oi_weight
            scores.append((contract, score))

        selected, selected_score = max(scores, key=lambda x: x[1])
        if log_func:
            log_func(
                f"选择主力合约: {selected.vt_symbol}, "
                f"得分: {selected_score:.2f}"
            )
        return selected

    def select_by_expiration(
        self,
        contracts: List[ContractData],
        current_date: date,
        mode: str = "current_month",
        date_range: Optional[Tuple[date, date]] = None,
        log_func: Optional[Callable[[str], None]] = None,
    ) -> List[ContractData]:
        """
        基于到期日解析过滤合约。

        Args:
            contracts: 可用合约列表
            current_date: 当前日期
            mode: 过滤模式 - "current_month" | "next_month" | "custom"
            date_range: 仅 mode="custom" 时使用，(start_date, end_date) 闭区间
            log_func: 日志回调函数

        Returns:
            过滤后的合约列表
        """
        if not contracts:
            return []

        # 确定目标日期范围
        if mode == "current_month":
            range_start = date(current_date.year, current_date.month, 1)
            last_day = calendar.monthrange(current_date.year, current_date.month)[1]
            range_end = date(current_date.year, current_date.month, last_day)
        elif mode == "next_month":
            if current_date.month == 12:
                next_year = current_date.year + 1
                next_month = 1
            else:
                next_year = current_date.year
                next_month = current_date.month + 1
            range_start = date(next_year, next_month, 1)
            last_day = calendar.monthrange(next_year, next_month)[1]
            range_end = date(next_year, next_month, last_day)
        elif mode == "custom":
            if date_range is None:
                if log_func:
                    log_func("custom 模式需要提供 date_range 参数")
                return []
            range_start, range_end = date_range
        else:
            if log_func:
                log_func(f"未知的过滤模式: {mode}")
            return []

        # 过滤合约
        result = []
        for contract in contracts:
            expiry = ContractHelper.get_expiry_from_symbol(contract.symbol)
            if expiry is None:
                if log_func:
                    log_func(f"无法解析合约 {contract.symbol} 的到期日，已排除")
                continue
            if range_start <= expiry <= range_end:
                result.append(contract)

        return result

    def check_rollover(
        self,
        current_contract: ContractData,
        current_date: Optional[date] = None,
        log_func: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        检查剩余天数是否大于移仓阈值，返回 bool。

        返回:
        - True: remaining_days > rollover_days
        - False: remaining_days <= rollover_days
        """
        if current_date is None:
            raise ValueError("current_date 不能为空")

        expiry = ContractHelper.get_expiry_from_symbol(current_contract.symbol)
        if expiry is None:
            raise ValueError(f"无法解析合约 {current_contract.symbol} 的到期日")

        remaining_days = (expiry - current_date).days
        result = remaining_days > self._config.rollover_days

        if log_func:
            log_func(
                f"合约 {current_contract.symbol} 剩余 {remaining_days} 天, "
                f"阈值 {self._config.rollover_days} 天, "
                f"检查结果: {result}"
            )

        return result
