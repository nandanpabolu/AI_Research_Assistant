"""
Base ingestor interface for data sources.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging

from models.schemas import DataSource, SourceType

logger = logging.getLogger(__name__)

class BaseIngestor(ABC):
    """Base class for all data ingestors."""
    
    def __init__(self, source_type: SourceType):
        """Initialize the ingestor."""
        self.source_type = source_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def ingest(self, query: str, run_id: int = 0, **kwargs) -> List[DataSource]:
        """
        Ingest data for the given query.
        
        Args:
            query: The search query (e.g., ticker symbol)
            run_id: ID of the analysis run
            **kwargs: Additional parameters specific to the ingestor
            
        Returns:
            List of DataSource objects
        """
        pass
    
    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """
        Check if this ingestor can handle the given query.
        
        Args:
            query: The search query
            
        Returns:
            True if the ingestor can handle this query
        """
        pass
    
    async def process_with_retry(self, func, *args, max_retries: int = 3, 
                               delay: float = 1.0, **kwargs):
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
        
        self.logger.error(f"All {max_retries} attempts failed")
        raise last_exception
    
    def validate_query(self, query: str) -> bool:
        """
        Validate the query format.
        
        Args:
            query: The search query
            
        Returns:
            True if query is valid
        """
        if not query or not query.strip():
            return False
        
        # Basic validation - can be overridden by subclasses
        return len(query.strip()) >= 1
    
    def create_source(self, run_id: int, url: Optional[str] = None, title: Optional[str] = None,
                      published_at: Optional[datetime] = None, 
                      raw_content: Optional[str] = None,
                      checksum: Optional[str] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> DataSource:
        """
        Create a DataSource object.
        
        Args:
            run_id: ID of the analysis run
            url: Source URL
            title: Source title
            published_at: Publication date
            raw_content: Raw content
            metadata: Additional metadata
            
        Returns:
            DataSource object
        """
        return DataSource(
            run_id=run_id,
            type=self.source_type,
            url=url,
            title=title,
            published_at=published_at,
            raw_content=raw_content,
            checksum=checksum,
            metadata=metadata or {}
        )
    
    def log_ingestion_summary(self, sources: List[DataSource], query: str):
        """
        Log a summary of the ingestion process.
        
        Args:
            sources: List of ingested sources
            query: The original query
        """
        self.logger.info(
            f"Ingested {len(sources)} sources for query '{query}' "
            f"from {self.source_type.value if hasattr(self.source_type, 'value') else self.source_type}"
        )
        
        if sources:
            source_types = {}
            for source in sources:
                source_type = source.type
                source_types[source_type] = source_types.get(source_type, 0) + 1
            
            for source_type, count in source_types.items():
                self.logger.debug(f"  - {source_type}: {count}")
    
    async def cleanup(self):
        """
        Cleanup resources used by the ingestor.
        Override in subclasses if needed.
        """
        pass
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.source_type.value if hasattr(self.source_type, 'value') else self.source_type})"
    
    def __repr__(self):
        return self.__str__()
