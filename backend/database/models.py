from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), index=True)
    date = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    created_at = Column(DateTime, default=func.now())


class MacroIndicator(Base):
    __tablename__ = "macro_indicators"

    id = Column(Integer, primary_key=True, index=True)
    indicator_name = Column(String(50), index=True)
    date = Column(DateTime, index=True)
    value = Column(Float)
    source = Column(String(50))
    created_at = Column(DateTime, default=func.now())


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    analysis_type = Column(String(50))  # geopolitical, fed_policy, tech_trend, sentiment
    content = Column(Text)
    risk_score = Column(Float)  # 0-100
    key_factors = Column(JSON)
    recommendations = Column(JSON)
    created_at = Column(DateTime, default=func.now())


class StrategyRecord(Base):
    __tablename__ = "strategy_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    allocation = Column(JSON)  # {"SPY": 0.3, "QQQ": 0.25, ...}
    expected_return = Column(Float)
    expected_volatility = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    reasoning = Column(Text)
    # 方案C数据
    rounded_allocation = Column(JSON, nullable=True)  # 5%取整后的配置
    rebalance_advice = Column(JSON, nullable=True)  # 调仓建议
    rebalance_count = Column(Integer, nullable=True)  # 需要调仓的资产数
    risk_context = Column(JSON, nullable=True)  # 统一风险上下文
    created_at = Column(DateTime, default=func.now())


class NewsEvent(Base):
    __tablename__ = "news_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    source = Column(String(100))
    url = Column(String(1000))
    published_at = Column(DateTime)
    summary = Column(Text)
    sentiment = Column(Float)  # -1 to 1
    relevance_score = Column(Float)  # 0 to 1
    created_at = Column(DateTime, default=func.now())


class AIAnalysisCache(Base):
    """缓存完整的 AI 分析结果，供策略优化使用"""
    __tablename__ = "ai_analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)

    # AI 分析的完整结果
    adjustments = Column(JSON)  # {"SPY": 0.03, "BTC-USD": -0.02, ...}
    overall_risk_score = Column(Float)  # 0-100
    market_summary = Column(Text)  # AI 生成的市场摘要
    allocation_advice = Column(JSON)  # 完整的配置建议
    raw_response = Column(JSON)  # AI 返回的完整原始数据


class AIPrediction(Base):
    """P2: AI 预测记录，用于追踪准确率"""
    __tablename__ = "ai_predictions"

    id = Column(Integer, primary_key=True, index=True)
    prediction_date = Column(DateTime, index=True)  # 预测日期
    evaluation_date = Column(DateTime, nullable=True)  # 评估日期（预测日+10天）

    # 预测内容
    asset = Column(String(20), index=True)  # 资产代码
    direction = Column(String(20))  # increase/decrease/maintain
    adjustment_value = Column(Float)  # 调整幅度
    confidence = Column(Float)  # AI 置信度 (可选)

    # 预测时的价格
    price_at_prediction = Column(Float)

    # 评估结果
    price_at_evaluation = Column(Float, nullable=True)
    actual_return = Column(Float, nullable=True)  # 实际收益率
    prediction_correct = Column(Integer, nullable=True)  # 1=正确, 0=错误, NULL=未评估

    # 元数据
    model = Column(String(50))  # 使用的模型
    created_at = Column(DateTime, default=func.now())


class UserConfig(Base):
    """用户配置：资产池、约束条件、风险偏好"""
    __tablename__ = "user_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # 资产配置
    asset_pool = Column(JSON)  # ["SPY", "QQQ", ...]
    asset_constraints = Column(JSON)  # {"SPY": {"min": 0, "max": 0.4}}

    # 风险偏好
    max_drawdown = Column(Float, default=0.25)
    target_sharpe = Column(Float, default=1.0)
    rebalance_threshold = Column(Float, default=0.05)

    # 优化偏好
    preferred_method = Column(String(50), default="composite")
    use_ai_adjustments = Column(Integer, default=1)


class StrategySnapshot(Base):
    """策略快照：完整记录优化时的参数、市场状态和结果"""
    __tablename__ = "strategy_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_config_id = Column(Integer, nullable=True)  # 关联用户配置
    created_at = Column(DateTime, default=func.now(), index=True)

    # 优化参数
    optimization_method = Column(String(50))
    max_drawdown_limit = Column(Float)
    use_ai_adjustments = Column(Integer)

    # 快照数据
    market_snapshot = Column(JSON)  # 优化时的市场价格
    macro_snapshot = Column(JSON)   # 优化时的宏观指标
    ai_analysis_id = Column(Integer, nullable=True)  # 关联 AI 分析缓存

    # 结果
    allocation = Column(JSON)           # 优化后配置
    rounded_allocation = Column(JSON)   # 取整后配置
    metrics = Column(JSON)              # 性能指标
    backtest_result = Column(JSON, nullable=True)  # 回测结果
