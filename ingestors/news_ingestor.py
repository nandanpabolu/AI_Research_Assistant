"""
News ingestor for RSS feeds and article scraping.
"""

import asyncio
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import logging

try:
    import feedparser
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    feedparser = None
    requests = None
    BeautifulSoup = None

from .base import BaseIngestor
from models.schemas import DataSource, SourceType
from core.config import get_data_source_config

logger = logging.getLogger(__name__)

class NewsIngestor(BaseIngestor):
    """Ingestor for news articles from RSS feeds."""
    
    def __init__(self):
        """Initialize the news ingestor."""
        super().__init__(SourceType.NEWS_ARTICLE)
        self.config = get_data_source_config("news")
        self.session = None
        self._init_session()
    
    def _init_session(self):
        """Initialize HTTP session."""
        try:
            if requests is None:
                raise ImportError("requests not available")
            
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'AI Research Assistant (your-email@domain.com)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            })
            self.logger.info("News ingestor session initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize news ingestor session: {e}")
            self.session = None
    
    def can_handle(self, query: str) -> bool:
        """
        Check if this ingestor can handle the given query.
        
        Args:
            query: The search query (ticker symbol)
            
        Returns:
            True if the query is a valid ticker symbol
        """
        if not self.validate_query(query):
            return False
        
        # News ingestor can handle any query
        return True
    
    async def ingest(self, query: str, run_id: int = 0, **kwargs) -> List[DataSource]:
        """
        Ingest news articles for the given query.
        
        Args:
            query: Search query (e.g., ticker symbol)
            **kwargs: Additional parameters
            
        Returns:
            List of DataSource objects
        """
        if not self.session:
            self.logger.error("News ingestor session not available")
            return []
        
        max_articles = kwargs.get("max_articles", self.config.get("max_articles", 20))
        rss_feeds = kwargs.get("rss_feeds", self.config.get("rss_feeds", []))
        
        self.logger.info(f"Starting news ingestion for query: {query}")
        
        try:
            sources = []
            
            # Process RSS feeds
            for feed_url in rss_feeds:
                try:
                    self.logger.info(f"Processing RSS feed: {feed_url}")
                    feed_sources = await self._process_rss_feed(feed_url, query, max_articles // len(rss_feeds), run_id)
                    self.logger.info(f"Feed {feed_url} returned {len(feed_sources)} sources")
                    sources.extend(feed_sources)
                    
                    # Rate limiting between feeds
                    if len(rss_feeds) > 1:
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to process RSS feed {feed_url}: {e}")
                    continue
            
            # Limit total sources
            sources = sources[:max_articles]
            
            self.log_ingestion_summary(sources, query)
            return sources
            
        except Exception as e:
            self.logger.error(f"News ingestion failed for {query}: {e}")
            return []
    
    async def _process_rss_feed(self, feed_url: str, query: str, max_articles: int, run_id: int) -> List[DataSource]:
        """
        Process a single RSS feed.
        
        Args:
            feed_url: URL of the RSS feed
            query: Search query
            max_articles: Maximum articles to process
            
        Returns:
            List of DataSource objects
        """
        def parse_feed():
            try:
                feed = feedparser.parse(feed_url)
                return feed.entries[:max_articles]
            except Exception as e:
                logger.error(f"Failed to parse RSS feed {feed_url}: {e}")
                return []
        
        # Parse RSS feed
        loop = asyncio.get_event_loop()
        entries = await loop.run_in_executor(None, parse_feed)
        
        sources = []
        
        for entry in entries:
            try:
                # Check if article is relevant to query
                if self._is_relevant_article(entry, query):
                    source = await self._process_article(entry, query, run_id)
                    if source:
                        sources.append(source)
                        
            except Exception as e:
                self.logger.warning(f"Failed to process RSS entry: {e}")
                continue
        
        return sources
    
    def _is_relevant_article(self, entry, query: str) -> bool:
        """
        Check if an article is relevant to the query.
        
        Args:
            entry: RSS feed entry
            query: Search query
            
        Returns:
            True if article is relevant
        """
        if not query:
            return True
        
        query_lower = query.lower()
        
        # Company name mappings for common tickers
        company_names = {
            'aapl': ['apple', 'apple inc', 'iphone', 'macbook', 'ipad'],
            'tsla': ['tesla', 'tesla inc', 'electric vehicle', 'ev'],
            'msft': ['microsoft', 'microsoft corp', 'windows', 'azure'],
            'googl': ['google', 'alphabet', 'alphabet inc'],
            'amzn': ['amazon', 'amazon.com', 'e-commerce'],
            'meta': ['facebook', 'meta platforms', 'social media'],
            'nvda': ['nvidia', 'nvidia corp', 'gpu', 'artificial intelligence'],
            'brk': ['berkshire hathaway', 'warren buffett'],
            'jpm': ['jpmorgan', 'jpmorgan chase', 'bank'],
            'v': ['visa', 'visa inc', 'payment', 'credit card']
        }
        
        # Check if query is a ticker and expand search terms
        search_terms = [query_lower]
        if query_lower in company_names:
            search_terms.extend(company_names[query_lower])
        
        # Check title
        if hasattr(entry, 'title') and entry.title:
            title_lower = entry.title.lower()
            # Check all search terms (including company names)
            if any(term in title_lower for term in search_terms):
                return True
            
            # Check for business/finance keywords if it's a ticker
            if len(query) <= 5 and query.isupper():  # Likely a ticker
                business_keywords = ['stock', 'market', 'earnings', 'revenue', 'profit', 'financial', 'business', 'company', 'trading']
                if any(keyword in title_lower for keyword in business_keywords):
                    return True
        
        # Check summary
        if hasattr(entry, 'summary') and entry.summary:
            summary_lower = entry.summary.lower()
            # Check all search terms (including company names)
            if any(term in summary_lower for term in search_terms):
                return True
            
            # Check for business/finance keywords if it's a ticker
            if len(query) <= 5 and query.isupper():  # Likely a ticker
                business_keywords = ['stock', 'market', 'earnings', 'revenue', 'profit', 'financial', 'business', 'company', 'trading']
                if any(keyword in summary_lower for keyword in business_keywords):
                    return True
        
        # Check tags
        if hasattr(entry, 'tags') and entry.tags:
            for tag in entry.tags:
                if hasattr(tag, 'term') and query_lower in tag.term.lower():
                    return True
        
        # For ticker symbols, also accept general business/finance articles
        if len(query) <= 5 and query.isupper():
            # Accept articles with business/finance content
            return True
        
        # For any query, accept business/finance articles as they might be relevant
        business_keywords = ['stock', 'market', 'earnings', 'revenue', 'profit', 'financial', 'business', 'company', 'trading', 'economy', 'investment']
        if hasattr(entry, 'title') and entry.title:
            if any(keyword in entry.title.lower() for keyword in business_keywords):
                return True
        if hasattr(entry, 'summary') and entry.summary:
            if any(keyword in entry.summary.lower() for keyword in business_keywords):
                return True
        
        return False
    
    async def _process_article(self, entry, query: str, run_id: int) -> Optional[DataSource]:
        """
        Process a single article entry.
        
        Args:
            entry: RSS feed entry
            query: Search query
            
        Returns:
            DataSource object or None if processing fails
        """
        try:
            # Extract basic metadata
            title = getattr(entry, 'title', 'Untitled Article')
            url = getattr(entry, 'link', '')
            published_at = self._parse_published_date(entry)
            
            # Scrape article content if possible
            content = ""
            if url and self.config.get("respect_robots_txt", True):
                content = await self._scrape_article_content(url)
            
            # If scraping failed, use summary
            if not content and hasattr(entry, 'summary'):
                content = entry.summary
            
            # Generate checksum
            checksum = hashlib.md5(content.encode()).hexdigest() if content else None
            
            # Create metadata
            metadata = {
                "query": query,
                "feed_title": getattr(entry, 'feed', {}).get('title', 'Unknown Feed'),
                "author": getattr(entry, 'author', 'Unknown'),
                "scraped": bool(content and content != getattr(entry, 'summary', '')),
                "extracted_at": datetime.now().isoformat()
            }
            
            # Create source
            source = self.create_source(
                run_id=run_id,
                url=url,
                title=title,
                published_at=published_at,
                checksum=checksum,
                raw_content=content,
                metadata=metadata
            )
            
            return source
            
        except Exception as e:
            self.logger.warning(f"Failed to process article: {e}")
            return None
    
    def _parse_published_date(self, entry) -> Optional[datetime]:
        """
        Parse the published date from an RSS entry.
        
        Args:
            entry: RSS feed entry
            
        Returns:
            Parsed datetime or None
        """
        try:
            # Try different date fields
            date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']
            
            for field in date_fields:
                if hasattr(entry, field) and getattr(entry, field):
                    time_tuple = getattr(entry, field)
                    return datetime(*time_tuple[:6])
            
            # Try string parsing
            if hasattr(entry, 'published'):
                from dateutil import parser
                return parser.parse(entry.published)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Failed to parse date: {e}")
            return None
    
    async def _scrape_article_content(self, url: str) -> str:
        """
        Scrape article content from URL.
        
        Args:
            url: Article URL
            
        Returns:
            Extracted content or empty string
        """
        try:
            if not self.session:
                return ""
            
            # Check robots.txt (basic implementation)
            if self.config.get("respect_robots_txt", True):
                if not await self._check_robots_txt(url):
                    return ""
            
            # Fetch article
            timeout = self.config.get("article_timeout", 10)
            response = await self._fetch_url(url, timeout)
            
            if not response or response.status_code != 200:
                return ""
            
            # Parse content
            content = self._extract_article_content(response.text, url)
            return content
            
        except Exception as e:
            self.logger.debug(f"Failed to scrape article {url}: {e}")
            return ""
    
    async def _check_robots_txt(self, url: str) -> bool:
        """
        Basic robots.txt check.
        
        Args:
            url: Article URL
            
        Returns:
            True if allowed to scrape
        """
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            response = await self._fetch_url(robots_url, timeout=5)
            if not response or response.status_code != 200:
                return True  # Assume allowed if robots.txt not found
            
            robots_content = response.text.lower()
            
            # Check for disallow rules
            if "user-agent: *" in robots_content:
                disallow_section = robots_content.split("user-agent: *")[1].split("user-agent:")[0]
                if "disallow: /" in disallow_section:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"Robots.txt check failed: {e}")
            return True  # Assume allowed on error
    
    async def _fetch_url(self, url: str, timeout: int = 10):
        """
        Fetch URL content.
        
        Args:
            url: URL to fetch
            timeout: Request timeout
            
        Returns:
            Response object or None
        """
        def fetch():
            try:
                return self.session.get(url, timeout=timeout)
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch)
    
    def _extract_article_content(self, html: str, url: str) -> str:
        """
        Extract article content from HTML.
        
        Args:
            html: HTML content
            url: Article URL
            
        Returns:
            Extracted text content
        """
        try:
            if not BeautifulSoup:
                return ""
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Try to find main content
            content_selectors = [
                'article',
                '[role="main"]',
                '.content',
                '.article-content',
                '.post-content',
                '.entry-content',
                'main',
                '.main-content'
            ]
            
            content_element = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break
            
            # If no main content found, use body
            if not content_element:
                content_element = soup.body or soup
            
            if not content_element:
                return ""
            
            # Extract text
            text = content_element.get_text()
            
            # Clean up text
            text = re.sub(r'\s+', ' ', text)  # Multiple spaces
            text = re.sub(r'\n\s*\n', '\n', text)  # Multiple newlines
            text = text.strip()
            
            return text
            
        except Exception as e:
            self.logger.debug(f"Failed to extract content from {url}: {e}")
            return ""
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.session:
                self.session.close()
                self.logger.info("News ingestor session closed")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup news ingestor: {e}")
    
    def get_supported_feeds(self) -> List[str]:
        """Get list of supported RSS feeds."""
        return self.config.get("rss_feeds", [])
    
    def get_scraping_config(self) -> Dict[str, Any]:
        """Get scraping configuration."""
        return {
            "respect_robots_txt": self.config.get("respect_robots_txt", True),
            "article_timeout": self.config.get("article_timeout", 10),
            "max_articles": self.config.get("max_articles", 20)
        }
