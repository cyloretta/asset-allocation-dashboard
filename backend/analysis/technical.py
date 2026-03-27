import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class TechnicalAnalyzer:
    """Calculate technical indicators for assets"""

    @staticmethod
    def calculate_sma(prices: pd.Series, window: int) -> pd.Series:
        """Simple Moving Average"""
        return prices.rolling(window=window).mean()

    @staticmethod
    def calculate_ema(prices: pd.Series, span: int) -> pd.Series:
        """Exponential Moving Average"""
        return prices.ewm(span=span, adjust=False).mean()

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_macd(prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_12 = prices.ewm(span=12, adjust=False).mean()
        ema_26 = prices.ewm(span=26, adjust=False).mean()
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(
        prices: pd.Series, window: int = 20, num_std: float = 2
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        return upper, sma, lower

    @staticmethod
    def calculate_atr(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    @staticmethod
    def calculate_adx(
        high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Average Directional Index (ADX) - 趋势强度指标

        Returns:
            adx: ADX 值 (0-100)
            plus_di: +DI (上涨方向指标)
            minus_di: -DI (下跌方向指标)

        解读:
            ADX < 20: 无趋势/震荡市
            ADX 20-25: 趋势开始形成
            ADX 25-50: 趋势明确
            ADX > 50: 强趋势
            +DI > -DI: 上升趋势
            +DI < -DI: 下降趋势
        """
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)

        # Smoothed averages (Wilder's smoothing)
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)

        # DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(alpha=1/period, adjust=False).mean()

        return adx, plus_di, minus_di

    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On-Balance Volume (OBV) - 能量潮指标

        量价背离检测:
        - 价格上涨但 OBV 下降: 看跌背离
        - 价格下跌但 OBV 上升: 看涨背离
        """
        direction = np.sign(close.diff())
        obv = (direction * volume).cumsum()
        return obv

    @staticmethod
    def calculate_roc(prices: pd.Series, period: int = 10) -> pd.Series:
        """
        Rate of Change (ROC) - 变化率指标

        衡量动量加速/减速
        """
        return ((prices / prices.shift(period)) - 1) * 100

    def analyze_asset(self, df: pd.DataFrame) -> Dict:
        """Run full technical analysis on an asset"""
        if df.empty or len(df) < 30:
            return {"error": "Insufficient data"}

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df.get("Volume", pd.Series([0] * len(df), index=df.index))

        # Calculate indicators
        sma_20 = self.calculate_sma(close, 20)
        sma_50 = self.calculate_sma(close, 50)
        sma_200 = self.calculate_sma(close, 200)
        rsi = self.calculate_rsi(close)
        macd_line, signal_line, histogram = self.calculate_macd(close)
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(close)

        # P1: 新增 ADX 趋势强度指标
        adx, plus_di, minus_di = self.calculate_adx(high, low, close)

        # ATR 波动率
        atr = self.calculate_atr(high, low, close)

        # ROC 动量
        roc = self.calculate_roc(close, 10)

        current_price = close.iloc[-1]
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 20

        # Determine trend
        if len(close) >= 200:
            if current_price > sma_200.iloc[-1]:
                long_term_trend = "bullish"
            else:
                long_term_trend = "bearish"
        else:
            long_term_trend = "unknown"

        if current_price > sma_20.iloc[-1]:
            short_term_trend = "bullish"
        else:
            short_term_trend = "bearish"

        # RSI signals
        if current_rsi > 70:
            rsi_signal = "overbought"
        elif current_rsi < 30:
            rsi_signal = "oversold"
        else:
            rsi_signal = "neutral"

        # MACD signal
        if histogram.iloc[-1] > 0:
            macd_signal = "bullish"
        else:
            macd_signal = "bearish"

        # Bollinger Band position
        bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])

        # P1: ADX 趋势强度判断
        if current_adx > 50:
            trend_strength = "very_strong"
        elif current_adx > 25:
            trend_strength = "strong"
        elif current_adx > 20:
            trend_strength = "moderate"
        else:
            trend_strength = "weak"  # 震荡市，避免趋势策略

        # ADX 方向判断
        adx_direction = "up" if plus_di.iloc[-1] > minus_di.iloc[-1] else "down"

        # ATR 相对值 (相对价格的百分比)
        atr_pct = (atr.iloc[-1] / current_price * 100) if not pd.isna(atr.iloc[-1]) else None

        return {
            "current_price": round(current_price, 2),
            "sma_20": round(sma_20.iloc[-1], 2) if not pd.isna(sma_20.iloc[-1]) else None,
            "sma_50": round(sma_50.iloc[-1], 2) if not pd.isna(sma_50.iloc[-1]) else None,
            "sma_200": round(sma_200.iloc[-1], 2) if len(close) >= 200 and not pd.isna(sma_200.iloc[-1]) else None,
            "rsi": round(current_rsi, 2),
            "rsi_signal": rsi_signal,
            "macd": round(macd_line.iloc[-1], 4) if not pd.isna(macd_line.iloc[-1]) else None,
            "macd_signal": macd_signal,
            "bb_upper": round(bb_upper.iloc[-1], 2) if not pd.isna(bb_upper.iloc[-1]) else None,
            "bb_lower": round(bb_lower.iloc[-1], 2) if not pd.isna(bb_lower.iloc[-1]) else None,
            "bb_position": round(bb_position, 2) if not pd.isna(bb_position) else None,
            # P1: 新增指标
            "adx": round(current_adx, 2),
            "adx_direction": adx_direction,
            "trend_strength": trend_strength,
            "plus_di": round(plus_di.iloc[-1], 2) if not pd.isna(plus_di.iloc[-1]) else None,
            "minus_di": round(minus_di.iloc[-1], 2) if not pd.isna(minus_di.iloc[-1]) else None,
            "atr": round(atr.iloc[-1], 4) if not pd.isna(atr.iloc[-1]) else None,
            "atr_pct": round(atr_pct, 2) if atr_pct else None,
            "roc": round(roc.iloc[-1], 2) if not pd.isna(roc.iloc[-1]) else None,
            # 趋势信息
            "short_term_trend": short_term_trend,
            "long_term_trend": long_term_trend,
            "overall_signal": self._determine_overall_signal_v2(
                short_trend=short_term_trend,
                long_trend=long_term_trend,
                rsi=rsi_signal,
                macd=macd_signal,
                adx=current_adx,
                trend_strength=trend_strength
            )
        }

    def _determine_overall_signal(
        self, short_trend: str, long_trend: str, rsi: str, macd: str
    ) -> str:
        """Determine overall trading signal (legacy)"""
        bullish_count = sum([
            short_trend == "bullish",
            long_trend == "bullish",
            rsi == "oversold",  # Contrarian
            macd == "bullish"
        ])

        if bullish_count >= 3:
            return "strong_buy"
        elif bullish_count >= 2:
            return "buy"
        elif bullish_count <= 1:
            return "sell"
        else:
            return "hold"

    def _determine_overall_signal_v2(
        self,
        short_trend: str,
        long_trend: str,
        rsi: str,
        macd: str,
        adx: float,
        trend_strength: str
    ) -> str:
        """
        增强版信号判断 - 考虑 ADX 趋势强度

        核心逻辑:
        1. ADX < 20 (震荡市): 避免追涨杀跌，偏向均值回归
        2. ADX > 25 (趋势市): 顺势操作
        """
        bullish_count = sum([
            short_trend == "bullish",
            long_trend == "bullish",
            macd == "bullish"
        ])

        bearish_count = sum([
            short_trend == "bearish",
            long_trend == "bearish",
            macd == "bearish"
        ])

        # 震荡市逻辑 (ADX < 20)
        if trend_strength == "weak":
            # 震荡市中，RSI 超买超卖更有效 (逆向操作)
            if rsi == "oversold":
                return "buy"  # 逢低买入
            elif rsi == "overbought":
                return "sell"  # 逢高卖出
            else:
                return "hold"  # 观望

        # 趋势市逻辑 (ADX >= 20)
        # 趋势越强，信号权重越大
        trend_multiplier = 1.0
        if trend_strength == "very_strong":
            trend_multiplier = 1.5
        elif trend_strength == "strong":
            trend_multiplier = 1.2

        # RSI 在趋势市中的作用不同
        # 超买不一定卖，超卖不一定买，要看趋势方向
        if bullish_count >= 3:
            if rsi == "overbought" and trend_strength != "very_strong":
                return "buy"  # 强势中超买可以继续持有
            return "strong_buy"
        elif bullish_count >= 2:
            return "buy"
        elif bearish_count >= 3:
            if rsi == "oversold" and trend_strength != "very_strong":
                return "sell"  # 弱势中超卖可以继续卖出
            return "strong_sell"
        elif bearish_count >= 2:
            return "sell"
        else:
            return "hold"

    def calculate_correlation_matrix(self, returns: pd.DataFrame) -> pd.DataFrame:
        """Calculate correlation matrix for assets"""
        return returns.corr()

    def calculate_volatility(self, returns: pd.Series, annualize: bool = True) -> float:
        """Calculate annualized volatility"""
        vol = returns.std()
        if annualize:
            vol *= np.sqrt(252)
        return vol
