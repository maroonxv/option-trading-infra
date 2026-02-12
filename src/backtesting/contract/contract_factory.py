"""
合约工厂

根据 vt_symbol 解析并生成 ContractData 对象，支持期货和期权格式。
"""

import logging
import re
from typing import Optional, Tuple

from vnpy.trader.constant import Exchange, OptionType, Product
from vnpy.trader.object import ContractData

from src.backtesting.config import (
    DEFAULT_PRODUCT_SPEC,
    OPTION_FUTURE_MAP,
    PRODUCT_SPECS,
)
from src.backtesting.contract.expiry_calculator import ExpiryCalculator

logger = logging.getLogger(__name__)

# 期权 symbol 正则：匹配 underlying + C/P + strike，支持带连字符和不带连字符格式
_OPTION_PATTERN = re.compile(
    r"^([a-zA-Z]+[0-9]+)(?:-)?([CPcp])(?:-)?([0-9]+(?:\.[0-9]+)?)$"
)


class ContractFactory:
    """合约工厂，根据 vt_symbol 解析并构建 ContractData。"""

    @classmethod
    def create(
        cls, vt_symbol: str, gateway_name: str = "BACKTESTING"
    ) -> Optional[ContractData]:
        """解析 vt_symbol 并构建 ContractData。支持期货和期权格式。"""
        parsed = cls.parse_vt_symbol(vt_symbol)
        if parsed is None:
            return None

        symbol, exchange_str, product_code = parsed

        try:
            exchange = Exchange(exchange_str)
        except ValueError:
            logger.warning("无法解析交易所: %s", vt_symbol)
            return None

        match = _OPTION_PATTERN.match(symbol)
        if match:
            return cls._build_option(
                symbol, exchange, match, product_code, gateway_name
            )
        else:
            return cls._build_futures(
                symbol, exchange, product_code, gateway_name
            )

    @staticmethod
    def parse_vt_symbol(vt_symbol: str) -> Optional[Tuple[str, str, str]]:
        """
        解析 vt_symbol 为 (symbol, exchange_str, product_code)。

        无法解析时返回 None 并记录警告。
        """
        # 使用 rsplit 以最后一个 '.' 为分隔符，支持行权价含小数的情况
        # 例如 sc2602C540.5.INE → ("sc2602C540.5", "INE")
        parts = vt_symbol.rsplit(".", maxsplit=1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            logger.warning("无法解析 vt_symbol（缺少 '.'）: %s", vt_symbol)
            return None
        symbol, exchange_str = parts

        product_match = re.match(r"^([a-zA-Z]+)", symbol)
        if not product_match:
            logger.warning("无法提取品种代码: %s", vt_symbol)
            return None

        product_code = product_match.group(1)
        return symbol, exchange_str, product_code

    @classmethod
    def _build_futures(
        cls,
        symbol: str,
        exchange: Exchange,
        product_code: str,
        gateway_name: str,
    ) -> ContractData:
        """构建期货 ContractData。"""
        size, pricetick = PRODUCT_SPECS.get(product_code, DEFAULT_PRODUCT_SPEC)

        return ContractData(
            symbol=symbol,
            exchange=exchange,
            name=symbol,
            product=Product.FUTURES,
            size=size,
            pricetick=pricetick,
            min_volume=1,
            gateway_name=gateway_name,
        )

    @classmethod
    def _build_option(
        cls,
        symbol: str,
        exchange: Exchange,
        match: re.Match,
        product_code: str,
        gateway_name: str,
    ) -> ContractData:
        """构建期权 ContractData。"""
        underlying_symbol = match.group(1)
        type_char = match.group(2).upper()
        strike_str = match.group(3)

        option_type = OptionType.CALL if type_char == "C" else OptionType.PUT
        strike_price = float(strike_str)

        # 期权反向映射（如 MO → IM）
        real_underlying_symbol = underlying_symbol
        if product_code in OPTION_FUTURE_MAP:
            future_product = OPTION_FUTURE_MAP[product_code]
            real_underlying_symbol = (
                future_product + underlying_symbol[len(product_code):]
            )

        size, pricetick = PRODUCT_SPECS.get(product_code, DEFAULT_PRODUCT_SPEC)

        contract = ContractData(
            symbol=symbol,
            exchange=exchange,
            name=symbol,
            product=Product.OPTION,
            size=size,
            pricetick=pricetick,
            min_volume=1,
            gateway_name=gateway_name,
            option_strike=strike_price,
            option_underlying=real_underlying_symbol,
            option_type=option_type,
        )

        # 计算到期日
        date_match = re.search(r"(\d{2})(\d{2})$", underlying_symbol)
        if date_match:
            year_short = int(date_match.group(1))
            month = int(date_match.group(2))
            year = 2000 + year_short
            contract.option_expiry = ExpiryCalculator.calculate(
                product_code, year, month
            )

        return contract
