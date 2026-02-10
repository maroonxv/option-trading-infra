"""
Gateway Infrastructure Module

封装 vnpy MainEngine 的各种能力，为上层策略提供统一的接口。

Gateway 类列表:
- VnpyGatewayAdapter: 基类，提供 MainEngine 访问和日志功能
- VnpyAccountGateway: 账户/持仓查询
- VnpyMarketDataGateway: 行情订阅/合约查询/历史数据
- VnpyTradeExecutionGateway: 交易执行/开平转换
- VnpyOrderGateway: 订单/成交查询
- VnpyQuoteGateway: 报价/做市
- VnpyConnectionGateway: 连接管理
- VnpyEventGateway: 事件监听
"""

from .vnpy_gateway_adapter import VnpyGatewayAdapter
from .vnpy_account_gateway import VnpyAccountGateway
from .vnpy_market_data_gateway import VnpyMarketDataGateway
from .vnpy_trade_execution_gateway import VnpyTradeExecutionGateway
from .vnpy_order_gateway import VnpyOrderGateway
from .vnpy_quote_gateway import VnpyQuoteGateway
from .vnpy_connection_gateway import VnpyConnectionGateway
from .vnpy_event_gateway import VnpyEventGateway

__all__ = [
    "VnpyGatewayAdapter",
    "VnpyAccountGateway",
    "VnpyMarketDataGateway",
    "VnpyTradeExecutionGateway",
    "VnpyOrderGateway",
    "VnpyQuoteGateway",
    "VnpyConnectionGateway",
    "VnpyEventGateway",
]
