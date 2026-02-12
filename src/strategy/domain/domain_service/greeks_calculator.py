"""
GreeksCalculator 领域服务

基于 Black-Scholes 模型计算期权 Greeks (Delta, Gamma, Theta, Vega)
以及隐含波动率反推。纯计算服务，无副作用。
"""
import math
from typing import Optional

from ..value_object.greeks import GreeksInput, GreeksResult, IVResult


def _norm_cdf(x: float) -> float:
    """标准正态分布累积分布函数"""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """标准正态分布概率密度函数"""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


class GreeksCalculator:
    """
    Black-Scholes Greeks 计算器

    职责: 计算单个期权的 Greeks 和隐含波动率。
    """

    def calculate_greeks(self, params: GreeksInput) -> GreeksResult:
        """
        计算 Greeks (Black-Scholes)

        Args:
            params: Greeks 计算输入参数

        Returns:
            GreeksResult 包含 delta, gamma, theta, vega
        """
        S = params.spot_price
        K = params.strike_price
        T = params.time_to_expiry
        r = params.risk_free_rate
        sigma = params.volatility
        opt = params.option_type

        # 参数校验
        if S <= 0 or K <= 0:
            return GreeksResult(
                success=False,
                error_message="spot_price 和 strike_price 必须大于 0"
            )
        if T < 0:
            return GreeksResult(
                success=False,
                error_message="time_to_expiry 不能为负数"
            )
        if sigma <= 0:
            return GreeksResult(
                success=False,
                error_message="volatility 必须大于 0"
            )

        # 到期时边界处理
        if T == 0:
            if opt == "call":
                delta = 1.0 if S > K else 0.0
            else:
                delta = -1.0 if S < K else 0.0
            return GreeksResult(delta=delta, gamma=0.0, theta=0.0, vega=0.0)

        try:
            sqrt_T = math.sqrt(T)
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
            d2 = d1 - sigma * sqrt_T

            pdf_d1 = _norm_pdf(d1)
            cdf_d1 = _norm_cdf(d1)
            cdf_d2 = _norm_cdf(d2)

            # Gamma 和 Vega 对 call/put 相同
            gamma = pdf_d1 / (S * sigma * sqrt_T)
            vega = S * pdf_d1 * sqrt_T / 100.0  # 除以100使单位为1%波动率

            if opt == "call":
                delta = cdf_d1
                theta = (
                    -S * pdf_d1 * sigma / (2.0 * sqrt_T)
                    - r * K * math.exp(-r * T) * cdf_d2
                ) / 365.0
            else:
                delta = cdf_d1 - 1.0
                theta = (
                    -S * pdf_d1 * sigma / (2.0 * sqrt_T)
                    + r * K * math.exp(-r * T) * _norm_cdf(-d2)
                ) / 365.0

            return GreeksResult(delta=delta, gamma=gamma, theta=theta, vega=vega)

        except (OverflowError, ValueError) as e:
            return GreeksResult(
                success=False,
                error_message=f"计算溢出: {e}"
            )

    def bs_price(self, params: GreeksInput) -> float:
        """
        Black-Scholes 理论价格

        Args:
            params: Greeks 计算输入参数

        Returns:
            期权理论价格
        """
        S = params.spot_price
        K = params.strike_price
        T = params.time_to_expiry
        r = params.risk_free_rate
        sigma = params.volatility
        opt = params.option_type

        if T == 0:
            if opt == "call":
                return max(S - K, 0.0)
            else:
                return max(K - S, 0.0)

        sqrt_T = math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        if opt == "call":
            return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        else:
            return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

    def calculate_implied_volatility(
        self,
        market_price: float,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        risk_free_rate: float,
        option_type: str,
        max_iterations: int = 100,
        tolerance: float = 0.01,
    ) -> IVResult:
        """
        牛顿法求解隐含波动率

        Args:
            market_price: 期权市场价格
            spot_price: 标的价格
            strike_price: 行权价
            time_to_expiry: 剩余到期时间 (年化)
            risk_free_rate: 无风险利率
            option_type: "call" | "put"
            max_iterations: 最大迭代次数
            tolerance: 收敛容差

        Returns:
            IVResult 包含隐含波动率和迭代信息
        """
        if market_price <= 0:
            return IVResult(
                success=False,
                error_message="市场价格必须大于 0"
            )

        # 检查市场价格是否低于内在价值
        if option_type == "call":
            intrinsic = max(spot_price - strike_price * math.exp(-risk_free_rate * time_to_expiry), 0.0)
        else:
            intrinsic = max(strike_price * math.exp(-risk_free_rate * time_to_expiry) - spot_price, 0.0)

        if market_price < intrinsic - tolerance:
            return IVResult(
                success=False,
                error_message="市场价格低于期权内在价值"
            )

        # 牛顿法迭代 + 二分法回退
        sigma = 0.5  # 初始猜测
        sigma_low = 0.001
        sigma_high = 10.0

        for i in range(max_iterations):
            params = GreeksInput(
                spot_price=spot_price,
                strike_price=strike_price,
                time_to_expiry=time_to_expiry,
                risk_free_rate=risk_free_rate,
                volatility=sigma,
                option_type=option_type,
            )
            price = self.bs_price(params)
            greeks = self.calculate_greeks(params)

            diff = price - market_price
            if abs(diff) < tolerance:
                return IVResult(
                    implied_volatility=sigma,
                    iterations=i + 1,
                )

            # 更新二分法边界
            if diff > 0:
                sigma_high = sigma
            else:
                sigma_low = sigma

            # 尝试牛顿法步进
            vega_raw = greeks.vega * 100.0 if greeks.success else 0.0
            if abs(vega_raw) > 1e-10:
                new_sigma = sigma - diff / vega_raw
                # 如果牛顿法步进在合理范围内则使用，否则回退到二分法
                if sigma_low < new_sigma < sigma_high:
                    sigma = new_sigma
                else:
                    sigma = (sigma_low + sigma_high) / 2.0
            else:
                # Vega 过小，回退到二分法
                sigma = (sigma_low + sigma_high) / 2.0

        return IVResult(
            success=False,
            error_message=f"在 {max_iterations} 次迭代内未收敛",
            iterations=max_iterations,
        )
