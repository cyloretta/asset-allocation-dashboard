from .models import Base, MarketData, MacroIndicator, AIAnalysis, StrategyRecord, NewsEvent, AIPrediction, AIAnalysisCache, UserConfig, StrategySnapshot
from .crud import (
    init_db, get_db, async_session,
    save_market_data, get_market_data, get_latest_prices,
    save_macro_indicator, get_macro_indicators,
    save_ai_analysis, get_latest_analysis, get_analysis_history,
    save_strategy, get_latest_strategy, get_strategy_history,
    save_news_event, get_recent_news,
    # P2: AI 预测追踪
    save_ai_predictions, evaluate_predictions, get_ai_accuracy_stats,
    # AI 分析缓存（用于策略优化）
    save_ai_analysis_cache, get_latest_ai_analysis_cache, get_ai_analysis_status,
    # 用户配置
    create_user_config, get_user_config, get_user_config_by_name,
    list_user_configs, update_user_config, delete_user_config,
    # 策略快照
    save_strategy_snapshot, get_strategy_snapshot, get_strategy_snapshots,
    get_snapshot_metrics_trend, compare_snapshots
)

__all__ = [
    "Base", "MarketData", "MacroIndicator", "AIAnalysis", "StrategyRecord", "NewsEvent",
    "AIPrediction", "AIAnalysisCache", "UserConfig", "StrategySnapshot",
    "init_db", "get_db", "async_session",
    "save_market_data", "get_market_data", "get_latest_prices",
    "save_macro_indicator", "get_macro_indicators",
    "save_ai_analysis", "get_latest_analysis", "get_analysis_history",
    "save_strategy", "get_latest_strategy", "get_strategy_history",
    "save_news_event", "get_recent_news",
    "save_ai_predictions", "evaluate_predictions", "get_ai_accuracy_stats",
    "save_ai_analysis_cache", "get_latest_ai_analysis_cache", "get_ai_analysis_status",
    "create_user_config", "get_user_config", "get_user_config_by_name",
    "list_user_configs", "update_user_config", "delete_user_config",
    "save_strategy_snapshot", "get_strategy_snapshot", "get_strategy_snapshots",
    "get_snapshot_metrics_trend", "compare_snapshots"
]
