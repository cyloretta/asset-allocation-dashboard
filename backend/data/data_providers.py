"""
多数据源提供者 - 实现数据源抽象和故障转移
"""
import requests
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from io import StringIO
import logging
import time
from functools import wraps
from threading import Lock

logger = logging.getLogger(__name__)


# ============ 缓存装饰器 ============

class DataCache:
    """线程安全的内存缓存"""

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expire_time)
        self._lock = Lock()
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                if datetime.now().timestamp() < expire_time:
                    logger.debug(f"Cache hit: {key}")
                    return value
                else:
                    del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            expire_time = datetime.now().timestamp() + (ttl or self.ttl)
            self._cache[key] = (value, expire_time)

    def clear(self):
        with self._lock:
            self._cache.clear()


# 全局缓存实例
price_cache = DataCache(ttl_seconds=600)  # 10分钟
history_cache = DataCache(ttl_seconds=7200)  # 2小时


def cached(cache: DataCache, key_func=None):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{kwargs}"

            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 只缓存成功的结果
            if result is not None:
                if isinstance(result, dict) and result.get('success') == False:
                    pass  # 不缓存失败结果
                elif isinstance(result, pd.DataFrame) and result.empty:
                    pass  # 不缓存空数据
                else:
                    cache.set(cache_key, result)

            return result
        return wrapper
    return decorator


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """带指数退避的重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}, retrying in {delay}s")
                        time.sleep(delay)
            logger.error(f"{func.__name__} all retries failed: {last_exception}")
            raise last_exception
        return wrapper
    return decorator


# ============ 数据提供者抽象 ============

class DataProvider(ABC):
    """数据提供者基类"""

    name: str = "base"
    supported_tickers: List[str] = []

    @abstractmethod
    def get_price(self, ticker: str) -> Dict:
        """获取当前价格，返回格式: {price, open, high, low, volume, change, success}"""
        pass

    @abstractmethod
    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        """获取历史数据，返回 DataFrame 含 Date, Open, High, Low, Close, Volume"""
        pass

    def supports(self, ticker: str) -> bool:
        """检查是否支持该 ticker"""
        return ticker in self.supported_tickers or not self.supported_tickers


# ============ Yahoo Finance 提供者 ============

class YahooProvider(DataProvider):
    """Yahoo Finance 数据提供者 (使用 yfinance)"""

    name = "yahoo"

    def __init__(self):
        try:
            import yfinance as yf
            self.yf = yf
            self.available = True
        except ImportError:
            logger.warning("yfinance not installed")
            self.available = False

    @cached(price_cache, key_func=lambda self, ticker: f"yahoo_price:{ticker}")
    def get_price(self, ticker: str) -> Dict:
        if not self.available:
            return {'success': False, 'error': 'yfinance not available'}

        try:
            stock = self.yf.Ticker(ticker)
            info = stock.fast_info
            hist = stock.history(period="2d")

            if hist.empty:
                return {'success': False, 'error': 'no data'}

            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2]['Close'] if len(hist) > 1 else latest['Open']
            change = ((latest['Close'] - prev_close) / prev_close * 100) if prev_close else 0

            return {
                'price': float(latest['Close']),
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'volume': int(latest['Volume']),
                'change': round(change, 2),
                'source': 'Yahoo Finance',
                'success': True
            }
        except Exception as e:
            logger.error(f"Yahoo error for {ticker}: {e}")
            return {'success': False, 'error': str(e)}

    @cached(history_cache, key_func=lambda self, ticker, days: f"yahoo_hist:{ticker}:{days}")
    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        if not self.available:
            return pd.DataFrame()

        try:
            stock = self.yf.Ticker(ticker)
            period = "1y" if days <= 365 else "2y" if days <= 730 else "5y"
            hist = stock.history(period=period)

            if hist.empty:
                return pd.DataFrame()

            hist = hist.reset_index()
            hist['ticker'] = ticker
            hist = hist.rename(columns={'Date': 'date'})
            hist['date'] = pd.to_datetime(hist['date']).dt.tz_localize(None)
            hist.set_index('date', inplace=True)
            return hist[['Open', 'High', 'Low', 'Close', 'Volume', 'ticker']]
        except Exception as e:
            logger.error(f"Yahoo history error for {ticker}: {e}")
            return pd.DataFrame()


# ============ Stooq 提供者 ============

class StooqProvider(DataProvider):
    """Stooq 数据提供者"""

    name = "stooq"

    SYMBOL_MAP = {
        "SPY": "spy.us",
        "QQQ": "qqq.us",
        "GLD": "xauusd",
        "TLT": "tlt.us",
        "IWM": "iwm.us",
        "EEM": "eem.us",
        "VNQ": "vnq.us",
        "DIA": "dia.us",
    }

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    def _get_symbol(self, ticker: str) -> Optional[str]:
        return self.SYMBOL_MAP.get(ticker)

    @cached(price_cache, key_func=lambda self, ticker: f"stooq_price:{ticker}")
    @retry_with_backoff(max_retries=2, base_delay=0.5)
    def get_price(self, ticker: str) -> Dict:
        symbol = self._get_symbol(ticker)
        if not symbol:
            return {'success': False, 'error': 'unsupported ticker'}

        try:
            url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
            resp = requests.get(url, headers=self.HEADERS, timeout=10)

            if resp.status_code != 200 or 'Symbol' not in resp.text:
                return {'success': False, 'error': 'bad response'}

            df = pd.read_csv(StringIO(resp.text))
            if df.empty or 'Close' not in df.columns:
                return {'success': False, 'error': 'no data'}

            row = df.iloc[0]
            volume = row.get('Volume', 0)
            if pd.isna(volume):
                volume = 0

            open_price = float(row['Open'])
            close_price = float(row['Close'])
            change = ((close_price - open_price) / open_price * 100) if open_price else 0

            return {
                'price': close_price,
                'open': open_price,
                'high': float(row['High']),
                'low': float(row['Low']),
                'volume': int(volume),
                'change': round(change, 2),
                'date': str(row.get('Date', '')),
                'source': 'Stooq',
                'success': True
            }
        except Exception as e:
            logger.error(f"Stooq error for {ticker}: {e}")
            return {'success': False, 'error': str(e)}

    @cached(history_cache, key_func=lambda self, ticker, days: f"stooq_hist:{ticker}:{days}")
    @retry_with_backoff(max_retries=2, base_delay=0.5)
    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        symbol = self._get_symbol(ticker)
        if not symbol:
            return pd.DataFrame()

        try:
            # 不指定日期范围，获取全部可用数据
            url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
            resp = requests.get(url, headers=self.HEADERS, timeout=15)
            if resp.status_code != 200 or 'Date' not in resp.text:
                return pd.DataFrame()

            df = pd.read_csv(StringIO(resp.text))
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df['ticker'] = ticker
            return df[['Open', 'High', 'Low', 'Close', 'Volume', 'ticker']]
        except Exception as e:
            logger.error(f"Stooq history error for {ticker}: {e}")
            return pd.DataFrame()


# ============ CoinGecko 提供者 ============

class CoinGeckoProvider(DataProvider):
    """CoinGecko 加密货币数据提供者"""

    name = "coingecko"

    COIN_MAP = {
        "BTC-USD": "bitcoin",
        "ETH-USD": "ethereum",
        "SOL-USD": "solana",
        "BNB-USD": "binancecoin",
    }

    def _get_coin_id(self, ticker: str) -> Optional[str]:
        return self.COIN_MAP.get(ticker)

    @cached(price_cache, key_func=lambda self, ticker: f"cg_price:{ticker}")
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def get_price(self, ticker: str) -> Dict:
        coin_id = self._get_coin_id(ticker)
        if not coin_id:
            return {'success': False, 'error': 'unsupported ticker'}

        try:
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_24hr_high": "true",
                "include_24hr_low": "true"
            }
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code != 200:
                return {'success': False, 'error': f'status {resp.status_code}'}

            data = resp.json().get(coin_id, {})
            if not data:
                return {'success': False, 'error': 'no data'}

            return {
                'price': data.get('usd', 0),
                'open': data.get('usd', 0),  # CoinGecko 没有开盘价
                'high': data.get('usd_24h_high', 0),
                'low': data.get('usd_24h_low', 0),
                'volume': int(data.get('usd_24h_vol', 0)),
                'change': round(data.get('usd_24h_change', 0), 2),
                'source': 'CoinGecko',
                'success': True
            }
        except Exception as e:
            logger.error(f"CoinGecko error for {ticker}: {e}")
            return {'success': False, 'error': str(e)}

    @cached(history_cache, key_func=lambda self, ticker, days: f"cg_hist:{ticker}:{days}")
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        coin_id = self._get_coin_id(ticker)
        if not coin_id:
            return pd.DataFrame()

        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            params = {"vs_currency": "usd", "days": min(days, 365)}  # 免费版最多 365 天
            resp = requests.get(url, params=params, timeout=15)

            if resp.status_code != 200:
                return pd.DataFrame()

            data = resp.json()
            prices = data.get('prices', [])

            if not prices:
                return pd.DataFrame()

            df = pd.DataFrame(prices, columns=['timestamp', 'Close'])
            df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('Date', inplace=True)
            df['Open'] = df['Close']
            df['High'] = df['Close']
            df['Low'] = df['Close']
            df['Volume'] = 0
            df['ticker'] = ticker
            return df[['Open', 'High', 'Low', 'Close', 'Volume', 'ticker']]
        except Exception as e:
            logger.error(f"CoinGecko history error for {ticker}: {e}")
            return pd.DataFrame()


# ============ Binance 提供者 (加密货币备份) ============

class BinanceProvider(DataProvider):
    """Binance 加密货币数据提供者"""

    name = "binance"

    SYMBOL_MAP = {
        "BTC-USD": "BTCUSDT",
        "ETH-USD": "ETHUSDT",
        "SOL-USD": "SOLUSDT",
        "BNB-USD": "BNBUSDT",
    }

    def _get_symbol(self, ticker: str) -> Optional[str]:
        return self.SYMBOL_MAP.get(ticker)

    @cached(price_cache, key_func=lambda self, ticker: f"binance_price:{ticker}")
    def get_price(self, ticker: str) -> Dict:
        symbol = self._get_symbol(ticker)
        if not symbol:
            return {'success': False, 'error': 'unsupported ticker'}

        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr"
            params = {"symbol": symbol}
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code != 200:
                return {'success': False, 'error': f'status {resp.status_code}'}

            data = resp.json()
            return {
                'price': float(data['lastPrice']),
                'open': float(data['openPrice']),
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'volume': float(data['volume']),
                'change': float(data['priceChangePercent']),
                'source': 'Binance',
                'success': True
            }
        except Exception as e:
            logger.error(f"Binance error for {ticker}: {e}")
            return {'success': False, 'error': str(e)}

    @cached(history_cache, key_func=lambda self, ticker, days: f"binance_hist:{ticker}:{days}")
    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        symbol = self._get_symbol(ticker)
        if not symbol:
            return pd.DataFrame()

        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": "1d",
                "limit": min(days, 1000)
            }
            resp = requests.get(url, params=params, timeout=15)

            if resp.status_code != 200:
                return pd.DataFrame()

            data = resp.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('Date', inplace=True)
            df['ticker'] = ticker

            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col])

            return df[['Open', 'High', 'Low', 'Close', 'Volume', 'ticker']]
        except Exception as e:
            logger.error(f"Binance history error for {ticker}: {e}")
            return pd.DataFrame()


# ============ 多数据源调度器 ============

class MultiSourceFetcher:
    """多数据源调度器 - 自动故障转移"""

    def __init__(self):
        # 股票/ETF 数据源优先级 (Stooq 优先，Yahoo 被墙)
        self.equity_providers: List[DataProvider] = [
            StooqProvider(),
            # YahooProvider(),  # 国内网络无法访问
        ]

        # 加密货币数据源优先级
        self.crypto_providers: List[DataProvider] = [
            CoinGeckoProvider(),
            BinanceProvider(),
        ]

        # 模拟数据提供者 (最后备份)
        self.mock_provider = MockDataProvider()

        # 数据源健康状态
        self.health_status: Dict[str, bool] = {}

    def _get_providers(self, ticker: str) -> List[DataProvider]:
        """根据 ticker 类型选择数据源列表"""
        if ticker.endswith("-USD") and ticker != "GLD":
            return self.crypto_providers
        return self.equity_providers

    def get_price(self, ticker: str) -> Dict:
        """获取价格，自动故障转移"""
        providers = self._get_providers(ticker)

        for provider in providers:
            try:
                result = provider.get_price(ticker)
                if result.get('success'):
                    self.health_status[provider.name] = True
                    return result
                else:
                    logger.warning(f"{provider.name} failed for {ticker}: {result.get('error')}")
            except Exception as e:
                logger.error(f"{provider.name} exception for {ticker}: {e}")
                self.health_status[provider.name] = False

        # 所有真实数据源失败，使用模拟数据
        logger.warning(f"All providers failed for {ticker}, using mock data")
        return self.mock_provider.get_price(ticker)

    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        """获取历史数据，自动故障转移"""
        providers = self._get_providers(ticker)

        for provider in providers:
            try:
                df = provider.get_history(ticker, days)
                if not df.empty:
                    self.health_status[provider.name] = True
                    logger.info(f"Got {len(df)} rows for {ticker} from {provider.name}")
                    return df
            except Exception as e:
                logger.error(f"{provider.name} history exception for {ticker}: {e}")
                self.health_status[provider.name] = False

        # 所有真实数据源失败，使用模拟数据
        logger.warning(f"All providers failed for {ticker} history, using mock data")
        return self.mock_provider.get_history(ticker, days)

    def get_health(self) -> Dict[str, bool]:
        """获取所有数据源健康状态"""
        return self.health_status.copy()

    def clear_cache(self):
        """清空所有缓存"""
        price_cache.clear()
        history_cache.clear()
        logger.info("Cache cleared")


# ============ 模拟数据提供者 (最后备份) ============

class MockDataProvider(DataProvider):
    """模拟数据提供者 - 当所有真实数据源都失败时使用"""

    name = "mock"

    # 基于历史统计的模拟参数
    MOCK_PARAMS = {
        "SPY": {"price": 500, "vol": 0.15, "mean_return": 0.10},
        "QQQ": {"price": 420, "vol": 0.22, "mean_return": 0.15},
        "GLD": {"price": 180, "vol": 0.12, "mean_return": 0.05},
        "TLT": {"price": 95, "vol": 0.10, "mean_return": 0.02},
        "BTC-USD": {"price": 65000, "vol": 0.60, "mean_return": 0.30},
    }

    def get_price(self, ticker: str) -> Dict:
        params = self.MOCK_PARAMS.get(ticker, {"price": 100, "vol": 0.15, "mean_return": 0.05})
        base_price = params["price"]
        # 添加一些随机波动
        np.random.seed(int(datetime.now().timestamp()) % 1000)
        noise = np.random.normal(0, 0.02)
        price = base_price * (1 + noise)

        return {
            'price': round(price, 2),
            'open': round(base_price, 2),
            'high': round(price * 1.01, 2),
            'low': round(price * 0.99, 2),
            'volume': 0,
            'change': round(noise * 100, 2),
            'source': 'Mock (估算)',
            'success': True,
            'is_mock': True
        }

    def get_history(self, ticker: str, days: int = 365) -> pd.DataFrame:
        params = self.MOCK_PARAMS.get(ticker, {"price": 100, "vol": 0.15, "mean_return": 0.05})
        np.random.seed(42)  # 固定种子以保持一致性

        dates = pd.date_range(end=datetime.now(), periods=min(days, 252), freq='B')
        daily_vol = params["vol"] / np.sqrt(252)
        daily_mean = params["mean_return"] / 252

        # 生成收益率序列
        returns = np.random.normal(daily_mean, daily_vol, len(dates))
        # 从基准价格反推历史价格
        price_multipliers = np.exp(np.cumsum(returns[::-1]))[::-1]
        prices = params["price"] / price_multipliers[-1] * price_multipliers

        df = pd.DataFrame({
            'Open': prices * 0.999,
            'High': prices * 1.01,
            'Low': prices * 0.99,
            'Close': prices,
            'Volume': 0,
            'ticker': ticker
        }, index=dates)

        return df


# 全局实例
multi_source_fetcher = MultiSourceFetcher()
mock_provider = MockDataProvider()
