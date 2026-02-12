"""
交易所解析器

根据品种代码查找对应的交易所代码。
"""

from src.backtesting.config import EXCHANGE_MAP


class ExchangeResolver:
    """交易所解析器，根据品种代码查找对应的交易所。"""

    @staticmethod
    def resolve(product_code: str) -> str:
        """根据品种代码返回交易所代码。未知品种抛出 ValueError。"""
        exchange = EXCHANGE_MAP.get(product_code)
        if exchange is None:
            raise ValueError(f"未知品种代码: {product_code}")
        return exchange

    @staticmethod
    def is_czce(product_code: str) -> bool:
        """判断品种是否属于郑商所（影响合约代码格式）。"""
        return ExchangeResolver.resolve(product_code) == "CZCE"
