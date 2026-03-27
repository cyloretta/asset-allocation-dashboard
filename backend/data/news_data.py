import feedparser
from datetime import datetime, timedelta
from typing import List, Dict
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re
import logging

logger = logging.getLogger(__name__)

# 尝试导入翻译库
try:
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='en', target='zh-CN')
    HAS_TRANSLATOR = True
except Exception as e:
    logger.warning(f"Google Translate not available: {e}")
    translator = None
    HAS_TRANSLATOR = False

# 翻译缓存，避免重复翻译
_translation_cache: Dict[str, str] = {}


class NewsFetcher:
    """Fetch financial news from RSS feeds"""

    RSS_FEEDS = {
        "reuters_markets": "https://feeds.reuters.com/reuters/businessNews",
        "yahoo_finance": "https://finance.yahoo.com/rss/topfinstories",
        "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "marketwatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
        "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
    }

    KEYWORDS = [
        "fed", "federal reserve", "interest rate", "inflation",
        "recession", "gdp", "employment", "jobs",
        "stock", "market", "s&p", "nasdaq", "dow",
        "bitcoin", "crypto", "gold", "oil",
        "china", "europe", "geopolitical", "war", "tariff",
        "ai", "artificial intelligence", "tech"
    ]

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)

    def _fetch_feed_sync(self, feed_name: str, feed_url: str) -> List[dict]:
        """Synchronously fetch and parse a single RSS feed"""
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            for entry in feed.entries[:10]:  # Limit to 10 per source
                published = entry.get("published_parsed")
                if published:
                    pub_date = datetime(*published[:6])
                else:
                    pub_date = datetime.now()

                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                # Clean HTML from summary
                summary = re.sub(r'<[^>]+>', '', summary)[:500]

                relevance = self._calculate_relevance(title + " " + summary)

                articles.append({
                    "title": title,
                    "title_zh": self._translate_title(title),
                    "source": feed_name,
                    "url": entry.get("link", ""),
                    "published_at": pub_date.isoformat(),  # Convert to ISO string for JSON serialization
                    "published_at_dt": pub_date,  # Keep datetime for internal use
                    "summary": summary,
                    "relevance_score": relevance,
                    "sentiment": 0  # Will be filled by AI analysis
                })

            return articles
        except Exception as e:
            logger.warning(f"Error fetching {feed_name}: {e}")
            return []

    def _calculate_relevance(self, text: str) -> float:
        """Calculate relevance score based on keyword matching"""
        text_lower = text.lower()
        matches = sum(1 for kw in self.KEYWORDS if kw in text_lower)
        return min(1.0, matches / 5)  # Normalize to 0-1

    def _translate_title(self, title: str) -> str:
        """Translate news title to Chinese using Google Translate"""
        global _translation_cache

        # 检查缓存
        if title in _translation_cache:
            return _translation_cache[title]

        # 如果翻译器可用，使用 Google 翻译
        if HAS_TRANSLATOR and translator:
            try:
                translated = translator.translate(title)
                if translated:
                    _translation_cache[title] = translated
                    return translated
            except Exception as e:
                logger.warning(f"Translation failed for '{title[:50]}...': {e}")

        # 翻译失败时返回原标题
        return title

    async def fetch_all(self) -> List[dict]:
        """Fetch news from all configured feeds"""
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.executor, self._fetch_feed_sync, name, url)
            for name, url in self.RSS_FEEDS.items()
        ]
        results = await asyncio.gather(*tasks)

        # Flatten and sort by relevance
        all_news = []
        for feed_news in results:
            all_news.extend(feed_news)

        # Sort by relevance, then by date
        all_news.sort(key=lambda x: (-x["relevance_score"], -x["published_at_dt"].timestamp()))
        return all_news[:50]  # Return top 50 most relevant

    async def get_market_news(self, hours: int = 24) -> List[dict]:
        """Get market-relevant news from the last N hours"""
        all_news = await self.fetch_all()
        cutoff = datetime.now() - timedelta(hours=hours)
        return [n for n in all_news if n["published_at_dt"] >= cutoff]

    async def get_news_summary(self) -> dict:
        """Get a summary of recent news for AI analysis"""
        news = await self.get_market_news(hours=24)
        # Remove internal datetime field before returning (not JSON serializable)
        clean_news = [
            {k: v for k, v in n.items() if k != "published_at_dt"}
            for n in news[:10]
        ]
        return {
            "total_articles": len(news),
            "top_stories": clean_news,
            "keyword_counts": self._count_keywords(news),
            "sources": list(set(n["source"] for n in news))
        }

    def _count_keywords(self, news: List[dict]) -> Dict[str, int]:
        """Count keyword occurrences in news"""
        counts = {kw: 0 for kw in self.KEYWORDS}
        for article in news:
            text = (article["title"] + " " + article["summary"]).lower()
            for kw in self.KEYWORDS:
                if kw in text:
                    counts[kw] += 1
        # Return sorted by count
        return dict(sorted(counts.items(), key=lambda x: -x[1])[:15])
