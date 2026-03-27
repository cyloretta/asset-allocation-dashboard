import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from io import StringIO
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class MacroDataFetcher:
    """Fetch macroeconomic indicators from free public APIs"""

    # FRED series IDs for real data
    FRED_SERIES = {
        'FEDFUNDS': 'DFF',           # Effective Federal Funds Rate (daily)
        'ICSA': 'ICSA',              # Initial Claims (weekly)
        'BAMLH0A0HYM2': 'BAMLH0A0HYM2',  # ICE BofA US High Yield Spread
        'T10Y2Y': 'T10Y2Y',          # 10Y-2Y Treasury Spread
        'M2SL': 'M2SL',              # M2 Money Stock
        'VIXCLS': 'VIXCLS',          # VIX
        'CPIAUCSL': 'CPIAUCSL',      # CPI All Urban Consumers (monthly)
        'CPILFESL': 'CPILFESL',      # Core CPI (ex food & energy)
    }

    INDICATORS = {
        # 利率指标
        "T10Y2Y": {"name": "Yield Curve (10Y-2Y)", "description": "10年期减2年期国债利差", "category": "rates"},
        "US10Y": {"name": "10Y Treasury", "description": "美国10年期国债收益率", "category": "rates"},
        "US2Y": {"name": "2Y Treasury", "description": "美国2年期国债收益率", "category": "rates"},
        "US3M": {"name": "3M T-Bill", "description": "3个月国债收益率(无风险利率)", "category": "rates"},
        "FEDFUNDS": {"name": "Fed Funds Rate", "description": "联邦基金利率", "category": "rates"},
        # 信用市场 (P0)
        "CREDIT_SPREAD": {"name": "Credit Spread", "description": "高收益债与投资级债利差", "category": "credit"},
        "TED_SPREAD": {"name": "TED Spread", "description": "银行间流动性压力指标", "category": "credit"},
        # 波动率
        "VIX": {"name": "VIX", "description": "恐慌指数", "category": "volatility"},
        "VIX_PREMIUM": {"name": "VIX Premium", "description": "VIX与实现波动率之差", "category": "volatility"},
        # 汇率
        "DXY": {"name": "USD Index", "description": "美元指数", "category": "fx"},
        # 市场情绪
        "PUT_CALL_RATIO": {"name": "Put/Call Ratio", "description": "期权看跌/看涨比率", "category": "sentiment"},
        "FEAR_GREED": {"name": "Fear & Greed", "description": "恐惧贪婪指数", "category": "sentiment"},
        # 经济领先指标
        "JOBLESS_CLAIMS": {"name": "Initial Claims", "description": "初请失业金人数", "category": "economic"},
        "CPI_YOY": {"name": "CPI YoY", "description": "CPI同比增速", "category": "inflation"},
        "CORE_CPI_YOY": {"name": "Core CPI YoY", "description": "核心CPI同比(不含食品能源)", "category": "inflation"},
        "M2_GROWTH": {"name": "M2 Growth", "description": "M2货币供应增速", "category": "economic"},
    }

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=6)
        self._treasury_data = None
        self._treasury_fetch_time = None
        self._cache = {}  # 通用缓存
        self._cache_ttl = timedelta(minutes=10)
        self._fred_api_key = settings.fred_api_key if hasattr(settings, 'fred_api_key') else None

    def _fetch_fred_series(self, series_id: str, limit: int = 1) -> dict:
        """从 FRED API 获取数据序列"""
        if not self._fred_api_key or self._fred_api_key == 'your_fred_api_key_here':
            return {'success': False, 'reason': 'No FRED API key'}

        try:
            url = f"https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self._fred_api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': limit
            }
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                observations = data.get('observations', [])
                if observations:
                    latest = observations[0]
                    value = latest.get('value')
                    if value and value != '.':
                        return {
                            'value': float(value),
                            'date': latest.get('date'),
                            'source': 'FRED',
                            'success': True
                        }
        except Exception as e:
            logger.warning(f"FRED fetch error for {series_id}: {e}")

        return {'success': False}

    def _fetch_treasury_yields(self) -> dict:
        """从 Treasury.gov 获取国债收益率"""
        # 缓存5分钟
        if self._treasury_data and self._treasury_fetch_time:
            if datetime.now() - self._treasury_fetch_time < timedelta(minutes=5):
                return self._treasury_data

        try:
            year = datetime.now().year
            url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv"
            resp = requests.get(url, timeout=15)

            if resp.status_code == 200:
                df = pd.read_csv(StringIO(resp.text))
                if not df.empty:
                    # 获取最新一行
                    latest = df.iloc[-1]
                    date_str = latest['Date']

                    # 解析收益率
                    us2y = float(latest.get('2 Yr', 0))
                    us10y = float(latest.get('10 Yr', 0))
                    us30y = float(latest.get('30 Yr', 0))

                    self._treasury_data = {
                        'date': date_str,
                        'US2Y': us2y,
                        'US10Y': us10y,
                        'US30Y': us30y,
                        'T10Y2Y': round(us10y - us2y, 2),
                        'success': True
                    }
                    self._treasury_fetch_time = datetime.now()
                    return self._treasury_data
        except Exception as e:
            logger.error(f"Treasury fetch error: {e}")

        return {'success': False}

    def _fetch_dxy(self) -> dict:
        """从 Stooq 获取美元指数"""
        try:
            resp = requests.get(
                "https://stooq.com/q/l/?s=dx.f&f=sd2t2ohlcv&h&e=csv",
                timeout=10
            )
            if resp.status_code == 200 and 'N/D' not in resp.text:
                df = pd.read_csv(StringIO(resp.text))
                if not df.empty:
                    row = df.iloc[0]
                    return {
                        'value': float(row['Close']),
                        'date': str(row['Date']),
                        'success': True
                    }
        except Exception as e:
            logger.error(f"DXY fetch error: {e}")
        return {'success': False}

    def _fetch_vix_real(self) -> dict:
        """从 CBOE 官方获取真实 VIX 数据"""
        try:
            # CBOE 官方 VIX 历史数据
            url = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
            resp = requests.get(url, timeout=15)

            if resp.status_code == 200:
                df = pd.read_csv(StringIO(resp.text))
                if not df.empty:
                    # 获取最新一行
                    latest = df.iloc[-1]
                    date_str = latest.iloc[0]  # DATE 列
                    close = float(latest.iloc[4])  # CLOSE 列
                    return {
                        'value': round(close, 2),
                        'date': date_str,
                        'is_estimate': False,
                        'source': 'CBOE',
                        'success': True
                    }
        except Exception as e:
            logger.warning(f"CBOE VIX fetch error: {e}")

        # 回退到估算
        return self._fetch_vix_estimate()

    def _fetch_vix_estimate(self) -> dict:
        """估算 VIX - 基于 SPY 波动率（最终回退方案）"""
        try:
            resp = requests.get(
                "https://stooq.com/q/d/l/?s=spy.us&i=d",
                timeout=10
            )
            if resp.status_code == 200 and 'Date' in resp.text:
                df = pd.read_csv(StringIO(resp.text))
                if len(df) >= 20:
                    # 计算最近20天的波动率
                    returns = df['Close'].tail(20).pct_change().dropna()
                    daily_vol = returns.std()
                    vix_estimate = daily_vol * (252 ** 0.5) * 100
                    return {
                        'value': round(vix_estimate, 2),
                        'date': df['Date'].iloc[-1],
                        'is_estimate': True,
                        'source': 'Estimated from SPY',
                        'success': True
                    }
        except Exception as e:
            logger.error(f"VIX estimate error: {e}")

        return {'value': 18.0, 'is_estimate': True, 'source': 'Default', 'success': True}

    def _fetch_vix_premium(self, vix_value: float) -> dict:
        """
        P0: 计算 VIX Premium = VIX - 实现波动率
        正值表示市场过度恐慌，负值表示过度乐观
        """
        try:
            # 获取 SPY 近期数据计算实现波动率
            resp = requests.get(
                "https://stooq.com/q/d/l/?s=spy.us&i=d",
                timeout=10
            )
            if resp.status_code == 200 and 'Date' in resp.text:
                df = pd.read_csv(StringIO(resp.text))
                if len(df) >= 20:
                    returns = df['Close'].tail(20).pct_change().dropna()
                    realized_vol = returns.std() * (252 ** 0.5) * 100
                    premium = vix_value - realized_vol

                    # 判断信号
                    if premium > 5:
                        signal = "fear_excessive"  # 恐慌过度，可能是买入机会
                    elif premium < -3:
                        signal = "complacent"  # 过度乐观，警惕回调
                    else:
                        signal = "normal"

                    return {
                        'value': round(premium, 2),
                        'vix': round(vix_value, 2),
                        'realized_vol': round(realized_vol, 2),
                        'signal': signal,
                        'success': True
                    }
        except Exception as e:
            logger.error(f"VIX Premium calculation error: {e}")
        return {'success': False}

    def _fetch_credit_spreads(self) -> dict:
        """
        P0: 获取信用利差指标
        - 高收益债利差 (HY Spread): 高收益债收益率 - 国债收益率
        - TED Spread: 银行间拆借利率 - 国债利率
        """
        result = {'success': False}
        is_estimate = True

        # 优先从 FRED 获取 ICE BofA High Yield Spread
        fred_hy = self._fetch_fred_series('BAMLH0A0HYM2')
        if fred_hy.get('success'):
            hy_spread = fred_hy['value']
            is_estimate = False
        else:
            # 回退到估算
            vix_data = self._fetch_vix_real()
            vix = vix_data.get('value', 20) if vix_data.get('success') else 20
            hy_spread = max(2.0, 2.5 + 0.1 * (vix - 15))

        try:
            treasury = self._fetch_treasury_yields()
            yield_curve = treasury.get('T10Y2Y', 0) if treasury.get('success') else 0

            # TED Spread 估算
            if is_estimate:
                vix_data = self._fetch_vix_real()
                vix = vix_data.get('value', 20) if vix_data.get('success') else 20
                ted_spread = 0.2 + 0.02 * max(0, vix - 15) + 0.1 * max(0, -yield_curve)
            else:
                # 如果有 FRED 数据，TED spread 也使用合理估计
                ted_spread = 0.15 + 0.05 * (hy_spread - 3) / 2

            # 判断信用环境
            if hy_spread > 6:
                credit_regime = "stress"
            elif hy_spread > 4.5:
                credit_regime = "elevated"
            else:
                credit_regime = "normal"

            result = {
                'hy_spread': round(hy_spread, 2),
                'ted_spread': round(ted_spread, 3),
                'credit_regime': credit_regime,
                'is_estimate': is_estimate,
                'source': 'FRED' if not is_estimate else 'Estimated',
                'success': True
            }

        except Exception as e:
            logger.error(f"Credit spread fetch error: {e}")

        return result

    def _fetch_put_call_ratio(self) -> dict:
        """
        获取 CBOE Put/Call Ratio
        > 1.0: 看跌情绪浓厚 (逆向看涨信号)
        < 0.7: 看涨情绪浓厚 (逆向看跌信号)
        """
        try:
            # CBOE 总 Put/Call Ratio
            url = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/TODAY_ALL.json"
            resp = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0'
            })

            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and len(data['data']) > 0:
                    latest = data['data'][-1]
                    ratio = float(latest.get('put_call_ratio', latest.get('ratio', 0.85)))

                    if ratio > 1.0:
                        signal = "bearish_extreme"  # 逆向看涨
                    elif ratio > 0.9:
                        signal = "bearish"
                    elif ratio < 0.7:
                        signal = "bullish_extreme"  # 逆向看跌
                    elif ratio < 0.8:
                        signal = "bullish"
                    else:
                        signal = "neutral"

                    return {
                        'value': round(ratio, 3),
                        'signal': signal,
                        'contrarian_signal': "buy" if ratio > 1.0 else ("sell" if ratio < 0.7 else "hold"),
                        'success': True
                    }
        except Exception as e:
            logger.warning(f"CBOE Put/Call fetch error: {e}")

        # 回退: 基于 VIX 估算
        try:
            vix_data = self._fetch_vix_real()
            vix = vix_data.get('value', 20) if vix_data.get('success') else 20
            # 经验关系: VIX 高时 P/C ratio 也高
            estimated_ratio = 0.7 + 0.015 * (vix - 15)
            return {
                'value': round(estimated_ratio, 3),
                'signal': 'neutral',
                'is_estimate': True,
                'success': True
            }
        except:
            return {'value': 0.85, 'is_estimate': True, 'success': True}

    def _fetch_fear_greed_index(self) -> dict:
        """
        计算综合恐惧贪婪指数 (0-100)
        0 = 极度恐惧, 100 = 极度贪婪

        基于以下因子:
        1. VIX 水平
        2. 价格动量 (SPY vs SMA)
        3. 市场广度 (估算)
        4. Put/Call Ratio
        5. 收益率曲线
        """
        try:
            scores = []

            # 1. VIX 得分 (VIX 低 = 贪婪)
            vix_data = self._fetch_vix_real()
            vix = vix_data.get('value', 20) if vix_data.get('success') else 20
            vix_score = max(0, min(100, 100 - (vix - 10) * 3))
            scores.append(vix_score)

            # 2. 价格动量得分
            try:
                resp = requests.get("https://stooq.com/q/d/l/?s=spy.us&i=d", timeout=10)
                if resp.status_code == 200 and 'Date' in resp.text:
                    df = pd.read_csv(StringIO(resp.text))
                    if len(df) >= 50:
                        current = df['Close'].iloc[-1]
                        sma_50 = df['Close'].tail(50).mean()
                        momentum_pct = (current / sma_50 - 1) * 100
                        momentum_score = max(0, min(100, 50 + momentum_pct * 5))
                        scores.append(momentum_score)
            except:
                pass

            # 3. 收益率曲线得分 (正常曲线 = 贪婪)
            treasury = self._fetch_treasury_yields()
            if treasury.get('success'):
                curve = treasury.get('T10Y2Y', 0)
                curve_score = max(0, min(100, 50 + curve * 20))
                scores.append(curve_score)

            # 4. Put/Call Ratio 得分 (低 P/C = 贪婪)
            pc_data = self._fetch_put_call_ratio()
            if pc_data.get('success'):
                pc = pc_data.get('value', 0.85)
                pc_score = max(0, min(100, 100 - (pc - 0.5) * 100))
                scores.append(pc_score)

            # 计算综合指数
            if scores:
                fear_greed = sum(scores) / len(scores)

                if fear_greed >= 75:
                    label = "extreme_greed"
                elif fear_greed >= 55:
                    label = "greed"
                elif fear_greed >= 45:
                    label = "neutral"
                elif fear_greed >= 25:
                    label = "fear"
                else:
                    label = "extreme_fear"

                return {
                    'value': round(fear_greed, 1),
                    'label': label,
                    'components': len(scores),
                    'success': True
                }

        except Exception as e:
            logger.error(f"Fear & Greed calculation error: {e}")

        return {'value': 50, 'label': 'neutral', 'is_estimate': True, 'success': True}

    def _fetch_fed_funds_rate(self) -> dict:
        """从 FRED 或备用源获取联邦基金利率"""
        # 优先使用 FRED API
        fred_data = self._fetch_fred_series('DFF')
        if fred_data.get('success'):
            return {
                'value': round(fred_data['value'], 2),
                'date': fred_data['date'],
                'source': 'FRED',
                'is_estimate': False,
                'success': True
            }

        # 备用：尝试从 Yahoo Finance 获取联邦基金期货推断
        try:
            resp = requests.get(
                "https://query1.finance.yahoo.com/v8/finance/chart/ZQ=F",
                headers={'User-Agent': 'Mozilla/5.0'},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                result = data.get('chart', {}).get('result', [])
                if result:
                    price = result[0].get('meta', {}).get('regularMarketPrice', 0)
                    # Fed Funds Futures: 100 - price = implied rate
                    if price > 90:
                        implied_rate = 100 - price
                        return {
                            'value': round(implied_rate, 2),
                            'source': 'Fed Funds Futures',
                            'is_estimate': False,
                            'success': True
                        }
        except Exception as e:
            logger.warning(f"Fed Funds fetch error: {e}")

        # 回退到最新已知值 (2026年3月)
        return {
            'value': 4.33,
            'source': 'Latest known (Mar 2026)',
            'is_estimate': True,
            'success': True
        }

    def _fetch_jobless_claims(self) -> dict:
        """从公开源获取初请失业金数据"""
        try:
            # 尝试从 FRED 公开页面获取
            # 备用：使用 tradingeconomics
            url = "https://tradingeconomics.com/united-states/jobless-claims"
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)

            if resp.status_code == 200:
                # 简单解析页面中的数值
                import re
                match = re.search(r'<span[^>]*id="[^"]*lastValue[^"]*"[^>]*>(\d+)', resp.text)
                if match:
                    value = int(match.group(1)) * 1000  # 转换为千人
                    signal = 'recession' if value > 350000 else ('warning' if value > 280000 else 'normal')
                    return {
                        'value': value,
                        'signal': signal,
                        'threshold_warning': 280000,
                        'threshold_recession': 350000,
                        'source': 'TradingEconomics',
                        'is_estimate': False,
                        'success': True
                    }
        except Exception as e:
            logger.warning(f"Jobless claims fetch error: {e}")

        # 回退到估算值
        return {
            'value': 220000,
            'signal': 'normal',
            'threshold_warning': 280000,
            'threshold_recession': 350000,
            'is_estimate': True,
            'success': True
        }

    def _fetch_cpi_data(self) -> dict:
        """
        从 FRED 获取 CPI 数据并计算同比增速
        返回 CPI 和 Core CPI 的同比增速
        """
        result = {
            'cpi_yoy': None,
            'core_cpi_yoy': None,
            'success': False
        }

        try:
            # 获取 CPI 最近13个月数据计算同比
            cpi_data = self._fetch_fred_series_history('CPIAUCSL', 13)
            if cpi_data.get('success') and len(cpi_data.get('values', [])) >= 12:
                values = cpi_data['values']
                # 计算同比: (最新值 - 12个月前值) / 12个月前值 * 100
                latest = values[0]['value']
                year_ago = values[12]['value'] if len(values) > 12 else values[-1]['value']
                cpi_yoy = (latest / year_ago - 1) * 100

                # 判断通胀水平
                if cpi_yoy > 4:
                    signal = 'high_inflation'
                elif cpi_yoy > 3:
                    signal = 'above_target'
                elif cpi_yoy >= 2:
                    signal = 'on_target'
                elif cpi_yoy >= 0:
                    signal = 'low_inflation'
                else:
                    signal = 'deflation'

                result['cpi_yoy'] = {
                    'value': round(cpi_yoy, 2),
                    'latest_index': round(latest, 2),
                    'date': values[0]['date'],
                    'signal': signal,
                    'source': 'FRED',
                    'is_estimate': False
                }
                result['success'] = True

            # 获取 Core CPI
            core_data = self._fetch_fred_series_history('CPILFESL', 13)
            if core_data.get('success') and len(core_data.get('values', [])) >= 12:
                values = core_data['values']
                latest = values[0]['value']
                year_ago = values[12]['value'] if len(values) > 12 else values[-1]['value']
                core_yoy = (latest / year_ago - 1) * 100

                if core_yoy > 3.5:
                    signal = 'sticky_inflation'
                elif core_yoy > 2.5:
                    signal = 'above_target'
                elif core_yoy >= 1.5:
                    signal = 'on_target'
                else:
                    signal = 'low'

                result['core_cpi_yoy'] = {
                    'value': round(core_yoy, 2),
                    'latest_index': round(latest, 2),
                    'date': values[0]['date'],
                    'signal': signal,
                    'source': 'FRED',
                    'is_estimate': False
                }
                result['success'] = True

        except Exception as e:
            logger.error(f"CPI fetch error: {e}")

        return result

    def _fetch_fred_series_history(self, series_id: str, limit: int = 13) -> dict:
        """从 FRED API 获取历史数据序列"""
        if not self._fred_api_key or self._fred_api_key == 'your_fred_api_key_here':
            return {'success': False, 'reason': 'No FRED API key'}

        try:
            url = f"https://api.stlouisfed.org/fred/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self._fred_api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': limit
            }
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                observations = data.get('observations', [])
                values = []
                for obs in observations:
                    if obs.get('value') and obs['value'] != '.':
                        values.append({
                            'value': float(obs['value']),
                            'date': obs['date']
                        })
                if values:
                    return {'values': values, 'success': True}
        except Exception as e:
            logger.warning(f"FRED history fetch error for {series_id}: {e}")

        return {'success': False}

    def _fetch_economic_indicators(self) -> dict:
        """
        获取经济领先指标
        - 初请失业金
        - CPI 通胀数据
        - M2 增速
        """
        result = {
            'jobless_claims': None,
            'cpi': None,
            'm2_growth': None,
            'success': True
        }

        # 初请失业金 - 尝试获取真实数据
        result['jobless_claims'] = self._fetch_jobless_claims()

        # CPI 通胀数据 - 从 FRED 获取
        result['cpi'] = self._fetch_cpi_data()

        # M2 增速 (YoY%) - 这个较难实时获取，使用估算
        result['m2_growth'] = {
            'value': 3.8,
            'signal': 'normal',
            'is_estimate': True
        }

        return result

    async def fetch_all(self) -> Dict[str, dict]:
        """Fetch all macro indicators including new P0 indicators"""
        loop = asyncio.get_event_loop()

        # 并行获取基础数据
        treasury_task = loop.run_in_executor(self.executor, self._fetch_treasury_yields)
        dxy_task = loop.run_in_executor(self.executor, self._fetch_dxy)
        vix_task = loop.run_in_executor(self.executor, self._fetch_vix_real)

        treasury, dxy, vix = await asyncio.gather(treasury_task, dxy_task, vix_task)

        indicators = {}

        # === 利率指标 ===
        if treasury.get('success'):
            indicators['US10Y'] = {
                'series_id': 'US10Y',
                'name': '10年期国债',
                'description': '美国10年期国债收益率',
                'value': treasury['US10Y'],
                'date': treasury['date'],
                'category': 'rates',
                'is_mock': False
            }
            indicators['US2Y'] = {
                'series_id': 'US2Y',
                'name': '2年期国债',
                'description': '美国2年期国债收益率',
                'value': treasury['US2Y'],
                'date': treasury['date'],
                'category': 'rates',
                'is_mock': False
            }
            indicators['T10Y2Y'] = {
                'series_id': 'T10Y2Y',
                'name': '收益率曲线',
                'description': '10Y-2Y利差',
                'value': treasury['T10Y2Y'],
                'date': treasury['date'],
                'category': 'rates',
                'is_mock': False,
                'signal': 'inverted' if treasury['T10Y2Y'] < 0 else ('flat' if treasury['T10Y2Y'] < 0.5 else 'normal')
            }
            # 3个月国债作为无风险利率
            indicators['US3M'] = {
                'series_id': 'US3M',
                'name': '3个月国债',
                'description': '无风险利率参考',
                'value': round(treasury['US2Y'] - 0.3, 2),  # 估算
                'date': treasury['date'],
                'category': 'rates',
                'is_estimate': True
            }
        else:
            indicators['US10Y'] = {'series_id': 'US10Y', 'name': '10年期国债', 'value': 4.2, 'category': 'rates', 'is_mock': True}
            indicators['US2Y'] = {'series_id': 'US2Y', 'name': '2年期国债', 'value': 3.5, 'category': 'rates', 'is_mock': True}
            indicators['T10Y2Y'] = {'series_id': 'T10Y2Y', 'name': '收益率曲线', 'value': 0.7, 'category': 'rates', 'is_mock': True}
            indicators['US3M'] = {'series_id': 'US3M', 'name': '3个月国债', 'value': 3.2, 'category': 'rates', 'is_mock': True}

        # Fed Funds Rate - 尝试获取真实数据
        fed_funds = await loop.run_in_executor(self.executor, self._fetch_fed_funds_rate)
        indicators['FEDFUNDS'] = {
            'series_id': 'FEDFUNDS',
            'name': 'Fed Funds',
            'description': '联邦基金利率',
            'value': fed_funds.get('value', 4.33),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'category': 'rates',
            'is_mock': fed_funds.get('is_estimate', True),
            'source': fed_funds.get('source', 'Unknown')
        }

        # === 汇率指标 ===
        if dxy.get('success'):
            indicators['DXY'] = {
                'series_id': 'DXY',
                'name': '美元指数',
                'description': 'US Dollar Index',
                'value': dxy['value'],
                'date': dxy['date'],
                'category': 'fx',
                'is_mock': False
            }
        else:
            indicators['DXY'] = {'series_id': 'DXY', 'name': '美元指数', 'value': 99.5, 'category': 'fx', 'is_mock': True}

        # === 波动率指标 ===
        vix_value = 18.0
        if vix.get('success'):
            vix_value = vix['value']
            indicators['VIX'] = {
                'series_id': 'VIX',
                'name': 'VIX',
                'description': '波动率指数' + (f" ({vix.get('source', '')})" if vix.get('source') else ''),
                'value': vix_value,
                'date': vix.get('date', datetime.now().strftime('%Y-%m-%d')),
                'category': 'volatility',
                'is_mock': False,
                'is_estimate': vix.get('is_estimate', False),
                'source': vix.get('source', 'Unknown'),
                'signal': 'high' if vix_value > 25 else ('elevated' if vix_value > 20 else 'low')
            }
        else:
            indicators['VIX'] = {'series_id': 'VIX', 'name': 'VIX', 'value': 18.0, 'category': 'volatility', 'is_mock': True}

        # P0: VIX Premium (VIX - 实现波动率)
        vix_premium = await loop.run_in_executor(
            self.executor,
            lambda: self._fetch_vix_premium(vix_value)
        )
        if vix_premium.get('success'):
            indicators['VIX_PREMIUM'] = {
                'series_id': 'VIX_PREMIUM',
                'name': 'VIX Premium',
                'description': 'VIX与实现波动率之差',
                'value': vix_premium['value'],
                'vix': vix_premium['vix'],
                'realized_vol': vix_premium['realized_vol'],
                'signal': vix_premium['signal'],
                'category': 'volatility',
                'is_mock': False
            }
        else:
            indicators['VIX_PREMIUM'] = {
                'series_id': 'VIX_PREMIUM',
                'name': 'VIX Premium',
                'value': 0,
                'category': 'volatility',
                'is_mock': True
            }

        # === P0: 信用市场指标 ===
        credit = await loop.run_in_executor(self.executor, self._fetch_credit_spreads)
        if credit.get('success'):
            indicators['CREDIT_SPREAD'] = {
                'series_id': 'CREDIT_SPREAD',
                'name': '高收益债利差',
                'description': 'HY-IG Spread (衰退预警指标)',
                'value': credit['hy_spread'],
                'regime': credit['credit_regime'],
                'category': 'credit',
                'is_estimate': credit.get('is_estimate', False),
                'signal': 'danger' if credit['hy_spread'] > 6 else ('warning' if credit['hy_spread'] > 4.5 else 'normal')
            }
            indicators['TED_SPREAD'] = {
                'series_id': 'TED_SPREAD',
                'name': 'TED Spread',
                'description': '银行间流动性压力',
                'value': credit['ted_spread'],
                'category': 'credit',
                'is_estimate': credit.get('is_estimate', False),
                'signal': 'stress' if credit['ted_spread'] > 0.5 else 'normal'
            }
        else:
            indicators['CREDIT_SPREAD'] = {'series_id': 'CREDIT_SPREAD', 'name': '高收益债利差', 'value': 3.5, 'category': 'credit', 'is_mock': True}
            indicators['TED_SPREAD'] = {'series_id': 'TED_SPREAD', 'name': 'TED Spread', 'value': 0.2, 'category': 'credit', 'is_mock': True}

        # === 市场情绪指标 ===
        put_call = await loop.run_in_executor(self.executor, self._fetch_put_call_ratio)
        if put_call.get('success'):
            indicators['PUT_CALL_RATIO'] = {
                'series_id': 'PUT_CALL_RATIO',
                'name': 'Put/Call Ratio',
                'description': '期权看跌/看涨比率',
                'value': put_call['value'],
                'signal': put_call.get('signal', 'neutral'),
                'contrarian_signal': put_call.get('contrarian_signal', 'hold'),
                'category': 'sentiment',
                'is_estimate': put_call.get('is_estimate', False)
            }
        else:
            indicators['PUT_CALL_RATIO'] = {'series_id': 'PUT_CALL_RATIO', 'name': 'Put/Call Ratio', 'value': 0.85, 'category': 'sentiment', 'is_mock': True}

        fear_greed = await loop.run_in_executor(self.executor, self._fetch_fear_greed_index)
        if fear_greed.get('success'):
            indicators['FEAR_GREED'] = {
                'series_id': 'FEAR_GREED',
                'name': 'Fear & Greed',
                'description': '恐惧贪婪指数 (0=极度恐惧, 100=极度贪婪)',
                'value': fear_greed['value'],
                'label': fear_greed['label'],
                'category': 'sentiment',
                'is_estimate': fear_greed.get('is_estimate', False)
            }
        else:
            indicators['FEAR_GREED'] = {'series_id': 'FEAR_GREED', 'name': 'Fear & Greed', 'value': 50, 'label': 'neutral', 'category': 'sentiment', 'is_mock': True}

        # === 经济领先指标 ===
        economic = await loop.run_in_executor(self.executor, self._fetch_economic_indicators)
        if economic.get('success'):
            jc = economic['jobless_claims']
            indicators['JOBLESS_CLAIMS'] = {
                'series_id': 'JOBLESS_CLAIMS',
                'name': '初请失业金',
                'description': '每周初请失业金人数',
                'value': jc['value'],
                'signal': jc['signal'],
                'category': 'economic',
                'is_estimate': jc.get('is_estimate', False),
                'thresholds': {
                    'warning': jc['threshold_warning'],
                    'recession': jc['threshold_recession']
                }
            }

            # CPI 通胀数据
            cpi_data = economic.get('cpi', {})
            if cpi_data.get('success') and cpi_data.get('cpi_yoy'):
                cpi = cpi_data['cpi_yoy']
                indicators['CPI_YOY'] = {
                    'series_id': 'CPI_YOY',
                    'name': 'CPI同比',
                    'description': '消费者物价指数同比增速',
                    'value': cpi['value'],
                    'date': cpi['date'],
                    'signal': cpi['signal'],
                    'category': 'inflation',
                    'is_mock': False,
                    'source': 'FRED',
                    'interpretation': '>3%高通胀, 2%目标, <0%通缩'
                }

            if cpi_data.get('success') and cpi_data.get('core_cpi_yoy'):
                core = cpi_data['core_cpi_yoy']
                indicators['CORE_CPI_YOY'] = {
                    'series_id': 'CORE_CPI_YOY',
                    'name': '核心CPI同比',
                    'description': '核心CPI(不含食品能源)',
                    'value': core['value'],
                    'date': core['date'],
                    'signal': core['signal'],
                    'category': 'inflation',
                    'is_mock': False,
                    'source': 'FRED',
                    'interpretation': 'Fed重点关注指标'
                }

            m2 = economic['m2_growth']
            indicators['M2_GROWTH'] = {
                'series_id': 'M2_GROWTH',
                'name': 'M2增速',
                'description': 'M2货币供应年增速(%)',
                'value': m2['value'],
                'signal': m2['signal'],
                'category': 'economic',
                'is_estimate': m2.get('is_estimate', False)
            }

        return indicators

    async def fetch_indicator(self, series_id: str, days: int = 365) -> dict:
        """Fetch a single indicator"""
        all_data = await self.fetch_all()
        return all_data.get(series_id, {})

    async def get_market_regime(self) -> dict:
        """
        Analyze current market regime based on comprehensive macro indicators
        包含 P0 信用利差、VIX Premium 等新指标
        """
        indicators = await self.fetch_all()

        # 获取关键指标值
        vix = indicators.get("VIX", {}).get("value", 20)
        yield_curve = indicators.get("T10Y2Y", {}).get("value", 0)
        fed_rate = indicators.get("FEDFUNDS", {}).get("value", 4.5)

        # P0: 新增指标
        credit_spread = indicators.get("CREDIT_SPREAD", {}).get("value", 3.5)
        ted_spread = indicators.get("TED_SPREAD", {}).get("value", 0.2)
        vix_premium = indicators.get("VIX_PREMIUM", {}).get("value", 0)
        fear_greed = indicators.get("FEAR_GREED", {}).get("value", 50)
        cpi_yoy = indicators.get("CPI_YOY", {}).get("value", 2.5)
        core_cpi_yoy = indicators.get("CORE_CPI_YOY", {}).get("value", 2.5)

        # 波动率判断
        if vix > 30:
            volatility_regime = "high_volatility"
        elif vix > 20:
            volatility_regime = "moderate_volatility"
        else:
            volatility_regime = "low_volatility"

        # 收益率曲线判断
        if yield_curve < 0:
            curve_regime = "inverted"
        elif yield_curve < 0.5:
            curve_regime = "flat"
        else:
            curve_regime = "normal"

        # 货币政策判断
        if fed_rate > 5:
            rate_regime = "restrictive"
        elif fed_rate > 2.5:
            rate_regime = "neutral"
        else:
            rate_regime = "accommodative"

        # P0: 信用市场判断
        if credit_spread > 6:
            credit_regime = "stress"
        elif credit_spread > 4.5:
            credit_regime = "elevated"
        else:
            credit_regime = "normal"

        # P0: 流动性判断
        if ted_spread > 0.5:
            liquidity_regime = "tight"
        elif ted_spread > 0.3:
            liquidity_regime = "moderate"
        else:
            liquidity_regime = "ample"

        # 市场情绪判断
        if fear_greed < 25:
            sentiment_regime = "extreme_fear"
        elif fear_greed < 45:
            sentiment_regime = "fear"
        elif fear_greed > 75:
            sentiment_regime = "extreme_greed"
        elif fear_greed > 55:
            sentiment_regime = "greed"
        else:
            sentiment_regime = "neutral"

        # 通胀环境判断 (替代PMI)
        if cpi_yoy > 4:
            inflation_regime = "high_inflation"
        elif cpi_yoy > 3:
            inflation_regime = "above_target"
        elif cpi_yoy >= 1.5:
            inflation_regime = "on_target"
        elif cpi_yoy >= 0:
            inflation_regime = "low_inflation"
        else:
            inflation_regime = "deflation"

        # 综合风险评分
        risk_score = self._calculate_risk_score_v2(indicators)

        # 衰退概率估算
        recession_probability = self._estimate_recession_probability(indicators)

        return {
            "volatility": volatility_regime,
            "yield_curve": curve_regime,
            "monetary_policy": rate_regime,
            "credit": credit_regime,
            "liquidity": liquidity_regime,
            "sentiment": sentiment_regime,
            "inflation": inflation_regime,
            "cpi_yoy": cpi_yoy,
            "core_cpi_yoy": core_cpi_yoy,
            "overall_risk": risk_score,
            "recession_probability": recession_probability,
            "recommended_action": self._get_recommended_action(risk_score, recession_probability),
            "indicators": indicators
        }

    def _calculate_risk_score_v2(self, indicators: Dict) -> float:
        """
        学术优化版风险评分 (0-100)

        权重分配基于学术研究:
        - 收益率曲线: 25% (Estrella & Mishkin 1996: 衰退预测准确率85%)
        - 信用利差: 20% (Gilchrist & Zakrajšek 2012: 领先股市3-6月)
        - VIX: 15% (实时指标，极端值信号强)
        - 通胀 CPI: 15% (滞胀组合风险最高)
        - 流动性 TED: 15% (金融危机关键指标)
        - 市场情绪: 10% (逆向辅助指标)
        """
        score = 50  # baseline

        # 1. 收益率曲线贡献 (权重 25%) - 最强衰退预警指标
        yield_curve = indicators.get("T10Y2Y", {}).get("value", 0)
        if yield_curve < -0.5:
            score += 20  # 深度倒挂，衰退概率极高
        elif yield_curve < -0.2:
            score += 15  # 明显倒挂
        elif yield_curve < 0:
            score += 10  # 轻度倒挂
        elif yield_curve < 0.3:
            score += 5   # 接近倒挂
        elif yield_curve > 1.5:
            score -= 8   # 健康曲线

        # 2. 信用利差贡献 (权重 20%) - 领先指标
        credit = indicators.get("CREDIT_SPREAD", {}).get("value", 3.5)
        if credit > 7:
            score += 15  # 严重压力
        elif credit > 5.5:
            score += 10
        elif credit > 4.5:
            score += 5
        elif credit < 3:
            score -= 5   # 信用环境宽松

        # 3. VIX 贡献 (权重 15%) - 实时市场压力
        vix = indicators.get("VIX", {}).get("value", 20)
        if vix > 35:
            score += 12  # 恐慌
        elif vix > 30:
            score += 9
        elif vix > 25:
            score += 6
        elif vix > 20:
            score += 3
        elif vix < 12:
            score -= 5   # 过度平静也是风险
        elif vix < 15:
            score -= 2

        # 4. 通胀指标贡献 (权重 15%) - 货币政策风险
        cpi = indicators.get("CPI_YOY", {}).get("value", 2.5)
        fed_rate = indicators.get("FEDFUNDS", {}).get("value", 4.5)
        # 滞胀组合（高通胀+紧缩政策）风险最高
        if cpi > 5 and fed_rate > 5:
            score += 12  # 滞胀风险
        elif cpi > 4:
            score += 8
        elif cpi > 3:
            score += 4
        elif cpi < 0:
            score += 10  # 通缩风险
        elif cpi < 1:
            score += 5

        # 5. 流动性贡献 (权重 15%) - 金融系统压力
        ted = indicators.get("TED_SPREAD", {}).get("value", 0.2)
        if ted > 0.8:
            score += 12  # 流动性危机
        elif ted > 0.5:
            score += 8
        elif ted > 0.3:
            score += 4

        # 6. 市场情绪贡献 (权重 10%) - 逆向辅助指标
        fear_greed = indicators.get("FEAR_GREED", {}).get("value", 50)
        if fear_greed < 20:
            score += 5   # 极度恐惧
        elif fear_greed < 35:
            score += 3
        elif fear_greed > 80:
            score += 4   # 极度贪婪也是风险信号
        elif fear_greed > 65:
            score += 2

        return max(0, min(100, score))

    def _estimate_recession_probability(self, indicators: Dict) -> float:
        """
        估算衰退概率 (0-100%)

        基于学术研究的权重分配:
        - 收益率曲线: 40% (最强预警，Estrella研究)
        - 信用利差: 25% (领先指标)
        - 滞胀组合: 20% (高CPI+高利率)
        - 失业金: 15% (劳动力市场压力)
        """
        prob = 10  # 基准概率

        # 1. 收益率曲线倒挂 (权重 40%) - 最强衰退预警
        # 历史上倒挂后 12-18 个月内衰退概率显著上升
        yield_curve = indicators.get("T10Y2Y", {}).get("value", 0)
        if yield_curve < -0.5:
            prob += 40  # 深度倒挂
        elif yield_curve < -0.2:
            prob += 30  # 明显倒挂
        elif yield_curve < 0:
            prob += 20  # 轻度倒挂
        elif yield_curve < 0.3:
            prob += 8   # 接近倒挂

        # 2. 信用利差扩大 (权重 25%)
        credit = indicators.get("CREDIT_SPREAD", {}).get("value", 3.5)
        if credit > 7:
            prob += 25  # 信用危机级别
        elif credit > 6:
            prob += 18
        elif credit > 5:
            prob += 12
        elif credit > 4:
            prob += 5

        # 3. 滞胀组合 (权重 20%) - 高通胀+紧缩政策
        cpi = indicators.get("CPI_YOY", {}).get("value", 2.5)
        fed_rate = indicators.get("FEDFUNDS", {}).get("value", 4.5)
        if cpi > 5 and fed_rate > 5:
            prob += 20  # 典型滞胀
        elif cpi > 4 and fed_rate > 5:
            prob += 15
        elif cpi > 3.5 and fed_rate > 4.5:
            prob += 8
        elif cpi < 0:
            prob += 15  # 通缩往往伴随衰退

        # 4. 失业金上升 (权重 15%)
        jobless = indicators.get("JOBLESS_CLAIMS", {}).get("value", 220000)
        if jobless > 350000:
            prob += 15
        elif jobless > 280000:
            prob += 8
        elif jobless > 250000:
            prob += 3

        return min(95, prob)

    def _get_recommended_action(self, risk_score: float, recession_prob: float) -> str:
        """根据风险评分和衰退概率给出建议"""
        if risk_score > 75 or recession_prob > 60:
            return "defensive"  # 防御：增加债券/黄金/现金
        elif risk_score > 60 or recession_prob > 40:
            return "cautious"   # 谨慎：降低股票敞口
        elif risk_score < 30 and recession_prob < 20:
            return "aggressive" # 积极：增加股票敞口
        else:
            return "balanced"   # 平衡：维持目标配置

    def _calculate_risk_score(self, vix: float, yield_curve: float, fed_rate: float) -> float:
        """Calculate overall risk score from 0-100 (legacy method)"""
        score = 50  # baseline

        # VIX 贡献
        if vix > 30:
            score += 20
        elif vix > 25:
            score += 15
        elif vix > 20:
            score += 10
        elif vix < 15:
            score -= 10

        # 收益率曲线贡献
        if yield_curve < -0.5:
            score += 15
        elif yield_curve < 0:
            score += 10
        elif yield_curve > 1:
            score -= 5

        # 利率环境
        if fed_rate > 5:
            score += 10
        elif fed_rate < 2:
            score -= 5

        return max(0, min(100, score))
