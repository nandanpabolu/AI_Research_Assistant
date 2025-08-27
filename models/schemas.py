"""
Pydantic schemas for data validation and structure.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, validator

class RunStatus(str, Enum):
    """Status of an analysis run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SourceType(str, Enum):
    """Type of data source."""
    SEC_FILING = "sec_filing"
    NEWS_ARTICLE = "news_article"
    MARKET_DATA = "market_data"
    RSS_FEED = "rss_feed"

class AnalysisRun(BaseModel):
    """Represents an analysis run."""
    id: Optional[int] = None
    query: str = Field(..., description="Ticker symbol or search query")
    started_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    status: RunStatus = Field(default=RunStatus.PENDING)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class DataSource(BaseModel):
    """Represents a data source."""
    id: Optional[int] = None
    run_id: int = Field(..., description="ID of the analysis run")
    type: SourceType = Field(..., description="Type of data source")
    url: Optional[str] = Field(None, description="URL of the source")
    title: Optional[str] = Field(None, description="Title or description")
    published_at: Optional[datetime] = None
    checksum: Optional[str] = Field(None, description="Content hash for deduplication")
    raw_content: Optional[str] = Field(None, description="Raw content from source")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class TextChunk(BaseModel):
    """Represents a processed text chunk."""
    id: Optional[int] = None
    source_id: int = Field(..., description="ID of the data source")
    text: str = Field(..., description="Processed text content")
    chunk_type: str = Field(..., description="Type of chunk (summary, risk, opportunity, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

class RiskItem(BaseModel):
    """Represents a risk item."""
    risk: str = Field(..., description="Description of the risk")
    rationale: str = Field(..., description="Explanation of why this is a risk")
    source_ids: List[int] = Field(default_factory=list, description="Source document IDs")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    severity: str = Field(..., description="Risk severity (low, medium, high, critical)")

class OpportunityItem(BaseModel):
    """Represents an opportunity item."""
    opportunity: str = Field(..., description="Description of the opportunity")
    rationale: str = Field(..., description="Explanation of why this is an opportunity")
    source_ids: List[int] = Field(default_factory=list, description="Source document IDs")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    potential_impact: str = Field(..., description="Potential impact (low, medium, high, transformative)")

class MetricItem(BaseModel):
    """Represents a financial or business metric."""
    metric: str = Field(..., description="Name of the metric")
    value: str = Field(..., description="Current value")
    trend: str = Field(..., description="Trend direction (up, down, stable)")
    period: str = Field(..., description="Time period for the metric")
    source_ids: List[int] = Field(default_factory=list, description="Source document IDs")
    context: Optional[str] = Field(None, description="Additional context")

class Memo(BaseModel):
    """Represents a generated analyst memo."""
    id: Optional[int] = None
    run_id: int = Field(..., description="ID of the analysis run")
    tldr: str = Field(..., description="Executive summary (4-6 lines)")
    risks: List[RiskItem] = Field(default_factory=list, description="Key risks")
    opportunities: List[OpportunityItem] = Field(default_factory=list, description="Key opportunities")
    metrics: List[MetricItem] = Field(default_factory=list, description="Key metrics")
    html_content: str = Field(..., description="Formatted HTML content")
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('risks')
    def validate_risks(cls, v):
        """Ensure we have at least 3 risks."""
        if len(v) < 3:
            raise ValueError("Must have at least 3 risks")
        return v
    
    @validator('opportunities')
    def validate_opportunities(cls, v):
        """Ensure we have at least 3 opportunities."""
        if len(v) < 3:
            raise ValueError("Must have at least 3 opportunities")
        return v

class AnalysisRequest(BaseModel):
    """Request for a new analysis."""
    query: str = Field(..., description="Ticker symbol or search query")
    include_sec: bool = Field(default=True, description="Include SEC filings analysis")
    include_news: bool = Field(default=True, description="Include news analysis")
    include_market: bool = Field(default=True, description="Include market data analysis")
    max_sources: int = Field(default=20, ge=5, le=50, description="Maximum number of sources to analyze")
    priority: str = Field(default="balanced", description="Analysis priority (speed, quality, balanced)")

class AnalysisResponse(BaseModel):
    """Response from an analysis request."""
    run_id: int = Field(..., description="ID of the analysis run")
    status: RunStatus = Field(..., description="Current status")
    estimated_completion: Optional[datetime] = None
    message: str = Field(..., description="Status message")

class ExportRequest(BaseModel):
    """Request for exporting analysis results."""
    run_id: int = Field(..., description="ID of the analysis run")
    format: str = Field(..., description="Export format (pdf, pptx, html)")
    include_sources: bool = Field(default=True, description="Include sources table")
    include_charts: bool = Field(default=True, description="Include charts and visualizations")



