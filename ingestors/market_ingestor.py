"""
Market data ingestor using yfinance.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    yf = None
    pd = None

from .base import BaseIngestor
from models.schemas import DataSource, SourceType
from core.config import get_data_source_config

logger = logging.getLogger(__name__)

class MarketIngestor(BaseIngestor):
    """Ingestor for market data using yfinance."""
    
    def __init__(self):
        """Initialize the market ingestor."""
        super().__init__(SourceType.MARKET_DATA)
        self.config = get_data_source_config("market")
        self._validate_dependencies()
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Minimum 2 seconds between requests
    
    def _validate_dependencies(self):
        """Validate required dependencies."""
        if yf is None:
            self.logger.error("yfinance not available")
        if pd is None:
            self.logger.error("pandas not available")
    
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
        
        # Market ingestor can handle any query that looks like a ticker
        # Basic validation - 1-5 alphanumeric characters
        import re
        ticker_pattern = re.compile(r'^[A-Z]{1,5}$')
        return bool(ticker_pattern.match(query.strip().upper()))
    
    async def ingest(self, query: str, run_id: int = 0, **kwargs) -> List[DataSource]:
        """
        Ingest market data for the given ticker.
        
        Args:
            query: Ticker symbol (e.g., "AAPL")
            **kwargs: Additional parameters
            
        Returns:
            List of DataSource objects
        """
        if not self.can_handle(query):
            self.logger.warning(f"Cannot handle query: {query}")
            return []
        
        if not yf or not pd:
            self.logger.error("Required dependencies not available")
            return []
        
        ticker = query.strip().upper()
        period = kwargs.get("period", self.config.get("period", "1y"))
        interval = kwargs.get("interval", self.config.get("interval", "1d"))
        max_retries = kwargs.get("max_retries", self.config.get("max_retries", 3))
        
        self.logger.info(f"Starting market data ingestion for {ticker}")
        
        try:
            sources = []
            
            # Get ticker info
            try:
                ticker_info = await self._get_ticker_info(ticker, run_id, max_retries)
                if ticker_info:
                    sources.append(ticker_info)
                    self.logger.info(f"✅ Collected ticker info for {ticker}")
                else:
                    self.logger.warning(f"⚠️ No ticker info collected for {ticker}")
            except Exception as e:
                self.logger.error(f"❌ Failed to get ticker info for {ticker}: {e}")
            
            # Get historical data
            try:
                historical_data = await self._get_historical_data(ticker, period, interval, run_id, max_retries)
                if historical_data:
                    sources.append(historical_data)
                    self.logger.info(f"✅ Collected historical data for {ticker}")
                else:
                    self.logger.warning(f"⚠️ No historical data collected for {ticker}")
            except Exception as e:
                self.logger.error(f"❌ Failed to get historical data for {ticker}: {e}")
            
            # Get financial ratios
            try:
                financial_ratios = await self._get_financial_ratios(ticker, run_id, max_retries)
                if financial_ratios:
                    sources.append(financial_ratios)
                    self.logger.info(f"✅ Collected financial ratios for {ticker}")
                else:
                    self.logger.warning(f"⚠️ No financial ratios collected for {ticker}")
            except Exception as e:
                self.logger.error(f"❌ Failed to get financial ratios for {ticker}: {e}")
            
            # Get earnings data
            try:
                earnings_data = await self._get_earnings_data(ticker, run_id, max_retries)
                if earnings_data:
                    sources.append(earnings_data)
                    self.logger.info(f"✅ Collected earnings data for {ticker}")
                else:
                    self.logger.warning(f"⚠️ No earnings data collected for {ticker}")
            except Exception as e:
                self.logger.error(f"❌ Failed to get earnings data for {ticker}: {e}")
            
            self.logger.info(f"🎯 Market ingestor collected {len(sources)} sources for {ticker}")
            self.log_ingestion_summary(sources, ticker)
            return sources
            
        except Exception as e:
            self.logger.error(f"Market data ingestion failed for {ticker}: {e}")
            return []
    
    async def _get_ticker_info(self, ticker: str, run_id: int, max_retries: int) -> Optional[DataSource]:
        """
        Get basic ticker information.
        
        Args:
            ticker: Ticker symbol
            max_retries: Maximum retry attempts
            
        Returns:
            DataSource object or None
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        def fetch_info():
            try:
                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info
                self.last_request_time = time.time()
                return info
            except Exception as e:
                logger.error(f"Failed to fetch ticker info for {ticker}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, fetch_info)
        
        if not info:
            return None
        
        # Create metadata
        metadata = {
            "ticker": ticker,
            "company_name": info.get('longName', 'Unknown'),
            "sector": info.get('sector', 'Unknown'),
            "industry": info.get('industry', 'Unknown'),
            "market_cap": info.get('marketCap'),
            "enterprise_value": info.get('enterpriseValue'),
            "pe_ratio": info.get('trailingPE'),
            "forward_pe": info.get('forwardPE'),
            "price_to_book": info.get('priceToBook'),
            "dividend_yield": info.get('dividendYield'),
            "beta": info.get('beta'),
            "extracted_at": datetime.now().isoformat()
        }
        
        # Create content
        content = self._format_ticker_info(info)
        
        return self.create_source(
            run_id=run_id,
            url=f"yfinance://{ticker}/info",
            title=f"{ticker} Company Information",
            published_at=datetime.now(),
            raw_content=content,
            metadata=metadata
        )
    
    async def _get_historical_data(self, ticker: str, period: str, interval: str, 
                                 run_id: int, max_retries: int) -> Optional[DataSource]:
        """
        Get historical price data.
        
        Args:
            ticker: Ticker symbol
            period: Time period (e.g., "1y", "6mo")
            interval: Data interval (e.g., "1d", "1wk")
            max_retries: Maximum retry attempts
            
        Returns:
            DataSource object or None
        """
        def fetch_history():
            try:
                ticker_obj = yf.Ticker(ticker)
                hist = ticker_obj.history(period=period, interval=interval)
                return hist
            except Exception as e:
                logger.error(f"Failed to fetch historical data for {ticker}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        hist = await loop.run_in_executor(None, fetch_history)
        
        if hist is None or hist.empty:
            return None
        
        # Calculate key metrics
        latest_price = hist['Close'].iloc[-1]
        price_change = hist['Close'].iloc[-1] - hist['Close'].iloc[0]
        price_change_pct = (price_change / hist['Close'].iloc[0]) * 100
        
        # Calculate volatility
        returns = hist['Close'].pct_change().dropna()
        volatility = returns.std() * (252 ** 0.5)  # Annualized volatility
        
        # Calculate moving averages
        ma_20 = hist['Close'].rolling(window=20).mean().iloc[-1]
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        
        # Create metadata
        metadata = {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data_points": len(hist),
            "latest_price": float(latest_price),
            "price_change": float(price_change),
            "price_change_pct": float(price_change_pct),
            "volatility": float(volatility),
            "ma_20": float(ma_20) if not pd.isna(ma_20) else None,
            "ma_50": float(ma_50) if not pd.isna(ma_50) else None,
            "volume_avg": float(hist['Volume'].mean()),
            "extracted_at": datetime.now().isoformat()
        }
        
        # Create content
        content = self._format_historical_data(hist, metadata)
        
        return self.create_source(
            run_id=run_id,
            url=f"yfinance://{ticker}/history",
            title=f"{ticker} Historical Data ({period})",
            published_at=datetime.now(),
            raw_content=content,
            metadata=metadata
        )
    
    async def _get_financial_ratios(self, ticker: str, run_id: int, max_retries: int) -> Optional[DataSource]:
        """
        Get financial ratios and metrics.
        
        Args:
            ticker: Ticker symbol
            max_retries: Maximum retry attempts
            
        Returns:
            DataSource object or None
        """
        def fetch_ratios():
            try:
                ticker_obj = yf.Ticker(ticker)
                
                # Get various financial data
                ratios = {}
                
                # Valuation ratios
                info = ticker_obj.info
                ratios.update({
                    'pe_ratio': info.get('trailingPE'),
                    'forward_pe': info.get('forwardPE'),
                    'price_to_book': info.get('priceToBook'),
                    'price_to_sales': info.get('priceToSalesTrailing12Months'),
                    'enterprise_value_to_ebitda': info.get('enterpriseToEbitda'),
                })
                
                # Profitability ratios
                ratios.update({
                    'return_on_equity': info.get('returnOnEquity'),
                    'return_on_assets': info.get('returnOnAssets'),
                    'profit_margin': info.get('profitMargins'),
                    'operating_margin': info.get('operatingMargins'),
                })
                
                # Financial strength ratios
                ratios.update({
                    'current_ratio': info.get('currentRatio'),
                    'debt_to_equity': info.get('debtToEquity'),
                    'quick_ratio': info.get('quickRatio'),
                })
                
                return ratios
                
            except Exception as e:
                logger.error(f"Failed to fetch financial ratios for {ticker}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        ratios = await loop.run_in_executor(None, fetch_ratios)
        
        if not ratios:
            return None
        
        # Create metadata
        metadata = {
            "ticker": ticker,
            "ratios": ratios,
            "extracted_at": datetime.now().isoformat()
        }
        
        # Create content
        content = self._format_financial_ratios(ratios)
        
        return self.create_source(
            run_id=run_id,
            url=f"yfinance://{ticker}/ratios",
            title=f"{ticker} Financial Ratios",
            published_at=datetime.now(),
            raw_content=content,
            metadata=metadata
        )
    
    async def _get_earnings_data(self, ticker: str, run_id: int, max_retries: int) -> Optional[DataSource]:
        """
        Get earnings data.
        
        Args:
            ticker: Ticker symbol
            max_retries: Maximum retry attempts
            
        Returns:
            DataSource object or None
        """
        def fetch_earnings():
            try:
                ticker_obj = yf.Ticker(ticker)
                
                # Get earnings data
                earnings = ticker_obj.earnings
                earnings_dates = ticker_obj.earnings_dates
                
                # Check if we have meaningful earnings data
                if earnings is not None and not earnings.empty:
                    earnings_dict = earnings.to_dict()
                else:
                    earnings_dict = None
                    
                if earnings_dates is not None and not earnings_dates.empty:
                    earnings_dates_dict = earnings_dates.to_dict()
                else:
                    earnings_dates_dict = None
                
                # Only return if we have some data
                if earnings_dict or earnings_dates_dict:
                    return {
                        'earnings': earnings_dict,
                        'earnings_dates': earnings_dates_dict
                    }
                else:
                    logger.info(f"No earnings data available for {ticker}")
                    return None
                
            except Exception as e:
                logger.error(f"Failed to fetch earnings data for {ticker}: {e}")
                return None
        
        loop = asyncio.get_event_loop()
        earnings_data = await loop.run_in_executor(None, fetch_earnings)
        
        if not earnings_data:
            return None
        
        # Create metadata
        metadata = {
            "ticker": ticker,
            "earnings_count": len(earnings_data.get('earnings', {})) if earnings_data.get('earnings') else 0,
            "earnings_dates_count": len(earnings_data.get('earnings_dates', {})) if earnings_data.get('earnings_dates') else 0,
            "extracted_at": datetime.now().isoformat()
        }
        
        # Create content
        content = self._format_earnings_data(earnings_data)
        
        return self.create_source(
            run_id=run_id,
            url=f"yfinance://{ticker}/earnings",
            title=f"{ticker} Earnings Data",
            published_at=datetime.now(),
            raw_content=content,
            metadata=metadata
        )
    
    def _format_ticker_info(self, info: Dict[str, Any]) -> str:
        """Format ticker info into readable text."""
        lines = []
        lines.append("COMPANY INFORMATION")
        lines.append("=" * 50)
        
        key_fields = [
            ('Company Name', 'longName'),
            ('Sector', 'sector'),
            ('Industry', 'industry'),
            ('Market Cap', 'marketCap'),
            ('Enterprise Value', 'enterpriseValue'),
            ('P/E Ratio', 'trailingPE'),
            ('Forward P/E', 'forwardPE'),
            ('Price to Book', 'priceToBook'),
            ('Dividend Yield', 'dividendYield'),
            ('Beta', 'beta'),
            ('52 Week High', 'fiftyTwoWeekHigh'),
            ('52 Week Low', 'fiftyTwoWeekLow'),
        ]
        
        for label, key in key_fields:
            value = info.get(key)
            if value is not None:
                if isinstance(value, float):
                    if key in ['marketCap', 'enterpriseValue']:
                        lines.append(f"{label}: ${value:,.0f}")
                    elif key in ['trailingPE', 'forwardPE', 'priceToBook', 'beta']:
                        lines.append(f"{label}: {value:.2f}")
                    elif key == 'dividendYield':
                        lines.append(f"{label}: {value:.2%}")
                    else:
                        lines.append(f"{label}: {value:.2f}")
                else:
                    lines.append(f"{label}: {value}")
        
        return "\n".join(lines)
    
    def _format_historical_data(self, hist: pd.DataFrame, metadata: Dict[str, Any]) -> str:
        """Format historical data into readable text."""
        lines = []
        lines.append("HISTORICAL PRICE DATA")
        lines.append("=" * 50)
        
        lines.append(f"Period: {metadata['period']}")
        lines.append(f"Data Points: {metadata['data_points']}")
        lines.append(f"Latest Price: ${metadata['latest_price']:.2f}")
        lines.append(f"Price Change: ${metadata['price_change']:.2f} ({metadata['price_change_pct']:.2f}%)")
        lines.append(f"Volatility (Annualized): {metadata['volatility']:.2%}")
        
        if metadata['ma_20']:
            lines.append(f"20-Day Moving Average: ${metadata['ma_20']:.2f}")
        if metadata['ma_50']:
            lines.append(f"50-Day Moving Average: ${metadata['ma_50']:.2f}")
        
        lines.append(f"Average Volume: {metadata['volume_avg']:,.0f}")
        
        # Add recent price data
        lines.append("\nRecent Prices:")
        lines.append("-" * 20)
        
        recent_data = hist.tail(5)
        for date, row in recent_data.iterrows():
            lines.append(f"{date.strftime('%Y-%m-%d')}: Open=${row['Open']:.2f}, Close=${row['Close']:.2f}, Volume={row['Volume']:,.0f}")
        
        return "\n".join(lines)
    
    def _format_financial_ratios(self, ratios: Dict[str, Any]) -> str:
        """Format financial ratios into readable text."""
        lines = []
        lines.append("FINANCIAL RATIOS")
        lines.append("=" * 50)
        
        # Group ratios by category
        categories = {
            'Valuation Ratios': ['pe_ratio', 'forward_pe', 'price_to_book', 'price_to_sales', 'enterprise_value_to_ebitda'],
            'Profitability Ratios': ['return_on_equity', 'return_on_assets', 'profit_margin', 'operating_margin'],
            'Financial Strength': ['current_ratio', 'debt_to_equity', 'quick_ratio']
        }
        
        for category, ratio_keys in categories.items():
            lines.append(f"\n{category}:")
            lines.append("-" * len(category))
            
            for key in ratio_keys:
                value = ratios.get(key)
                if value is not None:
                    if isinstance(value, float):
                        if 'margin' in key or 'return' in key:
                            lines.append(f"{key.replace('_', ' ').title()}: {value:.2%}")
                        else:
                            lines.append(f"{key.replace('_', ' ').title()}: {value:.2f}")
                    else:
                        lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(lines)
    
    def _format_earnings_data(self, earnings_data: Dict[str, Any]) -> str:
        """Format earnings data into readable text."""
        lines = []
        lines.append("EARNINGS DATA")
        lines.append("=" * 50)
        
        earnings = earnings_data.get('earnings')
        earnings_dates = earnings_data.get('earnings_dates')
        
        if earnings:
            lines.append(f"Historical Earnings: {len(earnings)} periods")
            if len(earnings) > 0:
                lines.append("\nRecent Earnings:")
                lines.append("-" * 20)
                
                # Get recent earnings data
                recent_earnings = list(earnings.items())[-5:]  # Last 5 periods
                for date, data in recent_earnings:
                    if isinstance(data, dict):
                        eps = data.get('Earnings', 'N/A')
                        revenue = data.get('Revenue', 'N/A')
                        lines.append(f"{date}: EPS={eps}, Revenue={revenue}")
        
        if earnings_dates:
            lines.append(f"\nEarnings Dates: {len(earnings_dates)} dates")
            if len(earnings_dates) > 0:
                lines.append("\nUpcoming Earnings:")
                lines.append("-" * 20)
                
                # Get upcoming earnings dates
                upcoming_dates = list(earnings_dates.items())[-5:]  # Last 5 dates
                for date, data in upcoming_dates:
                    if isinstance(data, dict):
                        eps_estimate = data.get('EPS Estimate', 'N/A')
                        lines.append(f"{date}: EPS Estimate={eps_estimate}")
        
        return "\n".join(lines)
    
    async def cleanup(self):
        """Cleanup resources."""
        # No cleanup needed for yfinance
        pass
    
    def get_supported_periods(self) -> List[str]:
        """Get list of supported time periods."""
        return ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
    
    def get_supported_intervals(self) -> List[str]:
        """Get list of supported data intervals."""
        return ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
    
    def get_data_config(self) -> Dict[str, Any]:
        """Get data configuration."""
        return {
            "default_period": self.config.get("period", "1y"),
            "default_interval": self.config.get("interval", "1d"),
            "max_retries": self.config.get("max_retries", 3)
        }
