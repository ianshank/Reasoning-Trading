"""
News data providers for sentiment analysis.

Provides abstracted access to news sources including:
- Finnhub: Financial news and company news
- NewsAPI: General news aggregator
- Alpaca: Trading platform news
"""

from reasoning_trading.sentiment.providers.base import NewsProvider, NewsProviderError
from reasoning_trading.sentiment.providers.finnhub import FinnhubNewsProvider
from reasoning_trading.sentiment.providers.newsapi import NewsAPIProvider
from reasoning_trading.sentiment.providers.factory import create_news_providers

__all__ = [
    "NewsProvider",
    "NewsProviderError",
    "FinnhubNewsProvider",
    "NewsAPIProvider",
    "create_news_providers",
]
