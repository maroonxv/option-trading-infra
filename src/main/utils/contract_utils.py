import re
from datetime import date
from typing import Optional


class ContractUtils:
    @staticmethod
    def get_expiry_from_symbol(symbol: str) -> Optional[date]:
        """
        从合约代码解析到期日
        示例: rb2501 -> 2025-01-15 (估算)
             SA501 -> 2025-01-15 (估算)
        """
        # 提取末尾数字
        match = re.search(r"(\d{3,4})$", symbol)
        if not match:
            return None
            
        digits = match.group(1)
        current_year = date.today().year
        
        if len(digits) == 4:
            # 如 2501 -> 2025年01月
            year_suffix = int(digits[:2])
            month = int(digits[2:])
            year = 2000 + year_suffix
        elif len(digits) == 3:
            # 郑商所常见格式，如 501 -> 2025年01月
            year_suffix = int(digits[0])
            month = int(digits[1:])
            
            # 推测年份：取当前年代 + 尾数
            year = (current_year // 10) * 10 + year_suffix
            
            # 如果推测出来的年份比当前年份小（且月份也小或者差距较大），
            # 可能是下一个年代的（例如在2029年看001，可能是2030）
            if year < current_year - 1:
                year += 10
        else:
            return None
            
        try:
            # 默认设为该月中旬，用于 7天规则判断
            # 实际上国内期货到期日常在月中
            return date(year, month, 15)
        except ValueError:
            return None
