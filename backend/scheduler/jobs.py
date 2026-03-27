from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from config import get_settings
from data import MarketDataFetcher, MacroDataFetcher, NewsFetcher
from analysis import AIAnalyst
from strategy import PortfolioOptimizer
from database import (
    async_session, save_market_data, save_ai_analysis,
    save_strategy, save_news_event
)

settings = get_settings()
logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manage scheduled jobs for data updates and analysis"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.market_fetcher = MarketDataFetcher()
        self.macro_fetcher = MacroDataFetcher()
        self.news_fetcher = NewsFetcher()
        self.ai_analyst = AIAnalyst()
        self.optimizer = PortfolioOptimizer()

    def start(self):
        """Start the scheduler"""
        # Daily market data update (6:00 AM)
        self.scheduler.add_job(
            self.update_market_data,
            CronTrigger(hour=settings.daily_update_hour, minute=settings.daily_update_minute),
            id="daily_market_update",
            replace_existing=True
        )

        # Daily AI analysis (6:30 AM)
        self.scheduler.add_job(
            self.run_daily_analysis,
            CronTrigger(hour=settings.daily_update_hour, minute=30),
            id="daily_ai_analysis",
            replace_existing=True
        )

        # News update every 4 hours
        self.scheduler.add_job(
            self.update_news,
            CronTrigger(hour="*/4"),
            id="news_update",
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    async def update_market_data(self):
        """Fetch and store latest market data"""
        logger.info("Starting market data update...")
        try:
            data = await self.market_fetcher.fetch_all(period="5d")

            async with async_session() as session:
                for ticker, df in data.items():
                    if not df.empty:
                        latest = df.iloc[-1]
                        await save_market_data(session, ticker, {
                            "date": df.index[-1].to_pydatetime(),
                            "open": float(latest["Open"]),
                            "high": float(latest["High"]),
                            "low": float(latest["Low"]),
                            "close": float(latest["Close"]),
                            "volume": float(latest["Volume"])
                        })

            logger.info(f"Market data updated for {len(data)} tickers")
        except Exception as e:
            logger.error(f"Market data update failed: {e}")

    async def run_daily_analysis(self):
        """Run daily AI analysis and strategy optimization"""
        logger.info("Starting daily AI analysis...")
        try:
            # Gather data
            market_data = await self.market_fetcher.get_current_prices()
            macro_data = await self.macro_fetcher.fetch_all()
            news_summary = await self.news_fetcher.get_news_summary()

            # Run AI analysis
            analysis = await self.ai_analyst.analyze(market_data, macro_data, news_summary)

            # Get historical returns for optimization
            returns = await self.market_fetcher.get_historical_returns()

            # Get AI recommended adjustments
            ai_adjustments = analysis.get("allocation_advice", {}).get("adjustments", {})

            # Run portfolio optimization (综合优化：保住回撤底线，最大化夏普比率)
            optimization = self.optimizer.optimize(
                returns,
                ai_adjustments=ai_adjustments,
                method="composite"
            )

            # Save results
            async with async_session() as session:
                # Save AI analysis
                await save_ai_analysis(
                    session,
                    analysis_type="daily_comprehensive",
                    content=analysis.get("summary", ""),
                    risk_score=analysis.get("overall_risk_score", 50),
                    key_factors=[
                        analysis.get("geopolitical_risk", {}).get("key_risks", []),
                        analysis.get("tech_trend", {}).get("key_factors", [])
                    ],
                    recommendations=[analysis.get("allocation_advice", {})]
                )

                # Save strategy
                await save_strategy(
                    session,
                    allocation=optimization.get("allocation", {}),
                    metrics=optimization.get("metrics", {}),
                    reasoning=analysis.get("allocation_advice", {}).get("reasoning", "")
                )

            logger.info("Daily analysis completed successfully")
            return {"analysis": analysis, "optimization": optimization}

        except Exception as e:
            logger.error(f"Daily analysis failed: {e}")
            raise

    async def update_news(self):
        """Fetch and store latest news"""
        logger.info("Starting news update...")
        try:
            news = await self.news_fetcher.get_market_news(hours=4)

            async with async_session() as session:
                for article in news[:20]:  # Store top 20
                    await save_news_event(session, article)

            logger.info(f"News updated: {len(news)} articles")
        except Exception as e:
            logger.error(f"News update failed: {e}")

    async def run_manual_update(self) -> dict:
        """Manually trigger full update (for API endpoint)"""
        await self.update_market_data()
        result = await self.run_daily_analysis()
        await self.update_news()
        return result
