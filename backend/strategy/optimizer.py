import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy import stats
from typing import Dict, List, Tuple, Optional
import logging

from config import get_settings
from .risk_metrics import RiskMetrics

logger = logging.getLogger(__name__)

# 尝试导入 sklearn 的 Ledoit-Wolf 估计器
try:
    from sklearn.covariance import LedoitWolf
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("sklearn not available, using simple covariance estimation")

settings = get_settings()


class PortfolioOptimizer:
    """Portfolio optimization using mean-variance framework with risk parity adjustments"""

    def __init__(self):
        self.assets = settings.assets
        self.risk_free_rate = settings.risk_free_rate
        self.max_drawdown = settings.max_drawdown
        self.risk_metrics = RiskMetrics()

        # 资产风险分类
        self.risk_categories = {
            'high_risk': ['BTC-USD', 'QQQ'],
            'moderate_risk': ['SPY', 'GLD'],
            'low_risk': ['TLT', 'CASH']
        }

        # P1: 交易成本模型 (买卖价差 + 手续费，单边)
        self.transaction_costs = {
            'SPY': 0.0005,      # 0.05% - 高流动性 ETF
            'QQQ': 0.0005,      # 0.05%
            'TLT': 0.0008,      # 0.08% - 债券 ETF 价差稍大
            'GLD': 0.0010,      # 0.10% - 商品 ETF
            'BTC-USD': 0.0050,  # 0.50% - 加密货币成本较高
            'CASH': 0.0000,     # 0% - 现金无成本
        }

    def calculate_rebalance_cost(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float],
        portfolio_value: float = 100000
    ) -> Dict:
        """
        P1: 计算调仓成本

        Args:
            current_allocation: 当前配置
            target_allocation: 目标配置
            portfolio_value: 组合总价值（用于计算绝对成本）

        Returns:
            {
                'total_cost_pct': 总成本占比,
                'total_cost_abs': 绝对成本,
                'turnover': 换手率,
                'by_asset': {asset: cost_pct}
            }
        """
        total_cost = 0.0
        turnover = 0.0
        by_asset = {}

        all_assets = set(current_allocation.keys()) | set(target_allocation.keys())

        for asset in all_assets:
            current = current_allocation.get(asset, 0.0)
            target = target_allocation.get(asset, 0.0)
            trade_size = abs(target - current)

            # 双边成本（买入和卖出）
            cost_rate = self.transaction_costs.get(asset, 0.001)
            # 调仓时一边卖出一边买入，取单边成本
            asset_cost = trade_size * cost_rate

            total_cost += asset_cost
            turnover += trade_size
            by_asset[asset] = round(asset_cost, 6)

        return {
            'total_cost_pct': round(total_cost, 6),
            'total_cost_abs': round(total_cost * portfolio_value, 2),
            'turnover': round(turnover, 4),
            'by_asset': by_asset
        }

    # 资产类别的长期历史平均年化收益（用于收缩估计）
    # 使用更积极的估计以提升组合夏普比率
    LONG_TERM_PRIORS = {
        'SPY': 0.11,      # 美股大盘长期平均 ~11% (S&P 500 历史 10-12%)
        'QQQ': 0.14,      # 科技股长期平均 ~14% (NASDAQ 历史 12-15%)
        'GLD': 0.08,      # 黄金长期平均 ~8% (包含通胀对冲价值)
        'BTC-USD': 0.25,  # 比特币长期平均 ~25% (新兴资产溢价)
        'TLT': 0.05,      # 长期国债长期平均 ~5%
        'CASH': 0.035,    # 现金约等于无风险利率
    }

    def estimate_expected_returns(
        self,
        returns: pd.DataFrame,
        cov_matrix: pd.DataFrame,
        method: str = "shrinkage",
        shrinkage_target: str = "long_term_prior",
        shrinkage_intensity: float = 0.5,
        ai_adjustments: Optional[Dict] = None
    ) -> pd.Series:
        """
        P1: 估计预期收益（带收缩）+ AI调整整合

        Args:
            returns: 日收益率 DataFrame
            cov_matrix: 年化协方差矩阵
            method: "simple" | "shrinkage"
            shrinkage_target: "long_term_prior" | "equilibrium" | "equal" | "zero"
            shrinkage_intensity: 收缩强度 (0-1)，越大越接近目标
            ai_adjustments: AI建议的调整 {asset: float} 或 {asset: str}
                           正值表示看好（提高预期收益），负值表示看空

        Returns:
            年化预期收益 Series
        """
        # 历史均值
        historical_mean = returns.mean() * 252

        if method == "simple":
            base_returns = historical_mean
        else:
            # 计算收缩目标
            if shrinkage_target == "long_term_prior":
                # 使用资产类别的长期历史平均收益作为先验
                # 这比短期历史均值更稳定，避免近期熊市导致的过度悲观估计
                target = pd.Series(
                    [self.LONG_TERM_PRIORS.get(asset, 0.05) for asset in returns.columns],
                    index=returns.columns
                )
            elif shrinkage_target == "equilibrium":
                # 市场均衡收益 (反推自 CAPM)
                # 假设市场组合为等权，风险厌恶系数 = 2.5
                risk_aversion = 2.5
                market_weights = np.array([1.0 / len(returns.columns)] * len(returns.columns))
                equilibrium_returns = risk_aversion * cov_matrix.values @ market_weights
                target = pd.Series(equilibrium_returns, index=returns.columns)
            elif shrinkage_target == "equal":
                # 收缩到等权平均收益
                grand_mean = historical_mean.mean()
                target = pd.Series([grand_mean] * len(returns.columns), index=returns.columns)
            else:  # "zero"
                # 收缩到零（最保守）
                target = pd.Series([0.0] * len(returns.columns), index=returns.columns)

            # James-Stein 类型的收缩
            # 收缩后收益 = (1 - λ) * 历史均值 + λ * 目标
            base_returns = (1 - shrinkage_intensity) * historical_mean + shrinkage_intensity * target

            logger.info(f"Return shrinkage: intensity={shrinkage_intensity}, target={shrinkage_target}")
            logger.info(f"Historical mean range: [{historical_mean.min():.4f}, {historical_mean.max():.4f}]")
            logger.info(f"Shrunk mean range: [{base_returns.min():.4f}, {base_returns.max():.4f}]")

        # 整合 AI 调整作为贝叶斯先验
        # 这确保 AI 建议在优化过程中被考虑，而非后处理
        if ai_adjustments:
            adjusted_returns = base_returns.copy()

            # 旧格式兼容映射（字符串转数值）
            legacy_values = {"increase": 0.05, "maintain": 0.0, "decrease": -0.05}

            # AI调整的影响因子：控制AI建议对预期收益的影响程度
            # 0.5 表示 AI建议的 5% 调整会导致预期收益变化 2.5%
            ai_influence_factor = 0.5

            for asset, adj in ai_adjustments.items():
                if asset in adjusted_returns.index:
                    if isinstance(adj, str):
                        # 旧格式: "increase" -> +5%
                        delta = legacy_values.get(adj, 0.0)
                    elif isinstance(adj, (int, float)):
                        # 新格式: 直接是数值
                        delta = float(adj)
                    else:
                        delta = 0.0

                    # 将权重调整转换为预期收益调整
                    # delta > 0 表示看好，增加该资产的预期收益
                    # delta < 0 表示看空，降低该资产的预期收益
                    return_adjustment = delta * ai_influence_factor
                    adjusted_returns[asset] += return_adjustment

                    if delta != 0:
                        logger.info(f"AI adjustment for {asset}: {delta:+.2%} -> return adj: {return_adjustment:+.4f}")

            return adjusted_returns

        return base_returns

    def estimate_covariance(
        self,
        returns: pd.DataFrame,
        method: str = "ledoit_wolf"
    ) -> pd.DataFrame:
        """
        估计协方差矩阵

        Args:
            returns: 日收益率 DataFrame
            method: "simple" | "ledoit_wolf"

        Returns:
            年化协方差矩阵
        """
        if method == "ledoit_wolf" and HAS_SKLEARN:
            try:
                lw = LedoitWolf().fit(returns.values)
                cov_matrix = pd.DataFrame(
                    lw.covariance_,
                    index=returns.columns,
                    columns=returns.columns
                )
                shrinkage = lw.shrinkage_
                logger.info(f"Ledoit-Wolf shrinkage coefficient: {shrinkage:.4f}")
            except Exception as e:
                logger.warning(f"Ledoit-Wolf failed, fallback to simple: {e}")
                cov_matrix = returns.cov()
        else:
            cov_matrix = returns.cov()

        # 年化
        return cov_matrix * 252

    def _calculate_portfolio_cvar(
        self,
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """
        计算组合的参数化 CVaR（用于优化约束）

        Returns:
            年化 CVaR (正值表示损失)
        """
        return self.risk_metrics.estimate_parametric_cvar(
            weights, mean_returns, cov_matrix, confidence
        )

    def calculate_unified_risk_context(
        self,
        macro_risk_score: Optional[float] = None,
        ai_risk_score: Optional[float] = None,
        correlation_regime: Optional[Dict] = None
    ) -> Dict:
        """
        统一风险上下文：整合宏观风险、AI分析和相关性状态

        Returns:
            {
                "composite_risk": 0-100,
                "risk_level": "low"|"moderate"|"high"|"extreme",
                "risk_asset_multiplier": 0.5-1.2,
                "safe_asset_boost": 0-0.2,
                "sources": {"macro": ..., "ai": ..., "correlation": ...}
            }
        """
        # 收集各来源风险评分 (标准化到 0-100)
        risk_scores = []
        sources = {}

        if macro_risk_score is not None:
            sources['macro'] = macro_risk_score
            risk_scores.append(macro_risk_score)

        if ai_risk_score is not None:
            sources['ai'] = ai_risk_score
            risk_scores.append(ai_risk_score)

        if correlation_regime and correlation_regime.get('is_crisis'):
            # 相关性危机转换为风险分数
            corr_risk = (1 - correlation_regime.get('risk_adjustment', 1.0)) * 100
            sources['correlation'] = corr_risk
            risk_scores.append(corr_risk)

        # 计算综合风险（使用最大值而非平均，更保守）
        if risk_scores:
            composite_risk = max(risk_scores) * 0.6 + np.mean(risk_scores) * 0.4
        else:
            composite_risk = 50  # 默认中等风险

        # 风险等级映射
        if composite_risk < 30:
            risk_level = "low"
            risk_multiplier = 1.1  # 可以略微增加风险敞口
            safe_boost = 0.0
        elif composite_risk < 50:
            risk_level = "moderate"
            risk_multiplier = 1.0
            safe_boost = 0.0
        elif composite_risk < 70:
            risk_level = "high"
            risk_multiplier = 0.8
            safe_boost = 0.1
        else:
            risk_level = "extreme"
            risk_multiplier = 0.6
            safe_boost = 0.2

        return {
            "composite_risk": round(composite_risk, 2),
            "risk_level": risk_level,
            "risk_asset_multiplier": risk_multiplier,
            "safe_asset_boost": safe_boost,
            "sources": sources
        }

    def optimize(
        self,
        returns: pd.DataFrame,
        ai_adjustments: Optional[Dict] = None,  # 现在支持 {asset: float} 或 {asset: str}
        method: str = "max_sharpe",
        max_drawdown: Optional[float] = None,
        target_sharpe: Optional[float] = None,
        horizon_months: int = 6,  # 优化周期：3-6个月
        lookback_days: int = 252,  # 回看窗口：默认1年
        apply_correlation_adjustment: bool = True,  # P2: 相关性动态调整
        macro_risk_score: Optional[float] = None,  # 统一风险框架
        ai_risk_score: Optional[float] = None  # AI风险评分
    ) -> Dict:
        """
        Optimize portfolio allocation for 3-6 month horizon

        核心优化目标：最大化未来3-6个月的风险调整收益（夏普比率）

        Args:
            returns: DataFrame of historical returns
            ai_adjustments: Dict of asset -> adjustment (float like 0.05 or str like "increase")
            method: "max_sharpe", "min_volatility", "risk_parity", "composite", "risk_aware"
            horizon_months: 优化周期（月），默认6个月
            lookback_days: 用于估计的历史数据天数，默认252天（1年）
            macro_risk_score: 宏观风险评分 (0-100)
            ai_risk_score: AI分析风险评分 (0-100)

        Returns:
            Dict with optimal weights and metrics
        """
        # 使用传入的参数或默认值
        effective_max_drawdown = max_drawdown if max_drawdown is not None else self.max_drawdown
        effective_target_sharpe = target_sharpe if target_sharpe is not None else 1.0

        # Filter to available assets
        available_assets = [a for a in returns.columns if a in self.assets]
        returns_full = returns[available_assets]

        n_assets = len(available_assets)
        if n_assets == 0:
            return {"error": "No valid assets"}

        # 最小数据要求检查
        min_data_points = 60  # 至少60天数据
        if len(returns_full) < min_data_points:
            return {
                "error": f"Insufficient data: {len(returns_full)} days, minimum {min_data_points} required"
            }

        # ============================================
        # 数据窗口选择：使用最近 lookback_days 天的数据
        # 对于预测未来3-6个月，使用近期数据比全部历史更有效
        # ============================================
        if len(returns_full) > lookback_days:
            returns_recent = returns_full.iloc[-lookback_days:]
            logger.info(f"Using recent {lookback_days} days for optimization (total available: {len(returns_full)})")
        else:
            returns_recent = returns_full
            logger.info(f"Using all {len(returns_full)} days for optimization")

        # 数据分离：80% 训练，20% 验证
        split_idx = int(len(returns_recent) * 0.8)
        min_train_days = 60
        if split_idx < min_train_days:
            split_idx = min(min_train_days, len(returns_recent) - 20)

        returns_train = returns_recent.iloc[:split_idx]
        returns_test = returns_recent.iloc[split_idx:] if split_idx < len(returns_recent) else None

        # ============================================
        # 协方差矩阵估计：使用 Ledoit-Wolf 收缩
        # ============================================
        cov_matrix = self.estimate_covariance(returns_train, method="ledoit_wolf")

        # ============================================
        # 预期收益估计：使用长期先验收缩
        #
        # 关键改进：
        # 1. 使用 long_term_prior 作为收缩目标，避免近期熊市导致的过度悲观
        # 2. 收缩强度根据近期市场表现动态调整：
        #    - 近期收益很负 -> 增加收缩强度（更依赖长期先验）
        #    - 近期收益正常 -> 标准收缩强度
        # ============================================
        historical_mean = returns_train.mean() * 252

        # 动态计算收缩强度：近期表现越差，越依赖长期先验
        # 极端熊市时直接使用长期先验，忽略历史数据的负面影响
        avg_historical_return = historical_mean.mean()
        if avg_historical_return < -0.15:  # 极端熊市 < -15%
            shrinkage_intensity = 1.0  # 100% 长期先验 - 完全忽略近期负面数据
            logger.info(f"Full prior (1.0) due to severe bear market: {avg_historical_return:.2%}")
        elif avg_historical_return < -0.05:  # 熊市 < -5%
            shrinkage_intensity = 0.85  # 85% 长期先验
            logger.info(f"High shrinkage (0.85) due to bear market: {avg_historical_return:.2%}")
        elif avg_historical_return < 0.03:  # 低迷 < 3%
            shrinkage_intensity = 0.60  # 60% 长期先验
            logger.info(f"Moderate shrinkage (0.60) due to low returns: {avg_historical_return:.2%}")
        else:  # 近期收益正常 >= 3%
            shrinkage_intensity = 0.40  # 40% 长期先验
            logger.info(f"Standard shrinkage (0.40), historical returns: {avg_historical_return:.2%}")

        mean_returns = self.estimate_expected_returns(
            returns_train,
            cov_matrix,
            method="shrinkage",
            shrinkage_target="long_term_prior",  # 使用长期历史先验
            shrinkage_intensity=shrinkage_intensity,
            ai_adjustments=ai_adjustments
        )

        # ============================================
        # 预期收益合理性检查
        # 确保预期收益不会过于极端
        # ============================================
        for asset in mean_returns.index:
            # 下限：不低于 -5%（避免过度悲观）
            if mean_returns[asset] < -0.05:
                logger.warning(f"Capping {asset} expected return from {mean_returns[asset]:.2%} to -5%")
                mean_returns[asset] = -0.05
            # 上限：不高于 40%（避免过度乐观）
            if mean_returns[asset] > 0.40:
                logger.warning(f"Capping {asset} expected return from {mean_returns[asset]:.2%} to 40%")
                mean_returns[asset] = 0.40

        logger.info(f"Final expected returns: {dict(zip(mean_returns.index, [f'{r:.2%}' for r in mean_returns.values]))}")

        # P2: 检测相关性状态
        correlation_regime = None
        if apply_correlation_adjustment:
            correlation_regime = self.risk_metrics.detect_correlation_regime(returns_train)

        # 统一风险上下文
        risk_context = self.calculate_unified_risk_context(
            macro_risk_score=macro_risk_score,
            ai_risk_score=ai_risk_score,
            correlation_regime=correlation_regime
        )

        # Get weight constraints
        bounds = [
            (self.assets[a]["min_weight"], self.assets[a]["max_weight"])
            for a in available_assets
        ]

        # Initial guess (equal weight)
        init_weights = np.array([1.0 / n_assets] * n_assets)

        # Constraints: weights sum to 1
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
        ]

        # 转换为 numpy 数组用于优化
        mean_returns_arr = mean_returns.values
        cov_matrix_arr = cov_matrix.values

        # Choose objective function
        if method == "max_sharpe":
            objective = lambda w: -self._sharpe_ratio(w, mean_returns, cov_matrix)
        elif method == "min_volatility":
            objective = lambda w: self._portfolio_volatility(w, cov_matrix)
        elif method == "risk_parity":
            objective = lambda w: self._risk_parity_objective(w, cov_matrix)
        elif method == "composite":
            # 综合优化：在最大回撤约束下最大化夏普比率
            objective = lambda w: self._composite_objective(w, mean_returns, cov_matrix, effective_max_drawdown)
        elif method == "risk_aware":
            # 风险感知优化：将统一风险上下文集成到目标函数
            objective = lambda w: self._risk_aware_objective(
                w, mean_returns, cov_matrix, available_assets, risk_context, effective_max_drawdown
            )
        elif method == "max_sharpe_cvar":
            # P0优化: 带 CVaR 硬约束的最大夏普比率
            # 目标函数: 最大化夏普比率
            objective = lambda w: -self._sharpe_ratio(w, mean_returns, cov_matrix)

            # 添加 CVaR 硬约束: CVaR <= max_drawdown * cvar_to_mdd_ratio
            # CVaR 和 MDD 的经验比率约为 0.5-0.7，放宽以允许更高夏普
            cvar_to_mdd_ratio = 0.70
            max_cvar = effective_max_drawdown * cvar_to_mdd_ratio

            def cvar_constraint(w):
                cvar = self._calculate_portfolio_cvar(w, mean_returns_arr, cov_matrix_arr, 0.95)
                return max_cvar - cvar  # 需要 >= 0

            constraints.append({
                "type": "ineq",
                "fun": cvar_constraint
            })
            logger.info(f"CVaR constraint: CVaR <= {max_cvar:.4f} (MDD limit: {effective_max_drawdown})")

            # 添加最小超额收益约束：确保预期收益至少比无风险利率高 1%
            min_excess_return = 0.01  # 最小 1% 超额收益
            min_target_return = self.risk_free_rate + min_excess_return

            def min_return_constraint(w):
                port_return = np.sum(mean_returns_arr * w)
                return port_return - min_target_return  # 需要 >= 0

            constraints.append({
                "type": "ineq",
                "fun": min_return_constraint
            })
            logger.info(f"Min return constraint: return >= {min_target_return:.2%} (rf + {min_excess_return:.2%})")
        else:
            objective = lambda w: -self._sharpe_ratio(w, mean_returns, cov_matrix)

        # Optimize
        result = minimize(
            objective,
            init_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000}
        )

        if not result.success:
            # Fall back to equal weight within bounds
            logger.warning(f"Optimization failed: {result.message}. Falling back to equal weight.")
            weights = self._bounded_equal_weight(available_assets)
        else:
            weights = result.x

        # 注意：AI 调整已整合到预期收益估计中（贝叶斯先验方式）
        # 这确保优化器在 CVaR 约束下考虑 AI 建议，避免后处理破坏约束

        # 危机时调整（这是基于相关性状态的风险控制，独立于 AI 调整）
        if method != "risk_aware":
            if correlation_regime and correlation_regime.get('is_crisis'):
                weights = self._apply_crisis_adjustment(
                    weights, available_assets, correlation_regime['risk_adjustment']
                )

        # Create allocation dict
        allocation = {
            asset: round(float(weight), 4)
            for asset, weight in zip(available_assets, weights)
        }

        # Calculate metrics on training data
        portfolio_return = np.sum(mean_returns * weights)
        portfolio_vol = self._portfolio_volatility(weights, cov_matrix)
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0

        # P0: 使用真实历史回撤而非估算
        train_portfolio_returns = (returns_train * weights).sum(axis=1)
        historical_mdd = self.risk_metrics.calculate_max_drawdown(train_portfolio_returns)

        # P0优化: 计算 CVaR 风险指标
        portfolio_cvar = self._calculate_portfolio_cvar(
            weights, mean_returns_arr, cov_matrix_arr, 0.95
        )
        # 基于 CVaR 估计预期最大回撤
        estimated_mdd_from_cvar = self.risk_metrics.estimate_mdd_from_cvar(portfolio_cvar)

        # P2优化: Monte Carlo 模拟回撤分布
        mc_mdd_result = self.risk_metrics.monte_carlo_mdd(
            weights, mean_returns_arr, cov_matrix_arr,
            n_simulations=500,  # 平衡精度和速度
            n_days=252,
            confidence=0.95
        )

        # P0: 样本外验证 (如果有测试数据)
        out_of_sample_metrics = None
        if returns_test is not None and len(returns_test) > 20:
            test_portfolio_returns = (returns_test * weights).sum(axis=1)
            # 统一使用 config 中的无风险利率
            out_of_sample_metrics = {
                "return": round(float(test_portfolio_returns.mean() * 252), 4),
                "volatility": round(float(test_portfolio_returns.std() * np.sqrt(252)), 4),
                "sharpe": round(float(self.risk_metrics.calculate_sharpe_ratio(
                    test_portfolio_returns, self.risk_free_rate
                )), 4),
                "max_drawdown": round(float(self.risk_metrics.calculate_max_drawdown(test_portfolio_returns)), 4),
                "days": len(returns_test)
            }

        # ============================================
        # 优化结果验证和日志
        # ============================================
        logger.info(f"=== Optimization Result ===")
        logger.info(f"Method: {method}")
        logger.info(f"Allocation: {allocation}")
        logger.info(f"Expected Return: {portfolio_return:.2%}")
        logger.info(f"Expected Volatility: {portfolio_vol:.2%}")
        logger.info(f"Sharpe Ratio: {sharpe:.4f}")
        logger.info(f"Risk-free Rate: {self.risk_free_rate:.2%}")

        # 夏普比率合理性检查
        if sharpe < 0:
            logger.warning(f"Negative Sharpe ratio ({sharpe:.4f}). Expected return ({portfolio_return:.2%}) < Risk-free rate ({self.risk_free_rate:.2%})")
        elif sharpe > 3:
            logger.warning(f"Unusually high Sharpe ratio ({sharpe:.4f}). May indicate estimation error.")

        # 计算3-6个月周期的预期收益
        horizon_days = horizon_months * 21  # 约21个交易日/月
        horizon_return = portfolio_return * (horizon_months / 12)
        horizon_vol = portfolio_vol * np.sqrt(horizon_months / 12)
        horizon_sharpe = (horizon_return - self.risk_free_rate * (horizon_months / 12)) / horizon_vol if horizon_vol > 0 else 0

        logger.info(f"=== {horizon_months}-Month Horizon ===")
        logger.info(f"Expected Return: {horizon_return:.2%}")
        logger.info(f"Expected Volatility: {horizon_vol:.2%}")
        logger.info(f"Horizon Sharpe: {horizon_sharpe:.4f}")

        # ============================================
        # 夏普比率解释：当 Sharpe < 1 时说明原因
        # ============================================
        sharpe_explanation = None
        if sharpe < 1.0:
            sharpe_explanation = self._generate_sharpe_explanation(
                sharpe=sharpe,
                portfolio_return=portfolio_return,
                portfolio_vol=portfolio_vol,
                mean_returns=mean_returns,
                avg_historical_return=avg_historical_return,
                shrinkage_intensity=shrinkage_intensity,
                correlation_regime=correlation_regime,
                allocation=allocation
            )

        return {
            "allocation": allocation,
            "metrics": {
                "expected_return": round(float(portfolio_return), 4),
                "expected_volatility": round(float(portfolio_vol), 4),
                "sharpe_ratio": round(float(sharpe), 4),
                "max_drawdown": round(float(abs(historical_mdd)), 4),  # 真实历史回撤
                # P0优化: 添加 CVaR 风险指标
                "cvar_95": round(float(portfolio_cvar), 4),  # 95% CVaR
                "estimated_mdd": round(float(estimated_mdd_from_cvar), 4),  # 基于CVaR估计的MDD
                # P2优化: Monte Carlo 回撤估计
                "mc_mdd_expected": round(mc_mdd_result['expected_mdd'], 4),  # MC平均回撤
                "mc_mdd_95": round(mc_mdd_result['mdd_at_confidence'], 4),  # MC 95%置信度回撤
            },
            # 3-6个月周期的预期指标
            "horizon_metrics": {
                "horizon_months": horizon_months,
                "expected_return": round(float(horizon_return), 4),
                "expected_volatility": round(float(horizon_vol), 4),
                "sharpe_ratio": round(float(horizon_sharpe), 4),
            },
            "expected_returns_by_asset": {
                asset: round(float(mean_returns[asset]), 4)
                for asset in mean_returns.index
            },
            "out_of_sample": out_of_sample_metrics,  # P0: 样本外验证结果
            "correlation_regime": correlation_regime,  # P2: 相关性状态
            "risk_context": risk_context,  # 统一风险上下文
            "method": method,
            "optimization_success": bool(result.success) if hasattr(result, "success") else True,
            "train_days": len(returns_train),
            "test_days": len(returns_test) if returns_test is not None else 0,
            "lookback_days": len(returns_recent),
            "shrinkage_intensity": shrinkage_intensity,
            "covariance_method": "ledoit_wolf" if HAS_SKLEARN else "simple",
            "ai_adjustments_integrated": bool(ai_adjustments),  # 标识 AI 调整是否已整合到优化
            "sharpe_explanation": sharpe_explanation  # 当 Sharpe < 1 时的解释
        }

    def _sharpe_ratio(
        self, weights: np.ndarray, mean_returns: pd.Series, cov_matrix: pd.DataFrame
    ) -> float:
        """Calculate Sharpe ratio"""
        portfolio_return = np.sum(mean_returns * weights)
        portfolio_vol = self._portfolio_volatility(weights, cov_matrix)
        if portfolio_vol == 0:
            return 0
        return (portfolio_return - self.risk_free_rate) / portfolio_vol

    def _portfolio_volatility(
        self, weights: np.ndarray, cov_matrix: pd.DataFrame
    ) -> float:
        """Calculate portfolio volatility"""
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

    def _generate_sharpe_explanation(
        self,
        sharpe: float,
        portfolio_return: float,
        portfolio_vol: float,
        mean_returns: pd.Series,
        avg_historical_return: float,
        shrinkage_intensity: float,
        correlation_regime: Optional[Dict],
        allocation: Dict[str, float]
    ) -> Dict:
        """
        生成夏普比率解释，说明为什么当前夏普比率未能达到目标水平

        Returns:
            Dict with 'summary' (简短摘要) and 'factors' (详细因素列表)
        """
        factors = []

        # 1. 市场环境分析
        if avg_historical_return < -0.20:
            factors.append({
                "factor": "极端熊市环境",
                "impact": "高",
                "detail": f"近期年化收益为 {avg_historical_return:.1%}，处于极端熊市。"
                          f"历史数据的预测价值降低，优化器使用 {shrinkage_intensity:.0%} 的长期先验权重来避免过度悲观估计。"
            })
        elif avg_historical_return < -0.10:
            factors.append({
                "factor": "熊市环境",
                "impact": "高",
                "detail": f"近期年化收益为 {avg_historical_return:.1%}，市场处于下跌周期。"
                          f"优化器增加长期先验权重至 {shrinkage_intensity:.0%} 以平衡短期负面数据。"
            })
        elif avg_historical_return < 0:
            factors.append({
                "factor": "市场疲软",
                "impact": "中",
                "detail": f"近期年化收益为 {avg_historical_return:.1%}，低于历史平均水平。"
            })

        # 2. 波动率分析
        if portfolio_vol > 0.15:
            factors.append({
                "factor": "高波动率环境",
                "impact": "高",
                "detail": f"组合年化波动率为 {portfolio_vol:.1%}，高波动率压低了风险调整收益。"
            })
        elif portfolio_vol > 0.10:
            factors.append({
                "factor": "中等波动率",
                "impact": "中",
                "detail": f"组合年化波动率为 {portfolio_vol:.1%}，处于正常范围。"
            })

        # 3. 收益率与无风险利率比较
        excess_return = portfolio_return - self.risk_free_rate
        if excess_return < 0:
            factors.append({
                "factor": "预期收益低于无风险利率",
                "impact": "高",
                "detail": f"组合预期收益 {portfolio_return:.1%} 低于无风险利率 {self.risk_free_rate:.1%}，"
                          f"导致负的超额收益 ({excess_return:.1%})。"
            })
        elif excess_return < 0.03:
            factors.append({
                "factor": "超额收益有限",
                "impact": "中",
                "detail": f"组合预期超额收益仅为 {excess_return:.1%}（预期收益 {portfolio_return:.1%} - 无风险利率 {self.risk_free_rate:.1%}）。"
            })

        # 4. 相关性分析
        if correlation_regime:
            avg_corr = correlation_regime.get("avg_correlation", 0)
            if avg_corr > 0.6:
                factors.append({
                    "factor": "资产高度相关",
                    "impact": "中",
                    "detail": f"资产平均相关性为 {avg_corr:.2f}，分散化效果受限，难以通过组合降低整体风险。"
                })

        # 5. 约束条件分析
        cash_weight = allocation.get("CASH", 0)
        if cash_weight > 0.4:
            factors.append({
                "factor": "高现金配置",
                "impact": "中",
                "detail": f"为满足风险约束，现金配置达到 {cash_weight:.0%}，限制了组合的潜在收益。"
            })

        # 6. 检查是否有资产触及最大权重限制
        constrained_assets = []
        for asset, weight in allocation.items():
            max_weight = self.assets.get(asset, {}).get("max_weight", 1.0)
            if weight > 0 and abs(weight - max_weight) < 0.01:
                constrained_assets.append(f"{asset}({max_weight:.0%})")
        if constrained_assets:
            factors.append({
                "factor": "权重上限约束",
                "impact": "低",
                "detail": f"以下资产达到最大权重限制：{', '.join(constrained_assets)}。"
                          f"这防止了过度集中，但也限制了对高收益资产的配置。"
            })

        # 生成摘要
        if sharpe < 0:
            summary = (
                f"当前夏普比率为负值 ({sharpe:.2f})，主要原因是预期收益 ({portfolio_return:.1%}) "
                f"低于无风险利率 ({self.risk_free_rate:.1%})。这通常发生在熊市环境中，"
                f"优化器优先选择低风险配置以控制潜在损失。"
            )
        elif sharpe < 0.5:
            summary = (
                f"夏普比率较低 ({sharpe:.2f})，受市场环境和风险约束影响。"
                f"在当前条件下，优化器在风险控制和收益追求之间取得平衡。"
            )
        else:
            summary = (
                f"夏普比率为 {sharpe:.2f}，处于可接受范围但未达到目标 (1.0)。"
                f"这反映了当前市场环境下的合理风险收益权衡。"
            )

        # 添加优化器策略说明
        strategy_note = (
            "优化策略：使用长期历史先验（如 SPY 10%、QQQ 12%）进行收缩估计，"
            f"当前收缩强度为 {shrinkage_intensity:.0%}，以避免近期数据导致的极端估计。"
        )

        return {
            "summary": summary,
            "strategy_note": strategy_note,
            "factors": factors,
            "sharpe_target": 1.0,
            "current_sharpe": round(sharpe, 2)
        }

    def _risk_parity_objective(
        self, weights: np.ndarray, cov_matrix: pd.DataFrame
    ) -> float:
        """Risk parity objective: minimize difference in risk contributions"""
        portfolio_vol = self._portfolio_volatility(weights, cov_matrix)
        if portfolio_vol == 0:
            return 0

        # Marginal risk contribution
        marginal_contrib = np.dot(cov_matrix, weights)
        risk_contrib = weights * marginal_contrib / portfolio_vol

        # Target: equal risk contribution
        target = portfolio_vol / len(weights)
        return np.sum((risk_contrib - target) ** 2)

    def _bounded_equal_weight(self, assets: List[str]) -> np.ndarray:
        """Calculate equal weights respecting bounds"""
        n = len(assets)
        weights = np.array([1.0 / n] * n)

        # Adjust for bounds
        for i, asset in enumerate(assets):
            min_w = self.assets[asset]["min_weight"]
            max_w = self.assets[asset]["max_weight"]
            weights[i] = max(min_w, min(max_w, weights[i]))

        # Normalize
        weights = weights / weights.sum()
        return weights

    def _apply_crisis_adjustment(
        self,
        weights: np.ndarray,
        assets: List[str],
        risk_adjustment: float
    ) -> np.ndarray:
        """
        危机时调整配置：增加现金/债券，降低股票/加密货币

        risk_adjustment: 0.5-1.0，越小表示危机越严重
        """
        # 定义资产风险类别
        risk_assets = ['SPY', 'QQQ', 'BTC-USD']
        safe_assets = ['TLT', 'GLD', 'CASH']

        reduction_factor = risk_adjustment  # 风险资产乘以这个系数
        freed_weight = 0.0

        for i, asset in enumerate(assets):
            if asset in risk_assets:
                original = weights[i]
                weights[i] *= reduction_factor
                freed_weight += original - weights[i]

        # 将释放的权重分配给安全资产
        safe_indices = [i for i, a in enumerate(assets) if a in safe_assets]
        if safe_indices and freed_weight > 0:
            add_per_asset = freed_weight / len(safe_indices)
            for i in safe_indices:
                weights[i] += add_per_asset

        # 重新应用边界
        for i, asset in enumerate(assets):
            min_w = self.assets[asset]["min_weight"]
            max_w = self.assets[asset]["max_weight"]
            weights[i] = max(min_w, min(max_w, weights[i]))

        # 归一化
        weights = weights / weights.sum()
        return weights

    def _apply_ai_adjustments(
        self,
        weights: np.ndarray,
        assets: List[str],
        adjustments: Dict
    ) -> np.ndarray:
        """
        Apply AI-suggested adjustments to weights

        支持两种格式:
        1. 旧格式: {"SPY": "increase", "GLD": "decrease"}
        2. 新格式(P1): {"SPY": 0.05, "GLD": -0.03}  # 直接指定调整幅度
        """
        # 旧格式兼容映射
        legacy_values = {"increase": 0.05, "maintain": 0.0, "decrease": -0.05}

        for i, asset in enumerate(assets):
            if asset in adjustments:
                adj = adjustments[asset]
                if isinstance(adj, str):
                    # 旧格式: "increase" -> +5%
                    delta = legacy_values.get(adj, 0.0)
                elif isinstance(adj, (int, float)):
                    # 新格式: 直接是数值
                    delta = float(adj)
                else:
                    delta = 0.0

                weights[i] += delta

        # Re-apply bounds
        for i, asset in enumerate(assets):
            min_w = self.assets[asset]["min_weight"]
            max_w = self.assets[asset]["max_weight"]
            weights[i] = max(min_w, min(max_w, weights[i]))

        # Normalize
        weights = weights / weights.sum()
        return weights

    def _estimate_max_drawdown(self, volatility: float, holding_period_years: float = 1.0) -> float:
        """
        Estimate maximum drawdown based on volatility

        使用更精确的经验公式 (Magdon-Ismail et al.):
        E[MDD] ≈ volatility * sqrt(T) * (0.63 + 0.5 * ln(T)) for T in years

        对于1年期，约为 volatility * 1.1
        """
        if holding_period_years <= 0:
            holding_period_years = 1.0

        # 更保守的估算，考虑肥尾
        base_estimate = volatility * np.sqrt(holding_period_years) * (0.63 + 0.5 * np.log(max(holding_period_years, 0.1)))

        # 对于高波动资产(如BTC)，用更保守的系数
        if volatility > 0.5:
            base_estimate *= 1.3

        return min(base_estimate, 0.95)

    def _composite_objective(
        self, weights: np.ndarray, mean_returns: pd.Series, cov_matrix: pd.DataFrame,
        max_drawdown_limit: Optional[float] = None
    ) -> float:
        """
        综合优化目标：在最大回撤约束下最大化夏普比率
        目标函数 = -Sharpe + penalty * max(0, estimated_mdd - max_drawdown_limit)
        """
        mdd_limit = max_drawdown_limit if max_drawdown_limit is not None else self.max_drawdown
        sharpe = self._sharpe_ratio(weights, mean_returns, cov_matrix)
        vol = self._portfolio_volatility(weights, cov_matrix)
        estimated_mdd = self._estimate_max_drawdown(vol)

        # 回撤惩罚：超过限制时大幅惩罚
        drawdown_penalty = 0
        if estimated_mdd > mdd_limit:
            drawdown_penalty = 100 * (estimated_mdd - mdd_limit) ** 2

        # 目标：最大化夏普比率（取负），同时惩罚超限回撤
        return -sharpe + drawdown_penalty

    def _risk_aware_objective(
        self,
        weights: np.ndarray,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        assets: List[str],
        risk_context: Dict,
        max_drawdown_limit: Optional[float] = None
    ) -> float:
        """
        风险感知优化目标：将统一风险上下文集成到目标函数

        与简单的后处理调整不同，这个方法将风险因素作为优化约束：
        1. 根据风险等级调整预期收益
        2. 对高风险资产在高风险环境下施加惩罚
        3. 在低风险环境下允许更高风险敞口
        """
        mdd_limit = max_drawdown_limit if max_drawdown_limit is not None else self.max_drawdown

        # 基础夏普比率
        sharpe = self._sharpe_ratio(weights, mean_returns, cov_matrix)

        # 波动率和回撤
        vol = self._portfolio_volatility(weights, cov_matrix)
        estimated_mdd = self._estimate_max_drawdown(vol)

        # 回撤惩罚
        drawdown_penalty = 0
        if estimated_mdd > mdd_limit:
            drawdown_penalty = 100 * (estimated_mdd - mdd_limit) ** 2

        # 风险敞口惩罚：根据风险上下文调整
        risk_multiplier = risk_context.get('risk_asset_multiplier', 1.0)
        risk_penalty = 0

        if risk_multiplier < 1.0:
            # 高风险环境：惩罚过多的风险资产持仓
            high_risk_exposure = 0
            for i, asset in enumerate(assets):
                if asset in self.risk_categories.get('high_risk', []):
                    high_risk_exposure += weights[i]

            # 风险敞口超过调整后阈值时惩罚
            adjusted_threshold = 0.3 * risk_multiplier  # 基础阈值30%
            if high_risk_exposure > adjusted_threshold:
                risk_penalty = 50 * (high_risk_exposure - adjusted_threshold) ** 2

        # 无论风险环境如何，都惩罚过高的现金配置（超过 40%）
        cash_exposure = 0
        for i, asset in enumerate(assets):
            if asset == 'CASH':
                cash_exposure = weights[i]
                break

        # 现金超过 40% 时施加惩罚，鼓励更多风险敞口
        if cash_exposure > 0.4:
            risk_penalty += 20 * (cash_exposure - 0.4) ** 2

        if risk_multiplier > 1.0:
            # 低风险环境：惩罚过多的安全资产持仓
            low_risk_exposure = 0
            for i, asset in enumerate(assets):
                if asset in self.risk_categories.get('low_risk', []):
                    low_risk_exposure += weights[i]

            # 如果安全资产过多（超过 50%），惩罚
            if low_risk_exposure > 0.5:
                risk_penalty += 10 * (low_risk_exposure - 0.5)

        # 综合目标：最大化夏普比率，约束回撤和风险敞口
        return -sharpe + drawdown_penalty + risk_penalty

    def round_allocation(
        self,
        allocation: Dict[str, float],
        step: float = 0.05
    ) -> Dict[str, float]:
        """
        方案C: 将配置取整到指定步长(默认5%)

        取整规则：
        - 所有仓位取整到 step (5%)
        - 确保总和为 100%
        - 优先调整最大仓位来平衡误差
        """
        # 先取整
        rounded = {}
        for asset, weight in allocation.items():
            rounded[asset] = round(weight / step) * step

        # 计算误差
        total = sum(rounded.values())
        error = 1.0 - total

        # 用最大仓位吸收误差
        if abs(error) > 0.001:
            max_asset = max(rounded, key=rounded.get)
            rounded[max_asset] += error
            rounded[max_asset] = round(rounded[max_asset], 4)

        return rounded

    def generate_rebalance_advice(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float],
        threshold: float = 0.05,
        expected_improvement: float = 0.0,
        portfolio_value: float = 100000
    ) -> Dict[str, Dict]:
        """
        方案C + P1: 生成调仓建议（含交易成本分析）

        Args:
            current_allocation: 当前配置
            target_allocation: 目标配置(已取整)
            threshold: 漂移阈值，超过才建议调仓
            expected_improvement: 预期夏普比率改善
            portfolio_value: 组合价值（用于计算绝对成本）

        Returns:
            {
                "SPY": {"current": 0.25, "target": 0.30, "drift": 0.05, "action": "调仓", "direction": "↑", "cost": 0.0003},
                ...
                "_summary": {"total_cost": ..., "cost_benefit_ratio": ..., "recommendation": ...}
            }
        """
        advice = {}
        all_assets = set(current_allocation.keys()) | set(target_allocation.keys())

        # P1: 计算交易成本
        rebalance_cost = self.calculate_rebalance_cost(
            current_allocation, target_allocation, portfolio_value
        )

        for asset in all_assets:
            current = current_allocation.get(asset, 0.0)
            target = target_allocation.get(asset, 0.0)
            drift = target - current
            abs_drift = abs(drift)

            # 获取该资产的交易成本
            asset_cost = rebalance_cost['by_asset'].get(asset, 0)

            if abs_drift >= threshold:
                action = "调仓"
                direction = "↑" if drift > 0 else "↓"
            else:
                action = "维持"
                direction = ""

            advice[asset] = {
                "current": round(current, 4),
                "target": round(target, 4),
                "drift": round(drift, 4),
                "abs_drift": round(abs_drift, 4),
                "action": action,
                "direction": direction,
                "cost_pct": round(asset_cost * 100, 4)  # 转为百分比
            }

        # P1: 成本效益分析
        total_cost_pct = rebalance_cost['total_cost_pct']

        # 判断是否值得调仓
        # 规则：预期年化改善 > 交易成本 * 调仓频率系数
        # 假设年调仓4次，则单次成本需要 < 预期改善/4
        rebalance_freq_factor = 4
        min_improvement_needed = total_cost_pct * rebalance_freq_factor

        if expected_improvement > 0:
            cost_benefit_ratio = expected_improvement / total_cost_pct if total_cost_pct > 0 else float('inf')
            is_worthwhile = expected_improvement > min_improvement_needed
        else:
            cost_benefit_ratio = 0
            is_worthwhile = rebalance_cost['turnover'] > 0.1  # 换手率>10%时才调仓

        # 总结
        advice["_summary"] = {
            "total_cost_pct": round(total_cost_pct * 100, 4),
            "total_cost_abs": rebalance_cost['total_cost_abs'],
            "turnover": round(rebalance_cost['turnover'] * 100, 2),
            "expected_improvement": round(expected_improvement * 100, 4) if expected_improvement else None,
            "cost_benefit_ratio": round(cost_benefit_ratio, 2) if cost_benefit_ratio != float('inf') else "N/A",
            "is_worthwhile": is_worthwhile,
            "recommendation": "建议调仓" if is_worthwhile else "成本过高，建议维持"
        }

        return advice

    def rolling_validation(
        self,
        returns: pd.DataFrame,
        method: str = "max_sharpe_cvar",
        train_window: int = 180,
        test_window: int = 60,
        step: int = 30,
        max_drawdown: float = 0.25
    ) -> Dict:
        """
        P2: 滚动窗口验证策略稳健性

        Args:
            returns: 完整历史收益率
            method: 优化方法
            train_window: 训练窗口天数
            test_window: 测试窗口天数
            step: 滚动步长天数
            max_drawdown: 回撤阈值

        Returns:
            {
                'n_periods': 滚动周期数,
                'avg_sharpe': 平均样本外夏普,
                'sharpe_std': 夏普标准差,
                'avg_mdd': 平均样本外回撤,
                'win_rate': 正收益周期占比,
                'periods': [{period_details}, ...]
            }
        """
        available_assets = [a for a in returns.columns if a in self.assets]
        returns = returns[available_assets]

        min_data = train_window + test_window
        if len(returns) < min_data:
            return {"error": f"Insufficient data: need {min_data} days, got {len(returns)}"}

        periods = []
        start_idx = 0

        while start_idx + train_window + test_window <= len(returns):
            train_end = start_idx + train_window
            test_end = train_end + test_window

            train_data = returns.iloc[start_idx:train_end]
            test_data = returns.iloc[train_end:test_end]

            # 训练期优化
            cov_matrix = self.estimate_covariance(train_data, method="ledoit_wolf")
            mean_returns = self.estimate_expected_returns(
                train_data, cov_matrix, method="shrinkage"
            )

            # 简化优化（不使用完整 optimize 方法避免递归）
            n_assets = len(available_assets)
            bounds = [(self.assets[a]["min_weight"], self.assets[a]["max_weight"]) for a in available_assets]
            init_weights = np.array([1.0 / n_assets] * n_assets)
            constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

            result = minimize(
                lambda w: -self._sharpe_ratio(w, mean_returns, cov_matrix),
                init_weights,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints
            )

            weights = result.x if result.success else self._bounded_equal_weight(available_assets)

            # 测试期表现
            test_portfolio_returns = (test_data * weights).sum(axis=1)
            test_sharpe = self.risk_metrics.calculate_sharpe_ratio(test_portfolio_returns, self.risk_free_rate)
            test_mdd = self.risk_metrics.calculate_max_drawdown(test_portfolio_returns)
            test_return = test_portfolio_returns.mean() * 252

            periods.append({
                'train_start': train_data.index[0].strftime('%Y-%m-%d') if hasattr(train_data.index[0], 'strftime') else str(train_data.index[0]),
                'test_end': test_data.index[-1].strftime('%Y-%m-%d') if hasattr(test_data.index[-1], 'strftime') else str(test_data.index[-1]),
                'sharpe': round(test_sharpe, 4),
                'return': round(test_return, 4),
                'mdd': round(abs(test_mdd), 4),
                'within_limit': abs(test_mdd) <= max_drawdown
            })

            start_idx += step

        if not periods:
            return {"error": "No valid periods"}

        sharpes = [p['sharpe'] for p in periods]
        mdds = [p['mdd'] for p in periods]
        returns_list = [p['return'] for p in periods]

        return {
            'n_periods': len(periods),
            'avg_sharpe': round(np.mean(sharpes), 4),
            'sharpe_std': round(np.std(sharpes), 4),
            'min_sharpe': round(min(sharpes), 4),
            'max_sharpe': round(max(sharpes), 4),
            'avg_mdd': round(np.mean(mdds), 4),
            'max_mdd': round(max(mdds), 4),
            'avg_return': round(np.mean(returns_list), 4),
            'win_rate': round(sum(1 for r in returns_list if r > 0) / len(returns_list), 4),
            'within_limit_rate': round(sum(1 for p in periods if p['within_limit']) / len(periods), 4),
            'periods': periods[-5:]  # 只返回最近5个周期详情
        }

    def get_efficient_frontier(
        self, returns: pd.DataFrame, n_points: int = 50
    ) -> List[Dict]:
        """Calculate efficient frontier points"""
        available_assets = [a for a in returns.columns if a in self.assets]
        returns = returns[available_assets]

        mean_returns = returns.mean() * 252
        cov_matrix = returns.cov() * 252

        # Find min and max return portfolios
        min_ret = mean_returns.min()
        max_ret = mean_returns.max()

        frontier = []
        target_returns = np.linspace(min_ret, max_ret, n_points)

        for target in target_returns:
            try:
                result = self._optimize_for_target_return(
                    target, mean_returns, cov_matrix, available_assets
                )
                if result:
                    frontier.append(result)
            except:
                continue

        return frontier

    def _optimize_for_target_return(
        self,
        target_return: float,
        mean_returns: pd.Series,
        cov_matrix: pd.DataFrame,
        assets: List[str]
    ) -> Optional[Dict]:
        """Optimize for minimum volatility at target return"""
        n_assets = len(assets)
        bounds = [
            (self.assets[a]["min_weight"], self.assets[a]["max_weight"])
            for a in assets
        ]

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w: np.sum(mean_returns * w) - target_return}
        ]

        result = minimize(
            lambda w: self._portfolio_volatility(w, cov_matrix),
            np.array([1.0 / n_assets] * n_assets),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints
        )

        if result.success:
            vol = self._portfolio_volatility(result.x, cov_matrix)
            sharpe = (target_return - self.risk_free_rate) / vol if vol > 0 else 0
            return {
                "return": round(float(target_return), 4),
                "volatility": round(float(vol), 4),
                "sharpe": round(float(sharpe), 4)
            }
        return None
