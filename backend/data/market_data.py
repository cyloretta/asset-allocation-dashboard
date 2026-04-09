"""
市场数据获取模块 - 使用多数据源架构
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from config import get_settings
from data.data_providers import multi_source_fetcher, price_cache, history_cache

settings = get_settings()
logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """市场数据获取器 - 封装多数据源调度"""

    def __init__(self):
        self.tickers = [t for t in settings.assets.keys() if t != "CASH"]
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.fetcher = multi_source_fetcher

    def _fetch_ticker_sync(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """同步获取单个 ticker 的历史数据"""
        days = {"5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}.get(period, 365)
        return self.fetcher.get_history(ticker, days)

    async def fetch_all(self, period: str = "1y") -> Dict[str, pd.DataFrame]:
        """获取所有 tickers 的数据"""
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, self._fetch_ticker_sync, ticker, period)
            for ticker in self.tickers
        ]
        results = await asyncio.gather(*tasks)
        return {ticker: df for ticker, df in zip(self.tickers, results) if not df.empty}

    async def fetch_ticker(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """获取单个 ticker 数据"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._fetch_ticker_sync, ticker, period
        )

    async def get_current_prices(self) -> Dict[str, dict]:
        """获取所有 tickers 的当前价格"""
        prices = {}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        loop = asyncio.get_event_loop()

        # 并行获取所有价格
        async def fetch_price(ticker: str) -> tuple:
            data = await loop.run_in_executor(
                self.executor, self.fetcher.get_price, ticker
            )
            return ticker, data

        tasks = [fetch_price(t) for t in self.tickers]
        results = await asyncio.gather(*tasks)

        for ticker, data in results:
            if data.get('success'):
                prices[ticker] = {
                    "price": round(data['price'], 2),
                    "change": round(data.get('change', 0), 2),
                    "volume": int(data.get('volume', 0)),
                    "high": round(data.get('high', 0), 2),
                    "low": round(data.get('low', 0), 2),
                    "date": f"{now} ({data.get('source', 'Unknown')})",
                    "is_mock": False
                }
            else:
                prices[ticker] = {
                    "price": 0, "change": 0, "volume": 0,
                    "high": 0, "low": 0, "date": now,
                    "is_mock": True, "error": data.get('error', 'fetch failed')
                }

        # 添加现金
        prices["CASH"] = {
            "price": 1.0, "change": 0.0, "volume": 0,
            "high": 1.0, "low": 1.0, "date": now, "is_mock": False
        }
        return prices

    async def get_historical_returns(self, period: str = "1y") -> pd.DataFrame:
        """获取历史收益率矩阵用于组合优化"""
        data = await self.fetch_all(period=period)

        # 收集各 ticker 的收盘价，分别存储（不直接合并，避免索引不匹配）
        ticker_closes = {}
        for ticker, df in data.items():
            if not df.empty and 'Close' in df.columns:
                # 确保索引是日期类型，去除时间部分
                close_series = df["Close"].copy()
                if hasattr(close_series.index, 'date'):
                    close_series.index = pd.to_datetime(close_series.index.date)
                # 去除重复索引，保留最后一个
                close_series = close_series[~close_series.index.duplicated(keep='last')]
                ticker_closes[ticker] = close_series

        # 如果没有任何数据，生成全部 mock 数据
        if not ticker_closes:
            logger.warning("No real data available, using all mock data")
            return self._generate_mock_returns()

        # 找到所有日期的并集，然后对齐
        all_dates = set()
        for series in ticker_closes.values():
            all_dates.update(series.index)
        all_dates = sorted(all_dates)

        # 创建统一索引的 DataFrame
        closes = pd.DataFrame(index=all_dates)
        for ticker, series in ticker_closes.items():
            closes[ticker] = series.reindex(all_dates)

        # 检查缺失的 tickers
        missing_tickers = [t for t in self.tickers if t not in closes.columns]

        # 为缺失的 tickers 生成 mock 收益率
        mock_returns = pd.DataFrame()
        if missing_tickers:
            logger.warning(f"Missing tickers {missing_tickers}, using mock data")
            np.random.seed(42)
            mock_params = {
                "SPY": {"mean": 0.10, "vol": 0.15},
                "QQQ": {"mean": 0.15, "vol": 0.22},
                "GLD": {"mean": 0.05, "vol": 0.12},
                "BTC-USD": {"mean": 0.30, "vol": 0.60},
                "TLT": {"mean": 0.02, "vol": 0.10},
            }
            for ticker in missing_tickers:
                params = mock_params.get(ticker, {"mean": 0.05, "vol": 0.15})
                daily_mean = params["mean"] / 252
                daily_vol = params["vol"] / np.sqrt(252)
                mock_returns[ticker] = pd.Series(
                    np.random.normal(daily_mean, daily_vol, len(all_dates)),
                    index=all_dates,
                    name=ticker
                )

        # 计算收益率（填充缺失值后再计算）
        # 使用前向填充处理缺失值
        closes_filled = closes.ffill().bfill()
        real_returns = closes_filled.pct_change().dropna()

        # 合并真实收益率和模拟收益率
        if not real_returns.empty and not mock_returns.empty:
            # 对齐到相同日期
            common_dates = real_returns.index.intersection(mock_returns.index)
            if len(common_dates) > 0:
                returns = pd.concat([
                    real_returns.loc[common_dates],
                    mock_returns.loc[common_dates]
                ], axis=1)
            else:
                # 如果没有交集，用最后 N 个日期
                n_days = min(len(real_returns), len(mock_returns))
                returns = pd.concat([
                    real_returns.iloc[-n_days:].reset_index(drop=True),
                    mock_returns.iloc[-n_days:].reset_index(drop=True)
                ], axis=1)
        elif not real_returns.empty:
            returns = real_returns
        else:
            returns = mock_returns

        # 确保有足够的数据
        if len(returns) < 60:
            logger.warning(f"Insufficient data ({len(returns)} days), using mock data")
            return self._generate_mock_returns()

        # CASH 的收益率为 0
        returns["CASH"] = 0.0
        return returns

    def _generate_mock_returns(self) -> pd.DataFrame:
        """生成完整的 mock 收益率数据"""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=252, freq='B')
        mock_params = {
            "SPY": {"mean": 0.10, "vol": 0.15},
            "QQQ": {"mean": 0.15, "vol": 0.22},
            "GLD": {"mean": 0.05, "vol": 0.12},
            "BTC-USD": {"mean": 0.30, "vol": 0.60},
            "TLT": {"mean": 0.02, "vol": 0.10},
        }
        returns = pd.DataFrame(index=dates)
        for ticker in self.tickers:
            params = mock_params.get(ticker, {"mean": 0.05, "vol": 0.15})
            daily_mean = params["mean"] / 252
            daily_vol = params["vol"] / np.sqrt(252)
            returns[ticker] = np.random.normal(daily_mean, daily_vol, 252)
        returns["CASH"] = 0.0
        return returns

    def get_ticker_info(self, ticker: str) -> dict:
        """获取 ticker 详细信息"""
        data = self.fetcher.get_price(ticker)
        if data.get('success'):
            return {
                "name": ticker,
                "price": data.get('price', 0),
                "source": data.get('source', 'Unknown')
            }
        return {"name": ticker}

    def get_data_sources_health(self) -> Dict[str, bool]:
        """获取数据源健康状态"""
        return self.fetcher.get_health()

    def clear_cache(self):
        """清空缓存"""
        self.fetcher.clear_cache()
