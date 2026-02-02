from abc import ABC, abstractmethod
from typing import List, Optional, Any

class IMarketDataGateway(ABC):
    """市场数据网关接口"""
    
    @abstractmethod
    def subscribe(self, vt_symbol: str) -> None:
        """订阅行情"""
        pass

    @abstractmethod
    def get_tick(self, vt_symbol: str) -> Optional[Any]:
        """获取最新 Tick 快照"""
        pass

    @abstractmethod
    def get_contract(self, vt_symbol: str) -> Optional[Any]:
        """获取合约详情"""
        pass

    @abstractmethod
    def get_all_contracts(self) -> List[Any]:
        """获取所有合约"""
        pass
