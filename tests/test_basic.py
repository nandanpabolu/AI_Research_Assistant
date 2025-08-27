"""
Basic tests for AI Research Assistant
"""

import pytest
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all main modules can be imported"""
    try:
        from core import config
        from models import schemas, database
        from ingestors import base, market_ingestor, news_ingestor, sec_ingestor
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import module: {e}")

def test_config():
    """Test that configuration can be loaded"""
    try:
        from core.config import DATA_SOURCES, PROCESSING, EXPORT
        assert DATA_SOURCES is not None
        assert PROCESSING is not None
        assert EXPORT is not None
    except Exception as e:
        pytest.fail(f"Failed to load configuration: {e}")

def test_schemas():
    """Test that data schemas can be created"""
    try:
        from models.schemas import DataSource, SourceType, RunStatus
        from datetime import datetime
        
        # Test creating a DataSource
        source = DataSource(
            run_id=1,
            type=SourceType.MARKET_DATA,
            url="test://example.com",
            title="Test Source"
        )
        assert source.run_id == 1
        assert source.type == SourceType.MARKET_DATA
    except Exception as e:
        pytest.fail(f"Failed to create schema objects: {e}")

if __name__ == "__main__":
    pytest.main([__file__])



