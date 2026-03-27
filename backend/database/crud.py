from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from typing import Optional, List
import json
import asyncio

from .models import Base, MarketData, MacroIndicator, AIAnalysis, StrategyRecord, NewsEvent, AIPrediction, AIAnalysisCache, UserConfig, StrategySnapshot
from config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# 数据库写操作锁，防止并发写入冲突（SQLite 限制）
_db_write_lock = asyncio.Lock()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        yield session


# Market Data CRUD
async def save_market_data(session: AsyncSession, ticker: str, data: dict):
    async with _db_write_lock:
        record = MarketData(
            ticker=ticker,
            date=data["date"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data["volume"]
        )
        session.add(record)
        await session.commit()
        return record


async def get_market_data(session: AsyncSession, ticker: str, days: int = 365) -> List[MarketData]:
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(MarketData)
        .where(MarketData.ticker == ticker, MarketData.date >= since)
        .order_by(MarketData.date)
    )
    return result.scalars().all()


async def get_latest_prices(session: AsyncSession) -> dict:
    tickers = list(get_settings().assets.keys())
    tickers.remove("CASH")
    prices = {}
    for ticker in tickers:
        result = await session.execute(
            select(MarketData)
            .where(MarketData.ticker == ticker)
            .order_by(desc(MarketData.date))
            .limit(1)
        )
        record = result.scalar_one_or_none()
        if record:
            prices[ticker] = {
                "price": record.close,
                "date": record.date.isoformat()
            }
    return prices


# Macro Indicator CRUD
async def save_macro_indicator(session: AsyncSession, name: str, date: datetime, value: float, source: str):
    async with _db_write_lock:
        record = MacroIndicator(
            indicator_name=name,
            date=date,
            value=value,
            source=source
        )
        session.add(record)
        await session.commit()
        return record


async def get_macro_indicators(session: AsyncSession, days: int = 90) -> List[MacroIndicator]:
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(MacroIndicator)
        .where(MacroIndicator.date >= since)
        .order_by(MacroIndicator.date)
    )
    return result.scalars().all()


# AI Analysis CRUD
async def save_ai_analysis(session: AsyncSession, analysis_type: str, content: str,
                           risk_score: float, key_factors: list, recommendations: list):
    async with _db_write_lock:
        record = AIAnalysis(
            date=datetime.now(),
            analysis_type=analysis_type,
            content=content,
            risk_score=risk_score,
            key_factors=key_factors,
            recommendations=recommendations
        )
        session.add(record)
        await session.commit()
        return record


async def get_latest_analysis(session: AsyncSession) -> Optional[AIAnalysis]:
    result = await session.execute(
        select(AIAnalysis)
        .order_by(desc(AIAnalysis.date))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_analysis_history(session: AsyncSession, days: int = 30) -> List[AIAnalysis]:
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(AIAnalysis)
        .where(AIAnalysis.date >= since)
        .order_by(desc(AIAnalysis.date))
    )
    return result.scalars().all()


# AI Analysis Cache CRUD (用于策略优化)
async def save_ai_analysis_cache(
    session: AsyncSession,
    adjustments: dict,
    overall_risk_score: float,
    market_summary: str,
    allocation_advice: dict,
    raw_response: dict
):
    """保存 AI 分析结果到缓存"""
    async with _db_write_lock:
        record = AIAnalysisCache(
            adjustments=adjustments,
            overall_risk_score=overall_risk_score,
            market_summary=market_summary,
            allocation_advice=allocation_advice,
            raw_response=raw_response
        )
        session.add(record)
        await session.commit()
        return record


async def get_latest_ai_analysis_cache(
    session: AsyncSession,
    max_age_minutes: int = 60
) -> Optional[AIAnalysisCache]:
    """获取最近的 AI 分析缓存（在有效期内）"""
    # 使用 UTC 时间保持一致性
    since = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    result = await session.execute(
        select(AIAnalysisCache)
        .where(AIAnalysisCache.created_at >= since)
        .order_by(desc(AIAnalysisCache.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_ai_analysis_status(session: AsyncSession, max_age_minutes: int = 60) -> dict:
    """获取 AI 分析状态（是否有有效缓存）"""
    # 获取最新的缓存记录（不限时间）
    result = await session.execute(
        select(AIAnalysisCache)
        .order_by(desc(AIAnalysisCache.created_at))
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    if not latest:
        return {
            "has_valid_cache": False,
            "last_analysis_time": None,
            "age_minutes": None,
            "is_expired": True,
            "message": "尚未运行 AI 分析"
        }

    # 使用 UTC 时间保持一致性（数据库存储的是 UTC）
    age = datetime.utcnow() - latest.created_at
    age_minutes = age.total_seconds() / 60
    is_expired = age_minutes > max_age_minutes

    return {
        "has_valid_cache": not is_expired,
        "last_analysis_time": latest.created_at.isoformat(),
        "age_minutes": round(age_minutes, 1),
        "is_expired": is_expired,
        "max_age_minutes": max_age_minutes,
        "message": "AI 分析有效" if not is_expired else f"AI 分析已过期（{round(age_minutes)}分钟前）"
    }


# Strategy Record CRUD
async def save_strategy(
    session: AsyncSession,
    allocation: dict,
    metrics: dict,
    reasoning: str,
    plan_c_data: Optional[dict] = None,
    risk_context: Optional[dict] = None
):
    """
    保存策略记录，包含方案C数据

    Args:
        allocation: 原始优化配置
        metrics: 性能指标
        reasoning: 策略理由
        plan_c_data: 方案C数据 {rounded_allocation, rebalance_advice, rebalance_count}
        risk_context: 统一风险上下文
    """
    async with _db_write_lock:
        record = StrategyRecord(
            date=datetime.now(),
            allocation=allocation,
            expected_return=metrics.get("expected_return", 0),
            expected_volatility=metrics.get("expected_volatility", 0),
            sharpe_ratio=metrics.get("sharpe_ratio", 0),
            max_drawdown=metrics.get("max_drawdown", 0),
            reasoning=reasoning,
            # 方案C数据
            rounded_allocation=plan_c_data.get("rounded_allocation") if plan_c_data else None,
            rebalance_advice=plan_c_data.get("rebalance_advice") if plan_c_data else None,
            rebalance_count=plan_c_data.get("rebalance_count") if plan_c_data else None,
            risk_context=risk_context
        )
        session.add(record)
        await session.commit()
        return record


async def get_latest_strategy(session: AsyncSession) -> Optional[StrategyRecord]:
    result = await session.execute(
        select(StrategyRecord)
        .order_by(desc(StrategyRecord.date))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_strategy_history(session: AsyncSession, days: int = 90) -> List[StrategyRecord]:
    since = datetime.now() - timedelta(days=days)
    result = await session.execute(
        select(StrategyRecord)
        .where(StrategyRecord.date >= since)
        .order_by(desc(StrategyRecord.date))
    )
    return result.scalars().all()


# News Event CRUD
async def save_news_event(session: AsyncSession, news: dict):
    async with _db_write_lock:
        record = NewsEvent(
            title=news["title"],
            source=news["source"],
            url=news["url"],
            published_at=news.get("published_at", datetime.now()),
            summary=news.get("summary", ""),
            sentiment=news.get("sentiment", 0),
            relevance_score=news.get("relevance_score", 0.5)
        )
        session.add(record)
        await session.commit()
        return record


async def get_recent_news(session: AsyncSession, hours: int = 24) -> List[NewsEvent]:
    since = datetime.now() - timedelta(hours=hours)
    result = await session.execute(
        select(NewsEvent)
        .where(NewsEvent.published_at >= since)
        .order_by(desc(NewsEvent.published_at))
    )
    return result.scalars().all()


# P2: AI Prediction CRUD
async def save_ai_predictions(
    session: AsyncSession,
    adjustments: dict,
    prices: dict,
    model: str,
    evaluation_days: int = 10
):
    """保存 AI 预测记录"""
    async with _db_write_lock:
        now = datetime.now()
        eval_date = now + timedelta(days=evaluation_days)

        records = []
        for asset, adjustment in adjustments.items():
            # 解析调整值
            if isinstance(adjustment, str):
                direction = adjustment
                adj_value = {"increase": 0.05, "maintain": 0.0, "decrease": -0.05}.get(adjustment, 0)
            else:
                adj_value = float(adjustment)
                direction = "increase" if adj_value > 0 else "decrease" if adj_value < 0 else "maintain"

            price = prices.get(asset, {}).get("price", 0)

            record = AIPrediction(
                prediction_date=now,
                evaluation_date=eval_date,
                asset=asset,
                direction=direction,
                adjustment_value=adj_value,
                price_at_prediction=price,
                model=model
            )
            session.add(record)
            records.append(record)

        await session.commit()
        return records


async def evaluate_predictions(session: AsyncSession, prices: dict) -> dict:
    """评估到期的 AI 预测"""
    now = datetime.now()

    # 获取需要评估的预测（评估日期已过但尚未评估）
    result = await session.execute(
        select(AIPrediction)
        .where(
            AIPrediction.evaluation_date <= now,
            AIPrediction.prediction_correct.is_(None)
        )
    )
    pending = result.scalars().all()

    evaluated = 0
    correct = 0

    async with _db_write_lock:
        for pred in pending:
            current_price = prices.get(pred.asset, {}).get("price")
            if current_price and pred.price_at_prediction > 0:
                # 计算实际收益率
                actual_return = (current_price - pred.price_at_prediction) / pred.price_at_prediction

                # 判断预测是否正确
                if pred.direction == "increase":
                    is_correct = actual_return > 0
                elif pred.direction == "decrease":
                    is_correct = actual_return < 0
                else:  # maintain
                    is_correct = abs(actual_return) < 0.03  # 波动小于3%视为正确

                pred.price_at_evaluation = current_price
                pred.actual_return = actual_return
                pred.prediction_correct = 1 if is_correct else 0

                evaluated += 1
                if is_correct:
                    correct += 1

        await session.commit()

    return {
        "evaluated": evaluated,
        "correct": correct,
        "accuracy": round(correct / evaluated, 4) if evaluated > 0 else None
    }


async def get_ai_accuracy_stats(session: AsyncSession, days: int = 30) -> dict:
    """获取 AI 预测准确率统计"""
    since = datetime.now() - timedelta(days=days)

    # 获取已评估的预测
    result = await session.execute(
        select(AIPrediction)
        .where(
            AIPrediction.prediction_date >= since,
            AIPrediction.prediction_correct.isnot(None)
        )
    )
    evaluated = result.scalars().all()

    # 获取未评估的预测数量（在 early return 之前查询）
    pending_result = await session.execute(
        select(AIPrediction)
        .where(
            AIPrediction.prediction_date >= since,
            AIPrediction.prediction_correct.is_(None)
        )
    )
    pending = len(pending_result.scalars().all())

    if not evaluated and pending == 0:
        return {
            "total_predictions": 0,
            "evaluated": 0,
            "pending_evaluation": 0,
            "correct": 0,
            "accuracy": None,
            "by_asset": {},
            "by_direction": {}
        }

    # 总体统计
    total = len(evaluated)
    correct = sum(1 for p in evaluated if p.prediction_correct == 1)

    # 按资产统计
    by_asset = {}
    for pred in evaluated:
        if pred.asset not in by_asset:
            by_asset[pred.asset] = {"total": 0, "correct": 0}
        by_asset[pred.asset]["total"] += 1
        if pred.prediction_correct == 1:
            by_asset[pred.asset]["correct"] += 1

    for asset in by_asset:
        stats = by_asset[asset]
        stats["accuracy"] = round(stats["correct"] / stats["total"], 4) if stats["total"] > 0 else 0

    # 按方向统计
    by_direction = {}
    for pred in evaluated:
        if pred.direction not in by_direction:
            by_direction[pred.direction] = {"total": 0, "correct": 0}
        by_direction[pred.direction]["total"] += 1
        if pred.prediction_correct == 1:
            by_direction[pred.direction]["correct"] += 1

    for direction in by_direction:
        stats = by_direction[direction]
        stats["accuracy"] = round(stats["correct"] / stats["total"], 4) if stats["total"] > 0 else 0

    return {
        "total_predictions": total + pending,
        "evaluated": total,
        "pending_evaluation": pending,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total > 0 else None,
        "by_asset": by_asset,
        "by_direction": by_direction
    }


# ============================================
# User Config CRUD
# ============================================

async def create_user_config(
    session: AsyncSession,
    name: str,
    asset_pool: List[str],
    asset_constraints: Optional[dict] = None,
    max_drawdown: float = 0.25,
    target_sharpe: float = 1.0,
    rebalance_threshold: float = 0.05,
    preferred_method: str = "composite",
    use_ai_adjustments: bool = True
) -> UserConfig:
    """创建用户配置"""
    async with _db_write_lock:
        record = UserConfig(
            name=name,
            asset_pool=asset_pool,
            asset_constraints=asset_constraints or {},
            max_drawdown=max_drawdown,
            target_sharpe=target_sharpe,
            rebalance_threshold=rebalance_threshold,
            preferred_method=preferred_method,
            use_ai_adjustments=1 if use_ai_adjustments else 0
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


async def get_user_config(session: AsyncSession, config_id: int) -> Optional[UserConfig]:
    """获取单个用户配置"""
    result = await session.execute(
        select(UserConfig).where(UserConfig.id == config_id)
    )
    return result.scalar_one_or_none()


async def get_user_config_by_name(session: AsyncSession, name: str) -> Optional[UserConfig]:
    """通过名称获取用户配置"""
    result = await session.execute(
        select(UserConfig).where(UserConfig.name == name)
    )
    return result.scalar_one_or_none()


async def list_user_configs(session: AsyncSession, active_only: bool = True) -> List[UserConfig]:
    """列出用户配置"""
    query = select(UserConfig)
    if active_only:
        query = query.where(UserConfig.is_active == 1)
    query = query.order_by(desc(UserConfig.created_at))
    result = await session.execute(query)
    return result.scalars().all()


async def update_user_config(
    session: AsyncSession,
    config_id: int,
    **kwargs
) -> Optional[UserConfig]:
    """更新用户配置"""
    async with _db_write_lock:
        record = await get_user_config(session, config_id)
        if not record:
            return None

        for key, value in kwargs.items():
            if hasattr(record, key) and value is not None:
                if key == 'use_ai_adjustments':
                    value = 1 if value else 0
                setattr(record, key, value)

        await session.commit()
        await session.refresh(record)
        return record


async def delete_user_config(session: AsyncSession, config_id: int) -> bool:
    """软删除用户配置"""
    async with _db_write_lock:
        record = await get_user_config(session, config_id)
        if not record:
            return False
        record.is_active = 0
        await session.commit()
        return True


# ============================================
# Strategy Snapshot CRUD
# ============================================

async def save_strategy_snapshot(
    session: AsyncSession,
    optimization_method: str,
    max_drawdown_limit: float,
    use_ai_adjustments: bool,
    market_snapshot: dict,
    macro_snapshot: dict,
    allocation: dict,
    rounded_allocation: dict,
    metrics: dict,
    user_config_id: Optional[int] = None,
    ai_analysis_id: Optional[int] = None,
    backtest_result: Optional[dict] = None
) -> StrategySnapshot:
    """保存策略快照"""
    async with _db_write_lock:
        record = StrategySnapshot(
            user_config_id=user_config_id,
            optimization_method=optimization_method,
            max_drawdown_limit=max_drawdown_limit,
            use_ai_adjustments=1 if use_ai_adjustments else 0,
            market_snapshot=market_snapshot,
            macro_snapshot=macro_snapshot,
            ai_analysis_id=ai_analysis_id,
            allocation=allocation,
            rounded_allocation=rounded_allocation,
            metrics=metrics,
            backtest_result=backtest_result
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record


async def get_strategy_snapshot(session: AsyncSession, snapshot_id: int) -> Optional[StrategySnapshot]:
    """获取单个策略快照"""
    result = await session.execute(
        select(StrategySnapshot).where(StrategySnapshot.id == snapshot_id)
    )
    return result.scalar_one_or_none()


async def get_strategy_snapshots(
    session: AsyncSession,
    days: int = 90,
    limit: int = 100,
    user_config_id: Optional[int] = None
) -> List[StrategySnapshot]:
    """获取策略快照列表"""
    since = datetime.now() - timedelta(days=days)
    query = select(StrategySnapshot).where(StrategySnapshot.created_at >= since)

    if user_config_id is not None:
        query = query.where(StrategySnapshot.user_config_id == user_config_id)

    query = query.order_by(desc(StrategySnapshot.created_at)).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


async def get_snapshot_metrics_trend(
    session: AsyncSession,
    days: int = 90
) -> List[dict]:
    """获取快照指标趋势数据"""
    snapshots = await get_strategy_snapshots(session, days=days, limit=200)

    trend_data = []
    for s in reversed(snapshots):  # 按时间正序
        metrics = s.metrics or {}
        trend_data.append({
            "id": s.id,
            "date": s.created_at.isoformat(),
            "sharpe": metrics.get("sharpe_ratio"),
            "return": metrics.get("expected_return"),
            "volatility": metrics.get("expected_volatility"),
            "max_drawdown": metrics.get("max_drawdown"),
            "method": s.optimization_method
        })

    return trend_data


async def compare_snapshots(
    session: AsyncSession,
    snapshot_ids: List[int]
) -> List[dict]:
    """对比多个策略快照"""
    results = []
    for sid in snapshot_ids:
        snapshot = await get_strategy_snapshot(session, sid)
        if snapshot:
            results.append({
                "id": snapshot.id,
                "created_at": snapshot.created_at.isoformat(),
                "method": snapshot.optimization_method,
                "max_drawdown_limit": snapshot.max_drawdown_limit,
                "use_ai": bool(snapshot.use_ai_adjustments),
                "allocation": snapshot.allocation,
                "rounded_allocation": snapshot.rounded_allocation,
                "metrics": snapshot.metrics
            })
    return results
