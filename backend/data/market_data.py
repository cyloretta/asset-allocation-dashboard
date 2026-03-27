import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from io import StringIO
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Stooq 符号映射
STOOQ_SYMBOLS = {
    "SPY": "spy.us",
    "QQQ": "qqq.us",
    "GLD": "xauusd",  # 国际金价 (XAU/USD)
    "TLT": "tlt.us",
}


class MarketDataFetcher:
    def __init__(self):
        self.tickers = [t for t in settings.assets.keys() if t != "CASH"]
        self.executor = ThreadPoolExecutor(max_workers=5)

    def _fetch_stooq(self, ticker: str) -> dict:
        """从 Stooq 获取股票/ETF 数据"""
        stooq_symbol = STOOQ_SYMBOLS.get(ticker)
        if not stooq_symbol:
            return {'success': False}

        try:
            # 获取最新报价
            url = f"https://stooq.com/q/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and 'Symbol' in resp.text:
                df = pd.read_csv(StringIO(resp.text))
                if not df.empty:
                    row = df.iloc[0]
                    volume = row.get('Volume', 0)
                    if pd.isna(volume):
                        volume = 0
                    return {
                        'price': float(row['Close']),
                        'open': float(row['Open']),
                        'high': float(row['High']),
                        'low': float(row['Low']),
                        'volume': int(volume),
                        'date': str(row['Date']),
                        'success': True
                    }
        except Exception as e:
            logger.error(f"Stooq error for {ticker}: {e}")
        return {'success': False}

    def _fetch_stooq_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        """从 Stooq 获取历史数据"""
        stooq_symbol = STOOQ_SYMBOLS.get(ticker)
        if not stooq_symbol:
            return pd.DataFrame()

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&d1={start_date.strftime('%Y%m%d')}&d2={end_date.strftime('%Y%m%d')}&i=d"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200 and 'Date' in resp.text:
                df = pd.read_csv(StringIO(resp.text))
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                df['ticker'] = ticker
                return df
        except Exception as e:
            logger.error(f"Stooq history error for {ticker}: {e}")
        return pd.DataFrame()

    def _fetch_coingecko(self, coin_id: str = "bitcoin") -> dict:
        """从 CoinGecko 获取加密货币数据"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_24hr_high=true&include_24hr_low=true"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get(coin_id, {})
                return {
                    'price': data.get('usd', 0),
                    'change': data.get('usd_24h_change', 0),
                    'volume': data.get('usd_24h_vol', 0),
                    'high': data.get('usd_24h_high', 0),
                    'low': data.get('usd_24h_low', 0),
                    'success': True
                }
        except Exception as e:
            logger.error(f"CoinGecko error: {e}")
        return {'success': False}

    def _fetch_coingecko_history(self, coin_id: str = "bitcoin", days: int = 365) -> pd.DataFrame:
        """从 CoinGecko 获取加密货币历史数据"""
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                prices = data.get('prices', [])
                df = pd.DataFrame(prices, columns=['timestamp', 'Close'])
                df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('Date', inplace=True)
                df['Open'] = df['Close']
                df['High'] = df['Close']
                df['Low'] = df['Close']
                df['Volume'] = 0
                df['ticker'] = 'BTC-USD'
                return df[['Open', 'High', 'Low', 'Close', 'Volume', 'ticker']]
        except Exception as e:
            logger.error(f"CoinGecko history error: {e}")
        return pd.DataFrame()

    def _fetch_ticker_sync(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """获取单个 ticker 的历史数据"""
        days = {"5d": 5, "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}.get(period, 365)

        if ticker == "BTC-USD":
            return self._fetch_coingecko_history("bitcoin", days)
        else:
            return self._fetch_stooq_history(ticker, days)

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

        # 获取股票/ETF 数据
        for ticker in self.tickers:
            if ticker == "BTC-USD":
                continue  # BTC 单独处理
            data = await loop.run_in_executor(self.executor, self._fetch_stooq, ticker)
            if data['success']:
                # 计算涨跌幅（用 open 和 close 估算）
                change = ((data['price'] - data['open']) / data['open'] * 100) if data['open'] else 0
                prices[ticker] = {
                    "price": round(data['price'], 2),
                    "change": round(change, 2),
                    "volume": data['volume'],
                    "high": round(data['high'], 2),
                    "low": round(data['low'], 2),
                    "date": data['date'] + " (Stooq)",
                    "is_mock": False
                }
            else:
                prices[ticker] = {
                    "price": 0, "change": 0, "volume": 0,
                    "high": 0, "low": 0, "date": now, "is_mock": True
                }

        # 获取 BTC 数据
        btc_data = await loop.run_in_executor(self.executor, self._fetch_coingecko, "bitcoin")
        if btc_data['success']:
            prices["BTC-USD"] = {
                "price": round(btc_data['price'], 2),
                "change": round(btc_data['change'], 2),
                "volume": int(btc_data['volume']),
                "high": round(btc_data['high'], 2),
                "low": round(btc_data['low'], 2),
                "date": now + " (CoinGecko)",
                "is_mock": False
            }
        else:
            prices["BTC-USD"] = {
                "price": 0, "change": 0, "volume": 0,
                "high": 0, "low": 0, "date": now, "is_mock": True
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
        closes = pd.DataFrame()

        for ticker, df in data.items():
            if not df.empty and 'Close' in df.columns:
                closes[ticker] = df["Close"]

        # 如果没有足够数据，生成模拟数据
        if closes.empty or len(closes.columns) < len(self.tickers):
            logger.warning(f"Only got {len(closes.columns)} tickers, using mock for missing")
            np.random.seed(42)
            dates = pd.date_range(end=datetime.now(), periods=252, freq='B')

            mock_params = {
                "SPY": {"mean": 0.10, "vol": 0.15},
                "QQQ": {"mean": 0.15, "vol": 0.22},
                "GLD": {"mean": 0.05, "vol": 0.12},
                "BTC-USD": {"mean": 0.30, "vol": 0.60},
                "TLT": {"mean": 0.02, "vol": 0.10},
            }

            for ticker in self.tickers:
                if ticker not in closes.columns:
                    params = mock_params.get(ticker, {"mean": 0.05, "vol": 0.15})
                    daily_mean = params["mean"] / 252
                    daily_vol = params["vol"] / np.sqrt(252)
                    mock_series = pd.Series(
                        np.random.normal(daily_mean, daily_vol, 252),
                        index=dates,
                        name=ticker
                    )
                    if closes.empty:
                        closes = pd.DataFrame(mock_series)
                    else:
                        closes[ticker] = mock_series

        closes["CASH"] = 1.0
        returns = closes.pct_change().dropna()
        return returns

    def get_ticker_info(self, ticker: str) -> dict:
        """获取 ticker 详细信息"""
        if ticker == "BTC-USD":
            data = self._fetch_coingecko()
        else:
            data = self._fetch_stooq(ticker)

        if data.get('success'):
            return {"name": ticker, "price": data.get('price', 0)}
        return {"name": ticker}
