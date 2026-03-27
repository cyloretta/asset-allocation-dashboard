from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    ai_provider: str = "deepseek"  # anthropic 或 deepseek
    fred_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data.db"

    # Assets configuration
    assets: dict = {
        "SPY": {"name": "S&P 500 ETF", "type": "us_equity", "min_weight": 0.0, "max_weight": 0.4},
        "QQQ": {"name": "Nasdaq 100 ETF", "type": "us_equity", "min_weight": 0.0, "max_weight": 0.4},
        "GLD": {"name": "Gold ETF", "type": "commodity", "min_weight": 0.0, "max_weight": 0.3},
        "BTC-USD": {"name": "Bitcoin", "type": "crypto", "min_weight": 0.0, "max_weight": 0.2},
        "TLT": {"name": "US Treasury Bond ETF", "type": "bond", "min_weight": 0.0, "max_weight": 0.4},
        "CASH": {"name": "USD Cash", "type": "cash", "min_weight": 0.05, "max_weight": 1.0},
    }

    # Optimization constraints
    max_drawdown: float = 0.25
    target_sharpe: float = 1.0
    risk_free_rate: float = 0.05

    # Scheduler
    daily_update_hour: int = 6
    daily_update_minute: int = 0

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
