import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .risk_metrics import RiskMetrics
from config import get_settings


class Backtester:
    """Backtest portfolio strategies"""

    def __init__(self):
        self.risk_metrics = RiskMetrics()

    def backtest_strategy(
        self,
        returns: pd.DataFrame,
        allocation: Dict[str, float],
        rebalance_freq: str = "monthly",
        start_value: float = 100000,
        transaction_cost: float = 0.001,  # P1: 交易成本 (0.1% = 滑点 + 手续费)
        slippage: float = 0.0005  # P1: 额外滑点
    ) -> Dict:
        """
        Backtest a portfolio allocation strategy

        Args:
            returns: DataFrame of asset returns
            allocation: Dict of asset -> weight
            rebalance_freq: "daily", "weekly", "monthly", "quarterly"
            start_value: Initial portfolio value
            transaction_cost: Trading cost as fraction (e.g., 0.001 = 0.1%)
            slippage: Additional slippage cost

        Returns:
            Dict with backtest results
        """
        total_cost_rate = transaction_cost + slippage

        # Filter to available assets
        available_assets = [a for a in allocation.keys() if a in returns.columns]
        weights = np.array([allocation[a] for a in available_assets])
        weights = weights / weights.sum()  # Normalize

        asset_returns = returns[available_assets]

        # Calculate portfolio returns
        if rebalance_freq == "daily":
            # Daily rebalancing means constant weights (with daily costs)
            portfolio_returns = (asset_returns * weights).sum(axis=1)
            # 每日再平衡的成本
            portfolio_returns = portfolio_returns - total_cost_rate
        else:
            # Periodic rebalancing with transaction costs
            portfolio_returns = self._calculate_rebalanced_returns(
                asset_returns, weights, rebalance_freq, total_cost_rate
            )

        # Calculate portfolio value series
        portfolio_values = start_value * (1 + portfolio_returns).cumprod()

        # Get benchmark (SPY) returns if available
        benchmark_returns = returns["SPY"] if "SPY" in returns.columns else None

        # Calculate metrics
        settings = get_settings()
        metrics = self.risk_metrics.calculate_all_metrics(
            portfolio_returns,
            benchmark_returns,
            risk_free_rate=settings.risk_free_rate
        )

        # Calculate drawdown series
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max

        # P1: 估算总交易成本
        n_rebalances = len(portfolio_returns) // {"daily": 1, "weekly": 5, "monthly": 21, "quarterly": 63}.get(rebalance_freq, 21)
        estimated_total_cost = n_rebalances * total_cost_rate * 0.3  # 假设平均换手率30%

        return {
            "portfolio_values": portfolio_values.tolist(),
            "portfolio_returns": portfolio_returns.tolist(),
            "dates": [d.strftime("%Y-%m-%d") for d in portfolio_returns.index],
            "drawdown": drawdown.tolist(),
            "metrics": metrics,
            "final_value": float(portfolio_values.iloc[-1]),
            "total_return": float(portfolio_values.iloc[-1] / start_value - 1),
            "allocation": allocation,
            "rebalance_freq": rebalance_freq,
            "transaction_cost": total_cost_rate,  # P1: 记录交易成本率
            "n_rebalances": n_rebalances,
            "estimated_total_cost": round(estimated_total_cost, 4)
        }

    def _calculate_rebalanced_returns(
        self,
        returns: pd.DataFrame,
        target_weights: np.ndarray,
        freq: str,
        transaction_cost: float = 0.001  # P1: 交易成本
    ) -> pd.Series:
        """Calculate returns with periodic rebalancing and transaction costs"""
        # Map frequency to rebalance days
        freq_days = {
            "weekly": 5,
            "monthly": 21,
            "quarterly": 63
        }
        rebalance_days = freq_days.get(freq, 21)

        portfolio_returns = pd.Series(index=returns.index, dtype=float)
        current_weights = target_weights.copy()
        total_turnover = 0.0  # 追踪总换手率

        for i, (date, row) in enumerate(returns.iterrows()):
            # Portfolio return for this day
            daily_return = (row.values * current_weights).sum()

            # Update weights based on asset returns (drift)
            current_weights = current_weights * (1 + row.values)
            current_weights = current_weights / current_weights.sum()

            # Rebalance at specified frequency
            if (i + 1) % rebalance_days == 0:
                # P1: 计算再平衡成本 (换手率 * 交易成本)
                turnover = np.sum(np.abs(current_weights - target_weights))
                rebalance_cost = turnover * transaction_cost
                daily_return -= rebalance_cost
                total_turnover += turnover

                current_weights = target_weights.copy()

            portfolio_returns.loc[date] = daily_return

        return portfolio_returns

    def compare_strategies(
        self,
        returns: pd.DataFrame,
        strategies: Dict[str, Dict[str, float]],
        start_value: float = 100000
    ) -> Dict:
        """Compare multiple allocation strategies"""
        results = {}

        for name, allocation in strategies.items():
            result = self.backtest_strategy(returns, allocation, start_value=start_value)
            results[name] = {
                "final_value": result["final_value"],
                "total_return": result["total_return"],
                "sharpe": result["metrics"]["sharpe_ratio"],
                "max_drawdown": result["metrics"]["max_drawdown"],
                "volatility": result["metrics"]["annualized_volatility"]
            }

        return results

    def monte_carlo_simulation(
        self,
        returns: pd.DataFrame,
        allocation: Dict[str, float],
        n_simulations: int = 1000,
        n_days: int = 252,
        start_value: float = 100000
    ) -> Dict:
        """Run Monte Carlo simulation for portfolio"""
        available_assets = [a for a in allocation.keys() if a in returns.columns]
        weights = np.array([allocation[a] for a in available_assets])
        weights = weights / weights.sum()

        asset_returns = returns[available_assets]

        # Calculate historical statistics
        mean_returns = asset_returns.mean().values
        cov_matrix = asset_returns.cov().values

        # Run simulations
        final_values = []
        paths = []

        for _ in range(n_simulations):
            # Generate random returns
            random_returns = np.random.multivariate_normal(
                mean_returns, cov_matrix, n_days
            )
            portfolio_returns = np.sum(random_returns * weights, axis=1)

            # Calculate portfolio value path
            values = start_value * np.cumprod(1 + portfolio_returns)
            final_values.append(values[-1])

            if len(paths) < 100:  # Store first 100 paths for visualization
                paths.append(values.tolist())

        final_values = np.array(final_values)

        return {
            "paths": paths,
            "final_values": {
                "mean": float(np.mean(final_values)),
                "median": float(np.median(final_values)),
                "std": float(np.std(final_values)),
                "percentile_5": float(np.percentile(final_values, 5)),
                "percentile_25": float(np.percentile(final_values, 25)),
                "percentile_75": float(np.percentile(final_values, 75)),
                "percentile_95": float(np.percentile(final_values, 95)),
            },
            "probability_profit": float((final_values > start_value).sum() / n_simulations),
            "expected_return": float(np.mean(final_values) / start_value - 1),
            "n_simulations": n_simulations,
            "n_days": n_days
        }
