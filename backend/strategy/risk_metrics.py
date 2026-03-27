import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy import stats


class RiskMetrics:
    """Calculate portfolio risk metrics"""

    @staticmethod
    def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
        """Calculate daily returns from prices"""
        return prices.pct_change().dropna()

    @staticmethod
    def calculate_cumulative_returns(returns: pd.DataFrame) -> pd.DataFrame:
        """Calculate cumulative returns"""
        return (1 + returns).cumprod() - 1

    @staticmethod
    def calculate_max_drawdown(returns: pd.Series) -> float:
        """Calculate maximum drawdown"""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return float(drawdown.min())

    @staticmethod
    def calculate_sharpe_ratio(
        returns: pd.Series, risk_free_rate: float = 0.05
    ) -> float:
        """Calculate annualized Sharpe ratio"""
        excess_returns = returns - risk_free_rate / 252
        if returns.std() == 0:
            return 0
        return float(np.sqrt(252) * excess_returns.mean() / returns.std())

    @staticmethod
    def calculate_sortino_ratio(
        returns: pd.Series, risk_free_rate: float = 0.05
    ) -> float:
        """Calculate annualized Sortino ratio (only considers downside volatility)"""
        excess_returns = returns - risk_free_rate / 252
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0
        return float(np.sqrt(252) * excess_returns.mean() / downside_returns.std())

    @staticmethod
    def calculate_var(returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Value at Risk at given confidence level"""
        return float(np.percentile(returns, (1 - confidence) * 100))

    @staticmethod
    def calculate_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Conditional VaR (Expected Shortfall)"""
        var = np.percentile(returns, (1 - confidence) * 100)
        return float(returns[returns <= var].mean())

    @staticmethod
    def calculate_calmar_ratio(returns: pd.Series) -> float:
        """Calculate Calmar ratio (annualized return / max drawdown)"""
        ann_return = returns.mean() * 252
        mdd = RiskMetrics.calculate_max_drawdown(returns)
        if mdd == 0:
            return 0
        return float(ann_return / abs(mdd))

    @staticmethod
    def calculate_beta(
        portfolio_returns: pd.Series, benchmark_returns: pd.Series
    ) -> float:
        """Calculate portfolio beta relative to benchmark"""
        if len(portfolio_returns) != len(benchmark_returns):
            min_len = min(len(portfolio_returns), len(benchmark_returns))
            portfolio_returns = portfolio_returns.iloc[-min_len:]
            benchmark_returns = benchmark_returns.iloc[-min_len:]

        covariance = portfolio_returns.cov(benchmark_returns)
        benchmark_variance = benchmark_returns.var()
        if benchmark_variance == 0:
            return 1.0
        return float(covariance / benchmark_variance)

    @staticmethod
    def calculate_alpha(
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        risk_free_rate: float = 0.05
    ) -> float:
        """Calculate Jensen's alpha"""
        beta = RiskMetrics.calculate_beta(portfolio_returns, benchmark_returns)
        ann_portfolio_return = portfolio_returns.mean() * 252
        ann_benchmark_return = benchmark_returns.mean() * 252
        return float(ann_portfolio_return - (risk_free_rate + beta * (ann_benchmark_return - risk_free_rate)))

    @staticmethod
    def calculate_information_ratio(
        portfolio_returns: pd.Series, benchmark_returns: pd.Series
    ) -> float:
        """Calculate Information Ratio"""
        if len(portfolio_returns) != len(benchmark_returns):
            min_len = min(len(portfolio_returns), len(benchmark_returns))
            portfolio_returns = portfolio_returns.iloc[-min_len:]
            benchmark_returns = benchmark_returns.iloc[-min_len:]

        active_return = portfolio_returns - benchmark_returns
        if active_return.std() == 0:
            return 0
        return float(np.sqrt(252) * active_return.mean() / active_return.std())

    def calculate_all_metrics(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series = None,
        risk_free_rate: float = 0.05
    ) -> Dict:
        """Calculate all risk metrics for a portfolio"""
        metrics = {
            "total_return": float((1 + portfolio_returns).prod() - 1),
            "annualized_return": float(portfolio_returns.mean() * 252),
            "annualized_volatility": float(portfolio_returns.std() * np.sqrt(252)),
            "sharpe_ratio": self.calculate_sharpe_ratio(portfolio_returns, risk_free_rate),
            "sortino_ratio": self.calculate_sortino_ratio(portfolio_returns, risk_free_rate),
            "max_drawdown": self.calculate_max_drawdown(portfolio_returns),
            "calmar_ratio": self.calculate_calmar_ratio(portfolio_returns),
            "var_95": self.calculate_var(portfolio_returns, 0.95),
            "cvar_95": self.calculate_cvar(portfolio_returns, 0.95),
            "skewness": float(portfolio_returns.skew()),
            "kurtosis": float(portfolio_returns.kurtosis()),
            "positive_days": float((portfolio_returns > 0).sum() / len(portfolio_returns)),
        }

        if benchmark_returns is not None:
            metrics["beta"] = self.calculate_beta(portfolio_returns, benchmark_returns)
            metrics["alpha"] = self.calculate_alpha(
                portfolio_returns, benchmark_returns, risk_free_rate
            )
            metrics["information_ratio"] = self.calculate_information_ratio(
                portfolio_returns, benchmark_returns
            )

        return metrics

    def calculate_rolling_metrics(
        self, returns: pd.Series, window: int = 60
    ) -> pd.DataFrame:
        """Calculate rolling risk metrics"""
        rolling = pd.DataFrame(index=returns.index)

        rolling["return"] = returns.rolling(window).mean() * 252
        rolling["volatility"] = returns.rolling(window).std() * np.sqrt(252)
        rolling["sharpe"] = rolling["return"] / rolling["volatility"]

        # Rolling max drawdown
        rolling["max_drawdown"] = returns.rolling(window).apply(
            lambda x: self.calculate_max_drawdown(x), raw=False
        )

        return rolling.dropna()

    @staticmethod
    def calculate_rolling_correlation(
        returns: pd.DataFrame,
        window: int = 20
    ) -> pd.DataFrame:
        """计算滚动相关性矩阵的平均值（危机检测指标）"""
        n_assets = len(returns.columns)
        if n_assets < 2:
            return pd.DataFrame()

        # 计算每个时间点的平均相关性
        avg_correlations = []
        dates = []

        for i in range(window, len(returns)):
            window_data = returns.iloc[i-window:i]
            corr_matrix = window_data.corr()

            # 提取上三角（不含对角线）的相关系数
            upper_tri = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )
            avg_corr = upper_tri.stack().mean()
            avg_correlations.append(avg_corr)
            dates.append(returns.index[i])

        return pd.DataFrame({
            'date': dates,
            'avg_correlation': avg_correlations
        }).set_index('date')

    @staticmethod
    def detect_correlation_regime(
        returns: pd.DataFrame,
        window: int = 20,
        crisis_threshold: float = 0.7
    ) -> Dict:
        """
        检测相关性状态，判断是否处于危机模式

        危机时资产相关性趋同（平均相关性 > 0.7）
        """
        n_assets = len(returns.columns)
        if n_assets < 2 or len(returns) < window:
            return {
                'regime': 'unknown',
                'avg_correlation': 0,
                'is_crisis': False,
                'risk_adjustment': 1.0
            }

        # 计算最近窗口的平均相关性
        recent_returns = returns.tail(window)
        corr_matrix = recent_returns.corr()

        # 提取上三角的相关系数
        upper_tri = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        current_avg_corr = upper_tri.stack().mean()

        # 计算历史平均相关性（用于比较）
        if len(returns) >= window * 3:
            historical_returns = returns.iloc[:-window]
            hist_corr_matrix = historical_returns.corr()
            hist_upper_tri = hist_corr_matrix.where(
                np.triu(np.ones(hist_corr_matrix.shape), k=1).astype(bool)
            )
            historical_avg_corr = hist_upper_tri.stack().mean()
        else:
            historical_avg_corr = 0.3  # 默认历史平均

        # 判断是否处于危机
        is_crisis = current_avg_corr > crisis_threshold
        corr_spike = current_avg_corr - historical_avg_corr

        # 计算风险调整系数（危机时降低风险敞口）
        if is_crisis:
            risk_adjustment = max(0.5, 1.0 - (current_avg_corr - crisis_threshold))
        elif corr_spike > 0.2:
            risk_adjustment = 0.8  # 相关性显著上升时轻微降低
        else:
            risk_adjustment = 1.0

        # 确定状态
        if current_avg_corr > crisis_threshold:
            regime = 'crisis'
        elif current_avg_corr > 0.5:
            regime = 'elevated'
        else:
            regime = 'normal'

        return {
            'regime': regime,
            'avg_correlation': round(float(current_avg_corr), 4),
            'historical_avg': round(float(historical_avg_corr), 4),
            'correlation_spike': round(float(corr_spike), 4),
            'is_crisis': bool(is_crisis),  # 转换为 Python bool
            'risk_adjustment': round(float(risk_adjustment), 2),
            'threshold': float(crisis_threshold)
        }

    @staticmethod
    def estimate_parametric_cvar(
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        confidence: float = 0.95
    ) -> float:
        """
        参数化 CVaR 估计（假设正态分布）

        用于优化约束，比历史 CVaR 更平滑可微

        Args:
            weights: 资产权重
            mean_returns: 年化预期收益
            cov_matrix: 年化协方差矩阵
            confidence: 置信水平 (默认 95%)

        Returns:
            年化 CVaR (正值表示损失)
        """
        # 组合日收益和波动率
        port_return = np.dot(weights, mean_returns) / 252
        port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) / np.sqrt(252)

        if port_vol <= 0:
            return 0.0

        # 正态分布的 VaR 和 CVaR
        alpha = 1 - confidence
        z_alpha = stats.norm.ppf(alpha)

        # 日 VaR
        daily_var = -(port_return + z_alpha * port_vol)

        # 日 CVaR (Expected Shortfall)
        # E[X | X < VaR] = μ - σ * φ(z_α) / α
        pdf_z = stats.norm.pdf(z_alpha)
        daily_cvar = -(port_return - port_vol * pdf_z / alpha)

        # 年化 (假设损失独立，用 sqrt(252) 放大)
        annual_cvar = daily_cvar * np.sqrt(252)

        return float(max(0, annual_cvar))

    @staticmethod
    def estimate_mdd_from_cvar(
        cvar: float,
        holding_period_days: int = 252,
        confidence: float = 0.95
    ) -> float:
        """
        基于 CVaR 估计最大回撤

        经验关系: MDD ≈ CVaR * sqrt(T/252) * adjustment_factor

        Args:
            cvar: 年化 CVaR
            holding_period_days: 持有期天数
            confidence: CVaR 的置信水平

        Returns:
            预期最大回撤 (0-1)
        """
        if cvar <= 0:
            return 0.0

        # 调整因子：考虑路径依赖和厚尾
        # 95% CVaR 转 95% MDD 的经验系数约为 1.5-2.0
        adjustment = 1.8 if confidence >= 0.95 else 1.5

        # 时间缩放
        time_factor = np.sqrt(holding_period_days / 252)

        estimated_mdd = cvar * time_factor * adjustment

        return float(min(0.95, estimated_mdd))  # 上限 95%

    @staticmethod
    def monte_carlo_mdd(
        weights: np.ndarray,
        mean_returns: np.ndarray,
        cov_matrix: np.ndarray,
        n_simulations: int = 1000,
        n_days: int = 252,
        confidence: float = 0.95
    ) -> Dict:
        """
        Monte Carlo 模拟最大回撤分布

        Args:
            weights: 资产权重
            mean_returns: 年化预期收益向量
            cov_matrix: 年化协方差矩阵
            n_simulations: 模拟次数
            n_days: 模拟天数
            confidence: 置信水平

        Returns:
            {
                'expected_mdd': 平均最大回撤,
                'mdd_at_confidence': 指定置信度的最大回撤,
                'mdd_std': 最大回撤标准差,
                'percentiles': {50: ..., 75: ..., 95: ..., 99: ...}
            }
        """
        # 转为日参数
        daily_mean = mean_returns / 252
        daily_cov = cov_matrix / 252

        # 组合参数
        port_daily_return = np.dot(weights, daily_mean)
        port_daily_vol = np.sqrt(np.dot(weights.T, np.dot(daily_cov, weights)))

        # 模拟
        np.random.seed(42)  # 可重现
        mdds = []

        for _ in range(n_simulations):
            # 生成日收益路径
            returns = np.random.normal(port_daily_return, port_daily_vol, n_days)

            # 计算累计价值
            cumulative = np.cumprod(1 + returns)

            # 计算回撤
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max) / running_max
            max_dd = abs(drawdowns.min())
            mdds.append(max_dd)

        mdds = np.array(mdds)

        return {
            'expected_mdd': float(np.mean(mdds)),
            'mdd_at_confidence': float(np.percentile(mdds, confidence * 100)),
            'mdd_std': float(np.std(mdds)),
            'percentiles': {
                50: float(np.percentile(mdds, 50)),
                75: float(np.percentile(mdds, 75)),
                95: float(np.percentile(mdds, 95)),
                99: float(np.percentile(mdds, 99))
            }
        }
