from datetime import date
from typing import List, Optional, Callable
from vnpy.trader.object import ContractData
from src.main.utils.contract_utils import ContractUtils


class FutureSelectionService:
    """
    选择当月期权合约，或者下月期权合约（若当月期权距离行权日不足7日）
    """
    
    def select_dominant_contract(
        self, 
        contracts: List[ContractData], 
        current_date: date,
        log_func: Optional[Callable[[str], None]] = None
    ) -> Optional[ContractData]:
        """  
        Args:
            contracts: 该品种的所有可用合约列表
            current_date: 当前日期
            log_func: 日志回调函数
            
        Returns:
            选中的主力合约对象
        """
        if not contracts:
            return None
            
        # 1. 按合约代码排序 (通常字母序等同于时间序，如 rb2501, rb2505, rb2510)
        sorted_contracts = sorted(contracts, key=lambda c: c.symbol)
        
        # 2. 定位当月合约 (排序后的第一个合约)
        current_month_contract = sorted_contracts[0]
        
        # 3. 解析到期日
        expiry_date = ContractUtils.get_expiry_from_symbol(current_month_contract.symbol)
        if not expiry_date:
            # 解析失败，保守策略：返回第一个
            if log_func:
                log_func(f"无法解析合约 {current_month_contract.symbol} 的到期日，默认选择当月合约")
            return current_month_contract
            
        # 4. 7天规则判断
        days_to_expiry = (expiry_date - current_date).days
        
        if days_to_expiry > 7:
            if log_func:
                log_func(f"合约 {current_month_contract.symbol} 距离到期还有 {days_to_expiry} 天 (>7天)，选择当月合约")
            return current_month_contract
        else:
            # 切换到次月
            if len(sorted_contracts) > 1:
                next_contract = sorted_contracts[1]
                if log_func:
                    log_func(f"合约 {current_month_contract.symbol} 距离到期仅剩 {days_to_expiry} 天 (<=7天)，切换至次月合约: {next_contract.symbol}")
                return next_contract
            else:
                if log_func:
                    log_func(f"合约 {current_month_contract.symbol} 距离到期仅剩 {days_to_expiry} 天，但未找到次月合约，被迫继续使用当月合约")
                return current_month_contract
