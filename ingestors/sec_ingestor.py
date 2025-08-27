"""
SEC EDGAR ingestor for company filings.
"""

import asyncio
import hashlib
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

try:
    from sec_edgar_downloader import Downloader
except ImportError:
    Downloader = None

from .base import BaseIngestor
from models.schemas import DataSource, SourceType
from core.config import get_data_source_config

logger = logging.getLogger(__name__)

class SECIngestor(BaseIngestor):
    """Ingestor for SEC EDGAR filings."""
    
    def __init__(self):
        """Initialize the SEC ingestor."""
        super().__init__(SourceType.SEC_FILING)
        self.config = get_data_source_config("sec")
        self.downloader = None
        self._init_downloader()
    
    def _init_downloader(self):
        """Initialize the SEC downloader."""
        try:
            if Downloader is None:
                raise ImportError("sec-edgar-downloader not available")
            
            # Create download directory
            download_dir = Path("cache/sec_filings")
            download_dir.mkdir(parents=True, exist_ok=True)
            
            self.downloader = Downloader(
                user_agent=self.config.get("user_agent", "AI Research Assistant"),
                download_folder=str(download_dir)
            )
            self.logger.info("SEC downloader initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SEC downloader: {e}")
            self.downloader = None
    
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
        
        # Check if it's a valid ticker format (1-5 alphanumeric characters)
        ticker_pattern = re.compile(r'^[A-Z]{1,5}$')
        return bool(ticker_pattern.match(query.strip().upper()))
    
    async def ingest(self, query: str, run_id: int = 0, **kwargs) -> List[DataSource]:
        """
        Ingest SEC filings for the given ticker.
        
        Args:
            query: Ticker symbol (e.g., "AAPL")
            **kwargs: Additional parameters
            
        Returns:
            List of DataSource objects
        """
        if not self.can_handle(query):
            self.logger.warning(f"Cannot handle query: {query}")
            return []
        
        if not self.downloader:
            self.logger.error("SEC downloader not available")
            return []
        
        ticker = query.strip().upper()
        max_filings = kwargs.get("max_filings", self.config.get("max_filings", 5))
        filing_types = kwargs.get("filing_types", self.config.get("filing_types", ["10-K", "10-Q"]))
        
        self.logger.info(f"Starting SEC ingestion for {ticker}")
        
        try:
            sources = []
            
            for filing_type in filing_types:
                filing_sources = await self._download_filings(
                    ticker, filing_type, max_filings // len(filing_types)
                )
                sources.extend(filing_sources)
                
                # Rate limiting between filing types
                if len(filing_types) > 1:
                    await asyncio.sleep(self.config.get("rate_limit_delay", 0.1))
            
            self.log_ingestion_summary(sources, ticker)
            return sources
            
        except Exception as e:
            self.logger.error(f"SEC ingestion failed for {ticker}: {e}")
            return []
    
    async def _download_filings(self, ticker: str, filing_type: str, 
                               max_filings: int) -> List[DataSource]:
        """
        Download filings of a specific type.
        
        Args:
            ticker: Ticker symbol
            filing_type: Type of filing (10-K, 10-Q, etc.)
            max_filings: Maximum number of filings to download
            
        Returns:
            List of DataSource objects
        """
        sources = []
        
        try:
            # Download filings
            downloaded_files = await self._download_filing_files(ticker, filing_type, max_filings)
            
            for file_path in downloaded_files:
                try:
                    source = await self._process_filing_file(file_path, ticker, filing_type)
                    if source:
                        sources.append(source)
                except Exception as e:
                    self.logger.warning(f"Failed to process filing {file_path}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Failed to download {filing_type} filings for {ticker}: {e}")
        
        return sources
    
    async def _download_filing_files(self, ticker: str, filing_type: str, 
                                   max_filings: int) -> List[Path]:
        """
        Download filing files from SEC.
        
        Args:
            ticker: Ticker symbol
            filing_type: Type of filing
            max_filings: Maximum number of filings
            
        Returns:
            List of downloaded file paths
        """
        def download_filings():
            try:
                # Get the number of filings to download
                count = min(max_filings, 10)  # SEC downloader limit
                
                # Download filings
                self.downloader.get(filing_type, ticker, count)
                
                # Find downloaded files
                download_dir = Path("cache/sec_filings") / ticker / filing_type
                if download_dir.exists():
                    return list(download_dir.glob("*.txt"))
                return []
                
            except Exception as e:
                self.logger.error(f"Download failed: {e}")
                return []
        
        # Run download in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(None, download_filings)
        
        self.logger.info(f"Downloaded {len(files)} {filing_type} files for {ticker}")
        return files
    
    async def _process_filing_file(self, file_path: Path, ticker: str, 
                                 filing_type: str) -> Optional[DataSource]:
        """
        Process a downloaded filing file.
        
        Args:
            file_path: Path to the filing file
            ticker: Ticker symbol
            filing_type: Type of filing
            
        Returns:
            DataSource object or None if processing fails
        """
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Extract filing metadata
            metadata = self._extract_filing_metadata(content, ticker, filing_type)
            
            # Generate checksum
            checksum = hashlib.md5(content.encode()).hexdigest()
            
            # Create source
            source = self.create_source(
                url=f"file://{file_path}",
                title=f"{ticker} {filing_type} - {metadata.get('filing_date', 'Unknown Date')}",
                published_at=metadata.get('filing_date'),
                raw_content=content,
                metadata=metadata
            )
            
            return source
            
        except Exception as e:
            self.logger.error(f"Failed to process filing {file_path}: {e}")
            return None
    
    def _extract_filing_metadata(self, content: str, ticker: str, 
                                filing_type: str) -> Dict[str, Any]:
        """
        Extract metadata from filing content.
        
        Args:
            content: Filing content
            ticker: Ticker symbol
            filing_type: Type of filing
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            "ticker": ticker,
            "filing_type": filing_type,
            "file_size": len(content),
            "extracted_at": datetime.now().isoformat()
        }
        
        try:
            # Extract filing date
            date_pattern = r'<FILING-DATE>(\d{4}-\d{2}-\d{2})</FILING-DATE>'
            date_match = re.search(date_pattern, content)
            if date_match:
                metadata["filing_date"] = datetime.fromisoformat(date_match.group(1))
            
            # Extract company name
            company_pattern = r'<COMPANY-CONFORMED-NAME>([^<]+)</COMPANY-CONFORMED-NAME>'
            company_match = re.search(company_pattern, content)
            if company_match:
                metadata["company_name"] = company_match.group(1).strip()
            
            # Extract CIK (Central Index Key)
            cik_pattern = r'<CIK>(\d+)</CIK>'
            cik_match = re.search(cik_pattern, content)
            if cik_match:
                metadata["cik"] = cik_match.group(1)
            
            # Extract document type
            doc_pattern = r'<TYPE>([^<]+)</TYPE>'
            doc_match = re.search(doc_pattern, content)
            if doc_match:
                metadata["document_type"] = doc_match.group(1).strip()
            
            # Extract accession number
            acc_pattern = r'<ACCESSION-NUMBER>([^<]+)</ACCESSION-NUMBER>'
            acc_match = re.search(acc_pattern, content)
            if acc_match:
                metadata["accession_number"] = acc_match.group(1).strip()
                
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata: {e}")
        
        return metadata
    
    def _clean_filing_content(self, content: str) -> str:
        """
        Clean filing content by removing boilerplate.
        
        Args:
            content: Raw filing content
            
        Returns:
            Cleaned content
        """
        # Remove XML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove multiple spaces and newlines
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common boilerplate
        boilerplate_patterns = [
            r'UNITED STATES SECURITIES AND EXCHANGE COMMISSION.*?Washington, D.C\.\s*\d+',
            r'FORM\s+\d+[-\w]*\s*[-–]\s*.*?REPORT',
            r'PURSUANT TO SECTION\s+\d+.*?OF THE SECURITIES EXCHANGE ACT OF 1934',
            r'For the.*?ended.*?\d+',
            r'Commission File Number:\s*\d+[-–]\d+',
            r'\(Exact name of registrant as specified in its charter\)',
        ]
        
        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)
        
        return content.strip()
    
    async def cleanup(self):
        """Cleanup downloaded files."""
        try:
            if self.downloader:
                # Clean up cache directory
                cache_dir = Path("cache/sec_filings")
                if cache_dir.exists():
                    import shutil
                    shutil.rmtree(cache_dir)
                    self.logger.info("Cleaned up SEC filing cache")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup SEC ingestor: {e}")
    
    def get_supported_filing_types(self) -> List[str]:
        """Get list of supported filing types."""
        return self.config.get("filing_types", ["10-K", "10-Q"])
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """Get rate limiting information."""
        return {
            "delay_between_requests": self.config.get("rate_limit_delay", 0.1),
            "max_concurrent_downloads": 1,  # SEC requires sequential downloads
            "user_agent": self.config.get("user_agent", "AI Research Assistant")
        }
