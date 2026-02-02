from abc import ABC, abstractmethod
from typing import List, Optional, Any

class IAccountGateway(ABC):
    """账户资金/持仓网关接口"""
    
    @abstractmethod
    def get_balance(self) -> float:
        """获取可用资金"""
        pass

    @abstractmethod
    def get_position(self, vt_symbol: str, direction: Any) -> Optional[Any]:
        """
        获取特定持仓
        
        Args:
            vt_symbol: 合约代码
            direction: 持仓方向 (Long/Short)
        """
        pass

    @abstractmethod
    def get_all_positions(self) -> List[Any]:
        """获取所有持仓"""
        pass
