"""
Data ingestion modules for the AI Research Analyst Agent.
"""

from .base import BaseIngestor
from .sec_ingestor import SECIngestor
from .news_ingestor import NewsIngestor
from .market_ingestor import MarketIngestor

__all__ = [
    "BaseIngestor",
    "SECIngestor", 
    "NewsIngestor",
    "MarketIngestor"
]



