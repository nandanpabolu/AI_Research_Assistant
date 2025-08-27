"""
Configuration settings for the AI Research Analyst Agent.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
CACHE_DIR = PROJECT_ROOT / "cache"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Database
DATABASE_PATH = DATA_DIR / "research.db"

# AI Models Configuration
AI_MODELS = {
    "summarization": {
        "primary": "facebook/bart-large-cnn",      # High quality, slower
        "fallback": "sshleifer/distilbart-cnn-12-6",  # Faster, lighter
        "max_length": 130,
        "min_length": 30
    },
    "embeddings": {
        "model": "all-MiniLM-L6-v2",              # Lightweight, fast
        "max_length": 512
    },
    "keyword_extraction": {
        "top_k": 10,
        "diversity": 0.7
    }
}

# Data Sources Configuration
DATA_SOURCES = {
    "sec": {
        "base_url": "https://www.sec.gov/Archives/edgar/data/",
        "user_agent": "AI Research Assistant (your-email@domain.com)",
        "rate_limit_delay": 0.1,  # seconds between requests
        "max_filings": 5,         # max recent filings to analyze
        "filing_types": ["10-K", "10-Q"]
    },
    "news": {
        "rss_feeds": [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.finance.yahoo.com/rss/2.0/headline",
            "https://www.marketwatch.com/rss/topstories",
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://feeds.finance.yahoo.com/rss/2.0/headline?s=aapl&region=US&lang=en-US",
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            "https://feeds.npr.org/1007/rss.xml"
        ],
        "max_articles": 30,
        "article_timeout": 15,    # seconds
        "respect_robots_txt": True
    },
    "market": {
        "data_provider": "yfinance",
        "period": "1y",           # 1 year of historical data
        "interval": "1d",         # daily data
        "max_retries": 3,
        "alternative_sources": [
            "alpha_vantage",      # Free tier available
            "quandl",            # Free tier available
            "finnhub"            # Free tier available
        ]
    }
}

# Processing Configuration
PROCESSING = {
    "text_cleaning": {
        "remove_boilerplate": True,
        "min_chunk_size": 100,
        "max_chunk_size": 2000,
        "overlap": 200
    },
    "analysis": {
        "max_risks": 5,
        "max_opportunities": 5,
        "max_metrics": 10,
        "min_confidence": 0.6
    },
    "caching": {
        "enable": True,
        "ttl_hours": 24,
        "max_cache_size_mb": 100
    }
}

# Export Configuration
EXPORT = {
    "pdf": {
        "page_size": "A4",
        "margin": "1in",
        "font_size": 11,
        "line_height": 1.2
    },
    "pptx": {
        "slide_width": 9.0,      # inches
        "slide_height": 6.75,    # inches
        "title_font_size": 24,
        "body_font_size": 18
    },
    "html": {
        "template": "memo.html",
        "css_file": "styles.css"
    }
}

# UI Configuration
UI = {
    "page_title": "AI Research Analyst Agent",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "max_upload_size": 200,      # MB
    "auto_refresh": False
}

# Logging Configuration
LOGGING = {
    "level": "INFO",
    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    "file": DATA_DIR / "app.log",
    "max_size": "10 MB",
    "rotation": "1 day"
}

# Performance Configuration
PERFORMANCE = {
    "max_concurrent_requests": 5,
    "request_timeout": 30,       # seconds
    "max_analysis_time": 300,    # 5 minutes
    "enable_progress_bars": True,
    "chunk_processing_batch_size": 10
}

# Security Configuration
SECURITY = {
    "allowed_file_types": [".txt", ".pdf", ".html"],
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "enable_rate_limiting": True,
    "max_requests_per_minute": 60
}

def get_config() -> Dict[str, Any]:
    """Get the complete configuration dictionary."""
    return {
        "ai_models": AI_MODELS,
        "data_sources": DATA_SOURCES,
        "processing": PROCESSING,
        "export": EXPORT,
        "ui": UI,
        "logging": LOGGING,
        "performance": PERFORMANCE,
        "security": SECURITY,
        "paths": {
            "project_root": str(PROJECT_ROOT),
            "data_dir": str(DATA_DIR),
            "templates_dir": str(TEMPLATES_DIR),
            "cache_dir": str(CACHE_DIR),
            "database": str(DATABASE_PATH)
        }
    }

def get_model_config(model_type: str) -> Dict[str, Any]:
    """Get configuration for a specific AI model type."""
    return AI_MODELS.get(model_type, {})

def get_data_source_config(source_type: str) -> Dict[str, Any]:
    """Get configuration for a specific data source type."""
    return DATA_SOURCES.get(source_type, {})

def get_export_config(format_type: str) -> Dict[str, Any]:
    """Get configuration for a specific export format."""
    return EXPORT.get(format_type, {})
