from datetime import date, timedelta
import calendar
import logging
from typing import List, Dict, Optional, Set
import re
from vnpy.trader.database import get_database
from vnpy.trader.constant import Interval, Exchange, Product, OptionType
from vnpy.trader.object import ContractData

# Try to import chinese_calendar, fallback if missing
try:
    import chinese_calendar
    HAS_CHINESE_CALENDAR = True
except ImportError:
    HAS_CHINESE_CALENDAR = False

logger = logging.getLogger(__name__)

# 手动指定到期日配置
# 格式: {"IF2501": date(2025, 1, 17), ...}
MANUAL_EXPIRY_CONFIG: Dict[str, date] = {}

# 交易所映射
EXCHANGE_MAP = {
    # SHFE
    "ag": "SHFE", "rb": "SHFE", "ao": "SHFE", "cu": "SHFE", "al": "SHFE",
    "zn": "SHFE", "au": "SHFE", "ru": "SHFE", "sn": "SHFE", "ni": "SHFE",
    "bu": "SHFE", "sp": "SHFE", "fu": "SHFE", "br": "SHFE", "pb": "SHFE",
    "ss": "SHFE", "hc": "SHFE", "wr": "SHFE",
    # CZCE
    "FG": "CZCE", "SA": "CZCE", "MA": "CZCE", "SR": "CZCE", "TA": "CZCE",
    "RM": "CZCE", "CF": "CZCE", "OI": "CZCE", "PK": "CZCE", "SF": "CZCE",
    "SM": "CZCE", "PX": "CZCE", "UR": "CZCE", "CJ": "CZCE", "AP": "CZCE",
    # DCE
    "m": "DCE", "i": "DCE", "p": "DCE", "y": "DCE", "c": "DCE", "jd": "DCE",
    "a": "DCE", "b": "DCE", "pp": "DCE", "l": "DCE", "v": "DCE", "eg": "DCE",
    "eb": "DCE", "pg": "DCE", "lh": "DCE", "si": "DCE",
    # CFFEX
    "IF": "CFFEX", "IH": "CFFEX", "IC": "CFFEX", "IM": "CFFEX",
    "IO": "CFFEX", "HO": "CFFEX", "MO": "CFFEX",
    "T": "CFFEX", "TF": "CFFEX", "TS": "CFFEX",
    # INE
    "sc": "INE", "lu": "INE", "nr": "INE", "bc": "INE"
}

# 股指期货与期权代码映射
FUTURE_OPTION_MAP = {
    "IF": "IO",
    "IM": "MO",
    "IH": "HO"
}

# 反向映射: 期权 -> 期货
OPTION_FUTURE_MAP = {v: k for k, v in FUTURE_OPTION_MAP.items()}

# 品种规格配置 (Size, PriceTick)
# 未配置的默认使用 (10, 1.0)
PRODUCT_SPECS = {
    # CFFEX - Stock Indices
    "IF": (300, 0.2),  # HS300 Future
    "IH": (300, 0.2),  # SSE50 Future
    "IC": (200, 0.2),  # CSI500 Future
    "IM": (200, 0.2),  # CSI1000 Future
    "IO": (100, 0.2),  # HS300 Option
    "HO": (100, 0.2),  # SSE50 Option
    "MO": (100, 0.2),  # CSI1000 Option
    
    # SHFE
    "rb": (10, 1.0),   # Rebar
    "hc": (10, 1.0),   # Hot Rolled Coil
    "ag": (15, 1.0),   # Silver
    "au": (1000, 0.02),# Gold
    
    # INE
    "sc": (1000, 0.1), # Crude Oil
    "lu": (10, 1.0),   # Low Sulfur Fuel Oil
    
    # DCE
    "m": (10, 1.0),    # Soybean Meal
    "i": (100, 0.5),   # Iron Ore
    
    # CZCE
    "SA": (20, 1.0),   # Soda Ash
    "MA": (10, 1.0),   # Methanol
}

class VtSymbolGenerator:
    """
    vt_symbol 生成器
    用于回测时生成标准的合约代码 (symbol.exchange)
    """

    @staticmethod
    def get_exchange(product_code: str) -> str:
        """获取品种对应的交易所代码"""
        return EXCHANGE_MAP.get(product_code, "SHFE")

    @staticmethod
    def get_trading_days(year: int, month: int) -> List[date]:
        """获取指定月份的交易日列表 (排除周末和法定节假日)"""
        num_days = calendar.monthrange(year, month)[1]
        days = []
        for day in range(1, num_days + 1):
            d = date(year, month, day)
            # 简单判断周末
            if d.weekday() >= 5:
                continue
            
            # 如果有 chinese_calendar，进一步判断节假日
            if HAS_CHINESE_CALENDAR:
                if chinese_calendar.is_holiday(d):
                    continue
            
            days.append(d)
        return days

    @classmethod
    def get_expiry_date(cls, product_code: str, contract_year: int, contract_month: int) -> date:  
        """
        计算合约到期日
        根据不同交易所规则推算
        """
        exchange = cls.get_exchange(product_code)
        
        # 1. 检查手动配置
        contract_suffix = f"{str(contract_year)[-2:]}{contract_month:02d}"
        symbol_key = f"{product_code}{contract_suffix}"
        
        if symbol_key in MANUAL_EXPIRY_CONFIG:
            return MANUAL_EXPIRY_CONFIG[symbol_key]

        # 2. 交易所规则
        # 计算交割月份的前一个月 (Pre-delivery month)
        if contract_month == 1:
            pre_year = contract_year - 1
            pre_month = 12
        else:
            pre_year = contract_year
            pre_month = contract_month - 1

        try:
            if exchange == "CFFEX":
                # 中金所: 第三个周五
                c_days = calendar.monthcalendar(contract_year, contract_month)
                fridays = []
                for week in c_days:
                    if week[4] != 0:
                        fridays.append(week[4])

                if len(fridays) >= 3:
                    day = fridays[2]
                    expiry = date(contract_year, contract_month, day)
                    # 顺延
                    if HAS_CHINESE_CALENDAR:
                        while chinese_calendar.is_holiday(expiry):
                            expiry += timedelta(days=1)
                    return expiry
                else:
                    return date(contract_year, contract_month, 15)

            elif exchange == "DCE":
                # 大商所: 交割月前一个月的第12个交易日
                trading_days = cls.get_trading_days(pre_year, pre_month)
                if len(trading_days) >= 12:
                    return trading_days[11]
                else:
                    return trading_days[-1] if trading_days else date(pre_year, pre_month, 28)

            elif exchange == "CZCE":
                # 郑商所: 交割月前一个月的第15个交易日 (此处规则有简化，实际较为复杂)
                trading_days = cls.get_trading_days(pre_year, pre_month)
                if len(trading_days) >= 15:
                    return trading_days[14]
                else:
                    return trading_days[-1] if trading_days else date(pre_year, pre_month, 28)

            elif exchange in ["SHFE", "INE"]:
                # 上期所/能源中心: 交割月前一个月的最后5个交易日 (倒数第5个)
                trading_days = cls.get_trading_days(pre_year, pre_month)
                if len(trading_days) >= 5:
                    return trading_days[-5]
                else:
                    return trading_days[0] if trading_days else date(pre_year, pre_month, 1)

        except Exception as e:
            logger.error(f"计算到期日失败 {product_code}: {e}")
            return date(contract_year, contract_month, 15)

        return date(contract_year, contract_month, 15)

    @classmethod
    def generate_vt_symbols_for_range(
        cls, 
        product_code: str, 
        start_year: int, 
        start_month: int,
        end_year: int,
        end_month: int
    ) -> List[str]:
        """
        生成指定时间范围内的所有合约代码
        
        Args:
            product_code: 品种代码 (e.g. "rb")
            start_year: 开始年份 (e.g. 2025)
            start_month: 开始月份 (e.g. 12)
            end_year: 结束年份 (e.g. 2026)
            end_month: 结束月份 (e.g. 2)
            
        Returns:
            List[str]: vt_symbol 列表 (e.g. ["rb2512.SHFE", "rb2601.SHFE", ...])
        """
        if "." in product_code:
            return [product_code]

        exchange_suffix = cls.get_exchange(product_code)
        symbols = []

        # 构造日期循环
        current_year = start_year
        current_month = start_month
        
        end_date_val = end_year * 100 + end_month
        
        while (current_year * 100 + current_month) <= end_date_val:
            
            # 生成合约代码
            # 郑商所是3位年份后缀? 通常是 3 位 (如 501 表示 2501)，但也支持 4 位
            # VnPy 通常标准化为 4 位后缀? 或者保持交易所习惯?
            # 根据 user 代码: f"{str(contract_year)[-2:]}{contract_month:02d}" -> 2 位年份
            # 大部分 VnPy 接口适配器 (如 CTP) 接受 4 位数字作为 InstrumentID (e.g. rb2501)
            # 郑商所 CTP 返回的 InstrumentID 是 3 位 (e.g. SA501)，但 vnpy_ctp 网关通常会处理
            # 这里如果不确定，先按主流 rb2501 格式生成 (2位年份 + 2位月份)
            
            # 特殊处理郑商所年份 (可选，视乎 vnpy 版本，标准 ctp gateway 通常兼容)
            # 用户代码用的是: str(contract_year)[-2:] -> 25
            
            short_year = str(current_year)[-2:]
            month_str = f"{current_month:02d}"
            
            # 郑商所特殊处理: 数据库中使用 3 位数字格式 (如 AP601)
            if exchange_suffix == "CZCE":
                # 取年份最后一位 (e.g. 2026 -> 6)
                year_char = str(current_year)[-1]
                symbol_code = f"{product_code}{year_char}{month_str}"
            else:
                # 其他交易所保持 4 位数字格式 (e.g. rb2601)
                symbol_code = f"{product_code}{short_year}{month_str}"
            
            symbol = f"{symbol_code}.{exchange_suffix}"
            symbols.append(symbol)
            
            # Next month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
                
        return symbols

    @classmethod
    def get_available_options_from_db(cls, underlying_vt_symbols: List[str]) -> List[str]:
        """
        从数据库中查找与指定期货合约相关联的期权合约
        
        Args:
            underlying_vt_symbols: 期货合约代码列表 (e.g. ["rb2505.SHFE"])
            
        Returns:
            List[str]: 数据库中存在的期权合约代码列表
        """
        if not underlying_vt_symbols:
            return []
            
        # 1. 解析期货代码
        # map: underlying_symbol -> (exchange, [prefixes])
        target_map = {}
        for vt_symbol in underlying_vt_symbols:
            try:
                symbol, exchange = vt_symbol.split(".")
                
                # 解析品种代码
                match = re.match(r"^([a-zA-Z]+)(\d+)", symbol)
                if match:
                    product_code = match.group(1).upper()
                    contract_suffix = match.group(2)
                    
                    prefixes = [symbol] # 默认包含自身，用于商品期权
                    
                    if product_code in FUTURE_OPTION_MAP:
                        option_product = FUTURE_OPTION_MAP[product_code]
                        option_prefix = f"{option_product}{contract_suffix}"
                        prefixes.append(option_prefix)
                        
                    target_map[symbol] = (exchange, prefixes)
                else:
                    target_map[symbol] = (exchange, [symbol])
            except ValueError:
                continue
                
        if not target_map:
            return []
            
        # 2. 获取数据库中所有 Bar 数据概览
        try:
            database = get_database()
            overviews = database.get_bar_overview()
        except Exception as e:
            logger.error(f"查询数据库失败: {e}")
            return []
            
        # 3. 筛选匹配的期权
        option_vt_symbols = []
        
        for overview in overviews:
            # 只关心 1分钟 K线 (通常回测用)
            if overview.interval != Interval.MINUTE:
                continue
                
            symbol = overview.symbol
            exchange = overview.exchange.value
            
            # 遍历所有目标期货
            for future_symbol, (future_exchange, prefixes) in target_map.items():
                if exchange != future_exchange:
                    continue
                
                # 检查是否匹配任一前缀
                matched_prefix = None
                for prefix in prefixes:
                    if symbol.startswith(prefix) and len(symbol) > len(prefix):
                        matched_prefix = prefix
                        break
                
                if not matched_prefix:
                    continue
                    
                # 进一步检查: 必须包含 C 或 P
                suffix = symbol[len(matched_prefix):]
                if "C" in suffix or "P" in suffix:
                     vt_symbol = f"{symbol}.{exchange}"
                     option_vt_symbols.append(vt_symbol)
                         
        logger.info(f"从数据库发现关联期权合约: {len(option_vt_symbols)} 个")
        return option_vt_symbols

    @classmethod
    def generate_recent_symbols(cls, product_code: str) -> List[str]:
        """
        生成近期合约代码
        范围: 2025.12 - (当前时间 + 1个月)
        """
        # 硬编码开始时间: 2025年12月
        start_year = 2025
        start_month = 12
        
        # 动态计算结束时间: 当前时间 + 1个月
        now = date.today()
        # 计算下个月
        if now.month == 12:
            end_year = now.year + 1
            end_month = 1
        else:
            end_year = now.year
            end_month = now.month + 1
            
        return cls.generate_vt_symbols_for_range(
            product_code=product_code,
            start_year=start_year,
            start_month=start_month,
            end_year=end_year,
            end_month=end_month
        )

    @staticmethod
    def generate_contract_data(vt_symbol: str, gateway_name: str = "BACKTESTING") -> Optional[ContractData]:
        """
        根据 vt_symbol 解析并生成 ContractData 对象 (用于回测)
        支持格式: 
        - 期货: rb2505.SHFE
        - 期权: rb2505C3000.SHFE, sc2602C540.INE, MO2601-C-6300.CFFEX
        """
        try:
            symbol, exchange_str = vt_symbol.split(".")
            exchange = Exchange(exchange_str)
        except ValueError:
            return None

        option_pattern = re.compile(r"^([a-zA-Z]+[0-9]+)(?:-)?([CPcp])(?:-)?([0-9]+(?:\.[0-9]+)?)$")
        match = option_pattern.match(symbol)
        
        if match:
            # 是期权
            underlying_symbol = match.group(1)
            type_char = match.group(2).upper()
            strike_str = match.group(3)
            
            option_type = OptionType.CALL if type_char == "C" else OptionType.PUT
            strike_price = float(strike_str)
            
            # 尝试推断 product
            # underlying_symbol e.g. rb2505 -> rb
            product_match = re.match(r"^([a-zA-Z]+)", underlying_symbol)
            product_name = product_match.group(1) if product_match else "Unknown"
            
            # 修正 option_underlying (例如 MO -> IM)
            # underlying_symbol 目前是 MO2602, 我们需要将其修正为 IM2602
            real_underlying_symbol = underlying_symbol
            if product_name in OPTION_FUTURE_MAP:
                future_product = OPTION_FUTURE_MAP[product_name]
                # 替换前缀 MO -> IM
                real_underlying_symbol = future_product + underlying_symbol[len(product_name):]

            # 获取规格
            size, pricetick = PRODUCT_SPECS.get(product_name, (10, 1.0))

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
                # option_expiry 需要日期，回测中如果不严格依赖 expiry_date 进行逻辑判断，可以暂空或给个假值
                # OptionSelectorService 会过滤 days_to_expiry，所以必须有 expiry
                # 我们可以复用 get_expiry_date，但需要解析年份月份
            )
            
            # 解析日期以计算 Expiry
            # underlying_symbol: rb2505 -> 25, 05
            date_match = re.search(r"(\d{2})(\d{2})$", underlying_symbol)
            if date_match:
                year_short = int(date_match.group(1))
                month = int(date_match.group(2))
                year = 2000 + year_short
                contract.option_expiry = VtSymbolGenerator.get_expiry_date(product_name, year, month)
            
            return contract
        else:
            # 是期货
            # underlying_symbol e.g. rb2505 -> rb
            product_match = re.match(r"^([a-zA-Z]+)", symbol)
            product_name = product_match.group(1) if product_match else "Unknown"
            
            # 获取规格
            size, pricetick = PRODUCT_SPECS.get(product_name, (10, 1.0))
            
            contract = ContractData(
                symbol=symbol,
                exchange=exchange,
                name=symbol,
                product=Product.FUTURES,
                size=size,
                pricetick=pricetick,
                min_volume=1,
                gateway_name=gateway_name
            )
            return contract
