from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
from pydantic import BaseModel
from collections import defaultdict
from datetime import datetime
import logging
import time

from config import get_settings
from database import init_db, get_db, async_session
from database import (
    get_latest_prices, get_market_data, get_macro_indicators,
    get_latest_analysis, get_analysis_history,
    get_latest_strategy, get_strategy_history,
    get_recent_news, save_strategy,
    # P2: AI 预测追踪
    save_ai_predictions, evaluate_predictions, get_ai_accuracy_stats,
    # AI 分析缓存（用于策略优化）
    save_ai_analysis_cache, get_latest_ai_analysis_cache, get_ai_analysis_status,
    # 策略快照
    save_strategy_snapshot, get_strategy_snapshot, get_strategy_snapshots,
    get_snapshot_metrics_trend, compare_snapshots,
    # 用户配置
    get_user_config
)
from data import MarketDataFetcher, MacroDataFetcher, NewsFetcher, cleanup_http_client
from api import user_config_router
from analysis import AIAnalyst, TechnicalAnalyzer
from strategy import PortfolioOptimizer, RiskMetrics, Backtester
from scheduler import SchedulerManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
scheduler_manager = SchedulerManager()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """简单的内存限流中间件"""

    def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.requests: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # 跳过健康检查和静态资源
        if request.url.path in ["/api/health", "/", "/favicon.ico"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        minute_ago = now - 60

        # 清理过期记录
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if ts > minute_ago
        ]

        # 检查限流
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )

        # 突发限制：1秒内最多 burst_limit 个请求
        second_ago = now - 1
        recent_requests = [ts for ts in self.requests[client_ip] if ts > second_ago]
        if len(recent_requests) >= self.burst_limit:
            logger.warning(f"Burst limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."}
            )

        # 记录请求
        self.requests[client_ip].append(now)

        return await call_next(request)


async def validate_fred_api_key() -> bool:
    """启动时验证 FRED API 密钥"""
    if not settings.fred_api_key or settings.fred_api_key == 'your_fred_api_key_here':
        logger.warning("FRED API key not configured - macro data will use fallback sources")
        return False

    try:
        import requests
        resp = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={
                'series_id': 'DFF',
                'api_key': settings.fred_api_key,
                'file_type': 'json',
                'limit': 1
            },
            timeout=10
        )
        if resp.status_code == 200:
            logger.info("FRED API key validated successfully")
            return True
        else:
            logger.warning(f"FRED API key validation failed: HTTP {resp.status_code}")
            return False
    except Exception as e:
        logger.warning(f"FRED API key validation error: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await validate_fred_api_key()
    scheduler_manager.start()
    logger.info("Application started")
    yield
    # Shutdown
    scheduler_manager.stop()
    await cleanup_http_client()
    logger.info("Application stopped")


app = FastAPI(
    title="Asset Allocation Dashboard API",
    description="API for dynamic asset allocation strategy based on macro analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - 限制允许的方法和头部
# 生产环境会通过环境变量 ALLOWED_ORIGINS 配置
import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

# Include routers
app.include_router(user_config_router)

# 速率限制中间件：每分钟60请求，突发限制10请求/秒
app.add_middleware(RateLimitMiddleware, requests_per_minute=60, burst_limit=10)

# Initialize services
market_fetcher = MarketDataFetcher()
macro_fetcher = MacroDataFetcher()
news_fetcher = NewsFetcher()
ai_analyst = AIAnalyst()
technical_analyzer = TechnicalAnalyzer()
optimizer = PortfolioOptimizer()
risk_metrics = RiskMetrics()
backtester = Backtester()


# Request/Response Models
class AllocationRequest(BaseModel):
    method: str = "max_sharpe_cvar"  # max_sharpe, min_volatility, risk_parity, composite, risk_aware, max_sharpe_cvar
    use_ai_adjustments: bool = True
    max_drawdown: Optional[float] = None  # 最大回撤阈值 (0-1)
    target_sharpe: Optional[float] = None  # 目标夏普比率
    use_unified_risk: bool = True  # 使用统一风险框架


class BacktestRequest(BaseModel):
    allocation: Dict[str, float]
    rebalance_freq: str = "monthly"
    start_value: float = 100000


# API Endpoints

@app.get("/")
async def root():
    return {"status": "ok", "message": "Asset Allocation Dashboard API"}


@app.get("/api/health")
async def health_check():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Market Data Endpoints

@app.get("/api/market/prices")
async def get_market_prices():
    """Get current prices for all assets"""
    try:
        prices = await market_fetcher.get_current_prices()
        return {"data": prices}
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/history/{ticker}")
async def get_ticker_history(ticker: str, period: str = "1y"):
    """Get historical data for a ticker"""
    try:
        df = await market_fetcher.fetch_ticker(ticker, period)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        return {
            "ticker": ticker,
            "data": [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(row["Open"], 2),
                    "high": round(row["High"], 2),
                    "low": round(row["Low"], 2),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"])
                }
                for idx, row in df.iterrows()
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/technical/{ticker}")
async def get_technical_analysis(ticker: str):
    """Get technical analysis for a ticker"""
    try:
        df = await market_fetcher.fetch_ticker(ticker, "1y")
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        analysis = technical_analyzer.analyze_asset(df)
        return {"ticker": ticker, "analysis": analysis}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in technical analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Macro Data Endpoints

@app.get("/api/macro/indicators")
async def get_macro_data():
    """Get all macro economic indicators"""
    try:
        indicators = await macro_fetcher.fetch_all()
        return {"data": indicators}
    except Exception as e:
        logger.error(f"Error fetching macro data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/macro/regime")
async def get_market_regime():
    """Get current market regime analysis"""
    try:
        regime = await macro_fetcher.get_market_regime()
        return {"data": regime}
    except Exception as e:
        logger.error(f"Error analyzing regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# AI Analysis Endpoints

@app.get("/api/analysis/latest")
async def get_latest_ai_analysis():
    """Get the latest AI analysis (from cache)"""
    async with async_session() as session:
        # 优先从 AIAnalysisCache 获取完整的分析数据（不限时间）
        cached = await get_latest_ai_analysis_cache(session, max_age_minutes=99999)
        if cached:
            # 计算分析时间距今多久
            from datetime import datetime
            age_minutes = (datetime.utcnow() - cached.created_at).total_seconds() / 60
            return {
                "data": {
                    **cached.raw_response,  # 包含完整的 AI 分析结果
                    "cached_at": cached.created_at.isoformat(),
                    "age_minutes": round(age_minutes, 1),
                    "is_valid_for_optimize": age_minutes <= 60  # 是否在 60 分钟有效期内
                }
            }
        return {"data": None, "message": "No analysis available. Please run AI analysis first."}


@app.get("/api/analysis/status")
async def get_analysis_status():
    """获取 AI 分析缓存状态（用于策略优化前检查）"""
    try:
        async with async_session() as session:
            status = await get_ai_analysis_status(session, max_age_minutes=60)
        return {"data": status}
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analysis/run")
async def run_ai_analysis(background_tasks: BackgroundTasks):
    """Trigger a new AI analysis"""
    try:
        # Gather data
        market_data = await market_fetcher.get_current_prices()
        macro_data = await macro_fetcher.fetch_all()
        news_summary = await news_fetcher.get_news_summary()

        # P1: 获取技术指标
        technical_data = {}
        tickers = [t for t in settings.assets.keys() if t != "CASH"]
        for ticker in tickers:
            try:
                df = await market_fetcher.fetch_ticker(ticker, "1y")
                if not df.empty and len(df) >= 30:
                    technical_data[ticker] = technical_analyzer.analyze_asset(df)
            except Exception as e:
                logger.warning(f"Failed to get technical data for {ticker}: {e}")

        # P4: 获取历史预测准确率用于反馈循环
        accuracy_stats = None
        async with async_session() as session:
            accuracy_stats = await get_ai_accuracy_stats(session)

        # Run analysis with technical data and accuracy feedback
        analysis = await ai_analyst.analyze(
            market_data, macro_data, news_summary, technical_data, accuracy_stats
        )

        # P2: 保存 AI 预测记录用于准确率追踪
        adjustments = analysis.get("allocation_advice", {}).get("adjustments", {})
        if adjustments:
            async with async_session() as session:
                await save_ai_predictions(
                    session,
                    adjustments=adjustments,
                    prices=market_data,
                    model=analysis.get("model", "unknown")
                )

        # 保存到 AI 分析缓存（供策略优化使用）
        async with async_session() as session:
            await save_ai_analysis_cache(
                session,
                adjustments=adjustments,
                overall_risk_score=analysis.get("overall_risk_score", 50),
                market_summary=analysis.get("summary", ""),
                allocation_advice=analysis.get("allocation_advice", {}),
                raw_response=analysis
            )
            logger.info("AI analysis cached for strategy optimization")

        return {"data": analysis}
    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/accuracy")
async def get_ai_accuracy():
    """获取 AI 预测准确率统计（P2）"""
    try:
        # 先评估到期的预测
        prices = await market_fetcher.get_current_prices()
        async with async_session() as session:
            eval_result = await evaluate_predictions(session, prices)
            stats = await get_ai_accuracy_stats(session)

        return {
            "data": {
                **stats,
                "recent_evaluation": eval_result
            }
        }
    except Exception as e:
        logger.error(f"Error getting AI accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/history")
async def get_analysis_history_endpoint(days: int = 30):
    """Get historical AI analyses"""
    async with async_session() as session:
        analyses = await get_analysis_history(session, days)
        return {
            "data": [
                {
                    "id": a.id,
                    "date": a.date.isoformat(),
                    "type": a.analysis_type,
                    "risk_score": a.risk_score
                }
                for a in analyses
            ]
        }


# Strategy Endpoints

@app.get("/api/strategy/current")
async def get_current_strategy():
    """Get the current portfolio strategy"""
    async with async_session() as session:
        strategy = await get_latest_strategy(session)
        if strategy:
            return {
                "data": {
                    "id": strategy.id,
                    "date": strategy.date.isoformat(),
                    "allocation": strategy.allocation,
                    "expected_return": strategy.expected_return,
                    "expected_volatility": strategy.expected_volatility,
                    "sharpe_ratio": strategy.sharpe_ratio,
                    "max_drawdown": strategy.max_drawdown,
                    "reasoning": strategy.reasoning,
                    # 方案C数据
                    "plan_c": {
                        "rounded_allocation": strategy.rounded_allocation,
                        "rebalance_advice": strategy.rebalance_advice,
                        "rebalance_count": strategy.rebalance_count
                    } if strategy.rounded_allocation else None,
                    "risk_context": strategy.risk_context
                }
            }
        return {"data": None, "message": "No strategy available"}


@app.post("/api/strategy/optimize")
async def optimize_portfolio(request: AllocationRequest):
    """Run portfolio optimization"""
    # 验证优化方法
    allowed_methods = ["max_sharpe", "min_volatility", "risk_parity", "composite", "risk_aware", "max_sharpe_cvar"]
    if request.method not in allowed_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid method: {request.method}. Allowed: {', '.join(allowed_methods)}"
        )

    try:
        # Get historical returns
        returns = await market_fetcher.get_historical_returns()

        # Get macro risk score for unified risk framework
        macro_risk_score = None
        ai_risk_score = None
        if request.use_unified_risk:
            macro_regime = await macro_fetcher.get_market_regime()
            macro_risk_score = macro_regime.get("overall_risk")

        # Get AI adjustments from cache (不再实时调用 AI)
        ai_adjustments = None
        if request.use_ai_adjustments:
            async with async_session() as session:
                # 检查是否有 60 分钟内的 AI 分析缓存
                cached_analysis = await get_latest_ai_analysis_cache(session, max_age_minutes=60)

                if not cached_analysis:
                    # 无有效缓存，提示用户先运行 AI 分析
                    raise HTTPException(
                        status_code=400,
                        detail="请先运行 AI 分析。AI 分析结果需要在 60 分钟内才能用于策略优化。"
                    )

                # 使用缓存的 AI 分析结果
                ai_adjustments = cached_analysis.adjustments
                logger.info(f"Using cached AI analysis from {cached_analysis.created_at}")

                # 获取 AI 风险评分
                if request.use_unified_risk:
                    ai_risk_score = cached_analysis.overall_risk_score

        # Optimize with unified risk context
        result = optimizer.optimize(
            returns,
            ai_adjustments=ai_adjustments,
            method=request.method,
            max_drawdown=request.max_drawdown,
            target_sharpe=request.target_sharpe,
            macro_risk_score=macro_risk_score,
            ai_risk_score=ai_risk_score
        )

        # 方案C: 获取当前配置，计算取整目标和调仓建议
        async with async_session() as session:
            current_strategy = await get_latest_strategy(session)
            current_allocation = current_strategy.allocation if current_strategy else {}

            # 取整到5%
            raw_allocation = result["allocation"]
            rounded_allocation = optimizer.round_allocation(raw_allocation, step=0.05)

            # P1: 生成调仓建议（含交易成本分析）
            rebalance_advice = optimizer.generate_rebalance_advice(
                current_allocation,
                rounded_allocation,
                threshold=0.05,
                expected_improvement=0.0,  # TODO: 计算预期改善
                portfolio_value=100000
            )

            # 统计需要调仓的资产数量（排除 _summary）
            rebalance_count = sum(
                1 for k, v in rebalance_advice.items()
                if k != "_summary" and v.get("action") == "调仓"
            )

            # 添加方案C数据到结果
            result["plan_c"] = {
                "current_allocation": current_allocation,
                "raw_allocation": raw_allocation,
                "rounded_allocation": rounded_allocation,
                "rebalance_advice": rebalance_advice,
                "rebalance_count": rebalance_count,
                "threshold": 0.05
            }

            # 生成结构化的策略理由
            reasoning_data = {
                "method": request.method,
                "method_name": {
                    "max_sharpe": "最大夏普比率",
                    "min_volatility": "最小波动率",
                    "risk_parity": "风险平价",
                    "composite": "综合优化",
                    "risk_aware": "风险感知优化",
                    "max_sharpe_cvar": "夏普最大化(CVaR约束)"
                }.get(request.method, request.method),
                "ai_adjustments": ai_adjustments,
                "correlation_regime": result.get("correlation_regime"),
                "risk_context": result.get("risk_context"),  # 统一风险上下文
                "out_of_sample": result.get("out_of_sample"),
                "train_days": result.get("train_days"),
                "test_days": result.get("test_days")
            }
            import json
            reasoning = json.dumps(reasoning_data, ensure_ascii=False)
            await save_strategy(
                session,
                allocation=result["allocation"],
                metrics=result["metrics"],
                reasoning=reasoning,
                plan_c_data=result["plan_c"],  # 保存方案C数据
                risk_context=result.get("risk_context")  # 保存统一风险上下文
            )

            # 保存策略快照（完整记录优化时的市场状态）
            market_prices = await market_fetcher.get_current_prices()
            macro_regime_snapshot = await macro_fetcher.get_market_regime()

            ai_analysis_id = None
            if request.use_ai_adjustments and cached_analysis:
                ai_analysis_id = cached_analysis.id

            await save_strategy_snapshot(
                session,
                optimization_method=request.method,
                max_drawdown_limit=request.max_drawdown or settings.max_drawdown,
                use_ai_adjustments=request.use_ai_adjustments,
                market_snapshot=market_prices,
                macro_snapshot=macro_regime_snapshot,
                allocation=result["allocation"],
                rounded_allocation=rounded_allocation,
                metrics=result["metrics"],
                ai_analysis_id=ai_analysis_id
            )
            logger.info("Strategy snapshot saved")

        return {"data": result}
    except Exception as e:
        logger.error(f"Error optimizing portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/correlation")
async def get_correlation_status():
    """获取资产相关性状态（P2: 危机检测）"""
    try:
        returns = await market_fetcher.get_historical_returns()
        logger.info(f"Got returns: {returns.shape}")

        regime = RiskMetrics.detect_correlation_regime(returns)
        logger.info(f"Got regime: {regime}")

        # 计算相关性矩阵（处理 NaN 值）
        import pandas as pd
        corr_matrix = returns.corr()
        correlation_matrix = {
            row: {
                col: round(float(corr_matrix.loc[row, col]), 4)
                if not pd.isna(corr_matrix.loc[row, col]) else 0.0
                for col in corr_matrix.columns
            }
            for row in corr_matrix.index
        }

        return {
            "data": {
                "regime": regime,
                "correlation_matrix": correlation_matrix
            }
        }
    except Exception as e:
        import traceback
        logger.error(f"Error getting correlation status: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/efficient-frontier")
async def get_efficient_frontier():
    """Get efficient frontier data"""
    try:
        returns = await market_fetcher.get_historical_returns()
        frontier = optimizer.get_efficient_frontier(returns)
        return {"data": frontier}
    except Exception as e:
        logger.error(f"Error calculating frontier: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/rolling-validation")
async def get_rolling_validation(
    train_window: int = 180,
    test_window: int = 60,
    step: int = 30
):
    """
    P2: 滚动窗口验证策略稳健性

    Args:
        train_window: 训练窗口天数 (默认180)
        test_window: 测试窗口天数 (默认60)
        step: 滚动步长天数 (默认30)
    """
    try:
        returns = await market_fetcher.get_historical_returns(period="1y")
        result = optimizer.rolling_validation(
            returns,
            method="max_sharpe_cvar",
            train_window=train_window,
            test_window=test_window,
            step=step,
            max_drawdown=settings.max_drawdown
        )
        return {"data": result}
    except Exception as e:
        logger.error(f"Error in rolling validation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/history")
async def get_strategy_history_endpoint(days: int = 90):
    """Get historical strategies"""
    async with async_session() as session:
        strategies = await get_strategy_history(session, days)
        return {
            "data": [
                {
                    "id": s.id,
                    "date": s.date.isoformat(),
                    "allocation": s.allocation,
                    "sharpe_ratio": s.sharpe_ratio
                }
                for s in strategies
            ]
        }


# Strategy Snapshot Endpoints

@app.get("/api/strategy/snapshots")
async def get_snapshots(days: int = 90, limit: int = 100):
    """获取策略快照列表"""
    async with async_session() as session:
        snapshots = await get_strategy_snapshots(session, days=days, limit=limit)
        return {
            "data": [
                {
                    "id": s.id,
                    "created_at": s.created_at.isoformat(),
                    "method": s.optimization_method,
                    "max_drawdown_limit": s.max_drawdown_limit,
                    "use_ai": bool(s.use_ai_adjustments),
                    "metrics": s.metrics
                }
                for s in snapshots
            ]
        }


@app.get("/api/strategy/snapshots/{snapshot_id}")
async def get_snapshot_detail(snapshot_id: int):
    """获取单个策略快照详情"""
    async with async_session() as session:
        snapshot = await get_strategy_snapshot(session, snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="快照不存在")

        return {
            "data": {
                "id": snapshot.id,
                "created_at": snapshot.created_at.isoformat(),
                "method": snapshot.optimization_method,
                "max_drawdown_limit": snapshot.max_drawdown_limit,
                "use_ai": bool(snapshot.use_ai_adjustments),
                "allocation": snapshot.allocation,
                "rounded_allocation": snapshot.rounded_allocation,
                "metrics": snapshot.metrics,
                "market_snapshot": snapshot.market_snapshot,
                "macro_snapshot": snapshot.macro_snapshot,
                "backtest_result": snapshot.backtest_result
            }
        }


@app.get("/api/strategy/history/trend")
async def get_history_trend(days: int = 90):
    """获取策略指标趋势数据"""
    try:
        async with async_session() as session:
            trend_data = await get_snapshot_metrics_trend(session, days=days)

            if not trend_data:
                return {"data": [], "metrics_summary": None}

            # 计算指标摘要
            sharpes = [d["sharpe"] for d in trend_data if d["sharpe"] is not None]
            mdds = [d["max_drawdown"] for d in trend_data if d["max_drawdown"] is not None]
            returns = [d["return"] for d in trend_data if d["return"] is not None]

            def calc_trend(values):
                if len(values) < 2:
                    return "stable"
                recent = values[-3:] if len(values) >= 3 else values
                earlier = values[:3]
                if sum(recent) / len(recent) > sum(earlier) / len(earlier) * 1.05:
                    return "up"
                elif sum(recent) / len(recent) < sum(earlier) / len(earlier) * 0.95:
                    return "down"
                return "stable"

            metrics_summary = {
                "sharpe": {
                    "min": round(min(sharpes), 4) if sharpes else None,
                    "max": round(max(sharpes), 4) if sharpes else None,
                    "avg": round(sum(sharpes) / len(sharpes), 4) if sharpes else None,
                    "trend": calc_trend(sharpes) if sharpes else "stable"
                },
                "max_drawdown": {
                    "min": round(min(mdds), 4) if mdds else None,
                    "max": round(max(mdds), 4) if mdds else None,
                    "avg": round(sum(mdds) / len(mdds), 4) if mdds else None,
                    "trend": calc_trend(mdds) if mdds else "stable"
                },
                "return": {
                    "min": round(min(returns), 4) if returns else None,
                    "max": round(max(returns), 4) if returns else None,
                    "avg": round(sum(returns) / len(returns), 4) if returns else None,
                    "trend": calc_trend(returns) if returns else "stable"
                }
            }

            return {
                "data": trend_data,
                "metrics_summary": metrics_summary
            }
    except Exception as e:
        logger.error(f"Error getting history trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/strategy/history/allocation-changes")
async def get_allocation_changes(days: int = 90):
    """获取配置变化详情"""
    try:
        async with async_session() as session:
            snapshots = await get_strategy_snapshots(session, days=days, limit=50)

            if len(snapshots) < 2:
                return {"data": [], "summary": {"total_changes": 0}}

            changes = []
            prev_allocation = None

            for s in reversed(snapshots):  # 按时间正序
                current = s.rounded_allocation or s.allocation
                if prev_allocation:
                    change_detail = {}
                    for asset in set(current.keys()) | set(prev_allocation.keys()):
                        curr_val = current.get(asset, 0)
                        prev_val = prev_allocation.get(asset, 0)
                        diff = curr_val - prev_val
                        if abs(diff) > 0.01:
                            change_detail[asset] = {
                                "from": round(prev_val, 4),
                                "to": round(curr_val, 4),
                                "change": round(diff, 4)
                            }

                    if change_detail:
                        changes.append({
                            "date": s.created_at.isoformat(),
                            "method": s.optimization_method,
                            "changes": change_detail
                        })

                prev_allocation = current

            return {
                "data": changes[-20:],  # 最近 20 次变化
                "summary": {
                    "total_changes": len(changes),
                    "period_days": days
                }
            }
    except Exception as e:
        logger.error(f"Error getting allocation changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SnapshotCompareRequest(BaseModel):
    snapshot_ids: List[int]


@app.post("/api/strategy/history/compare")
async def compare_snapshots_endpoint(request: SnapshotCompareRequest):
    """对比多个策略快照"""
    if len(request.snapshot_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要 2 个快照进行对比")
    if len(request.snapshot_ids) > 5:
        raise HTTPException(status_code=400, detail="最多支持对比 5 个快照")

    try:
        async with async_session() as session:
            results = await compare_snapshots(session, request.snapshot_ids)

            if len(results) < 2:
                raise HTTPException(status_code=404, detail="找不到足够的快照")

            return {"data": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Backtest Endpoints

@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRequest):
    """Run backtest for an allocation"""
    try:
        returns = await market_fetcher.get_historical_returns()
        result = backtester.backtest_strategy(
            returns,
            request.allocation,
            rebalance_freq=request.rebalance_freq,
            start_value=request.start_value
        )
        return {"data": result}
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backtest/monte-carlo")
async def run_monte_carlo(request: BacktestRequest):
    """Run Monte Carlo simulation"""
    try:
        returns = await market_fetcher.get_historical_returns()
        result = backtester.monte_carlo_simulation(
            returns,
            request.allocation,
            n_simulations=500,
            start_value=request.start_value
        )
        return {"data": result}
    except Exception as e:
        logger.error(f"Error running simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# News Endpoints

@app.get("/api/news/recent")
async def get_news(hours: int = 24):
    """Get recent market news"""
    try:
        news = await news_fetcher.get_market_news(hours)
        return {
            "data": [
                {
                    "title": n["title"],
                    "title_zh": n.get("title_zh", n["title"]),
                    "source": n["source"],
                    "url": n["url"],
                    "published_at": n["published_at"],  # Already ISO string
                    "summary": n["summary"][:200],
                    "relevance_score": n["relevance_score"]
                }
                for n in news[:20]
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Endpoints

@app.post("/api/system/update")
async def trigger_manual_update():
    """Manually trigger full data update and analysis"""
    try:
        result = await scheduler_manager.run_manual_update()
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"Error in manual update: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/config")
async def get_system_config():
    """Get system configuration"""
    return {
        "assets": settings.assets,
        "max_drawdown": settings.max_drawdown,
        "risk_free_rate": settings.risk_free_rate,
        "update_schedule": {
            "hour": settings.daily_update_hour,
            "minute": settings.daily_update_minute
        }
    }


def check_data_freshness(data_date: datetime, max_age_hours: int = 24) -> dict:
    """检查数据新鲜度"""
    from datetime import timezone
    now = datetime.now()
    if data_date.tzinfo:
        now = datetime.now(timezone.utc)
    age_hours = (now - data_date).total_seconds() / 3600
    is_stale = age_hours > max_age_hours
    return {
        "is_stale": is_stale,
        "age_hours": round(age_hours, 1),
        "max_age_hours": max_age_hours,
        "warning": f"数据已过期 {round(age_hours)}小时" if is_stale else None
    }


# Dashboard Summary Endpoint

@app.get("/api/dashboard/summary")
async def get_dashboard_summary():
    """Get complete dashboard summary"""
    try:
        # Gather all data in parallel
        prices = await market_fetcher.get_current_prices()
        macro = await macro_fetcher.get_market_regime()

        async with async_session() as session:
            strategy = await get_latest_strategy(session)
            analysis = await get_latest_analysis(session)

        # 数据新鲜度检查
        freshness = {}
        warnings = []

        if strategy:
            strategy_freshness = check_data_freshness(strategy.date, max_age_hours=24)
            freshness["strategy"] = strategy_freshness
            if strategy_freshness["is_stale"]:
                warnings.append(f"策略数据已过期: {strategy_freshness['warning']}")

        if analysis:
            analysis_freshness = check_data_freshness(analysis.date, max_age_hours=24)
            freshness["analysis"] = analysis_freshness
            if analysis_freshness["is_stale"]:
                warnings.append(f"AI分析已过期: {analysis_freshness['warning']}")

        # 检查市场数据新鲜度
        market_stale_count = 0
        for ticker, data in prices.items():
            if isinstance(data, dict) and data.get("date"):
                try:
                    # 解析日期（处理不同格式）
                    date_str = data["date"].split(" ")[0]  # 移除来源标注
                    data_date = datetime.strptime(date_str, "%Y-%m-%d")
                    market_freshness = check_data_freshness(data_date, max_age_hours=48)
                    if market_freshness["is_stale"]:
                        market_stale_count += 1
                except:
                    pass

        if market_stale_count > 0:
            warnings.append(f"{market_stale_count}个资产的市场数据可能过期")
            freshness["market"] = {"stale_assets": market_stale_count}

        # 统一返回格式：包装在 data 字段中
        return {
            "data": {
                "market": prices,
                "macro": macro,
                "strategy": {
                    "allocation": strategy.allocation,
                    "expected_return": strategy.expected_return,
                    "expected_volatility": strategy.expected_volatility,
                    "sharpe_ratio": strategy.sharpe_ratio,
                    "max_drawdown": strategy.max_drawdown,
                    "reasoning": strategy.reasoning,
                    "date": strategy.date.isoformat(),
                    # 方案C数据
                    "plan_c": {
                        "rounded_allocation": strategy.rounded_allocation,
                        "rebalance_advice": strategy.rebalance_advice,
                        "rebalance_count": strategy.rebalance_count
                    } if strategy.rounded_allocation else None,
                    "risk_context": strategy.risk_context
                } if strategy else None,
                "analysis": {
                    "risk_score": analysis.risk_score,
                    "content": analysis.content,
                    "date": analysis.date.isoformat()
                } if analysis else None,
                "freshness": freshness if freshness else None,
                "warnings": warnings if warnings else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
