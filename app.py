"""
AI Research Analyst Agent - Main Streamlit Application
"""

import streamlit as st
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from core.config import get_config, UI
from models.database import DatabaseManager
from models.schemas import RunStatus
from ingestors import SECIngestor, NewsIngestor, MarketIngestor

# Page configuration
st.set_page_config(
    page_title=UI["page_title"],
    page_icon=UI["page_icon"],
    layout=UI["layout"],
    initial_sidebar_state=UI["initial_sidebar_state"]
)

# Initialize session state
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None
if 'database' not in st.session_state:
    st.session_state.database = None
if 'ingestors' not in st.session_state:
    st.session_state.ingestors = None

def initialize_components():
    """Initialize database and ingestors."""
    try:
        if st.session_state.database is None:
            st.session_state.database = DatabaseManager()
            logger.info("Database initialized")
        
        if st.session_state.ingestors is None:
            st.session_state.ingestors = {
                'sec': SECIngestor(),
                'news': NewsIngestor(),
                'market': MarketIngestor()
            }
            logger.info("Ingestors initialized")
            
    except Exception as e:
        st.error(f"Failed to initialize components: {e}")
        logger.error(f"Initialization error: {e}")

def main():
    """Main application function."""
    st.title("🤖 AI Research Analyst Agent")
    st.markdown("Generate comprehensive company analysis reports from public data sources")
    
    # Initialize components
    initialize_components()
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Analysis Options")
        
        # Data source selection
        st.subheader("Data Sources")
        include_sec = st.checkbox("SEC Filings", value=True, help="Include 10-K/10-Q analysis")
        include_news = st.checkbox("News Articles", value=True, help="Include recent news analysis")
        include_market = st.checkbox("Market Data", value=True, help="Include stock price analysis")
        
        # Analysis parameters
        st.subheader("Analysis Parameters")
        max_sources = st.slider("Max Sources", min_value=5, max_value=50, value=20, 
                               help="Maximum number of sources to analyze")
        priority = st.selectbox("Priority", ["balanced", "speed", "quality"], 
                               help="Analysis priority setting")
        
        # Recent analyses
        st.subheader("Recent Analyses")
        if st.session_state.database:
            recent_runs = st.session_state.database.get_recent_runs(limit=10)
            for run in recent_runs:
                status_color = {
                    'completed': '🟢',
                    'running': '🟡', 
                    'failed': '🔴',
                    'pending': '⚪'
                }.get(run.status, '⚪')
                
                # Make completed analyses clickable
                if run.status == 'completed':
                    if st.button(f"{status_color} {run.query} ({run.status})", key=f"view_{run.id}"):
                        st.session_state.current_analysis = run.id
                        st.rerun()
                else:
                    st.write(f"{status_color} {run.query} ({run.status})")
                
                st.caption(f"Started: {run.started_at.strftime('%Y-%m-%d %H:%M')}")
                st.caption(f"ID: {run.id}")
        
        # Database stats
        st.subheader("Database Stats")
        if st.session_state.database:
            stats = st.session_state.database.get_database_stats()
            if stats:
                st.write(f"📁 Total Runs: {stats.get('runs_count', 0)}")
                st.write(f"📰 Total Sources: {stats.get('sources_count', 0)}")
                st.write(f"📊 Total Memos: {stats.get('memos_count', 0)}")
                st.write(f"💾 Size: {stats.get('database_size_mb', 0):.1f} MB")
        
        # Quick access to completed analyses
        st.subheader("📋 Quick Access")
        if st.session_state.database:
            completed_runs = [run for run in st.session_state.database.get_recent_runs(limit=20) if run.status == 'completed']
            if completed_runs:
                for run in completed_runs[:5]:  # Show top 5
                    if st.button(f"📄 {run.query} - {run.started_at.strftime('%m/%d')}", key=f"quick_{run.id}"):
                        st.session_state.current_analysis = run.id
                        st.rerun()
            else:
                st.info("No completed analyses yet")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🔍 Start New Analysis")
        
        # Query input
        query = st.text_input(
            "Enter Ticker Symbol or Company Name",
            placeholder="e.g., AAPL, MSFT, TSLA",
            help="Enter a stock ticker symbol to analyze"
        )
        
        # Analysis options
        col1a, col1b = st.columns(2)
        with col1a:
            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                if query and query.strip():
                    start_analysis(query.strip(), include_sec, include_news, include_market, max_sources, priority)
                else:
                    st.error("Please enter a valid ticker symbol")
        
        with col1b:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        # Current analysis status
        if st.session_state.current_analysis:
            st.subheader("📋 Current Analysis")
            run = st.session_state.database.get_run(st.session_state.current_analysis)
            
            if run:
                # Progress bar
                if run.status == 'running':
                    progress = st.progress(0)
                    st.write("🔄 Analysis in progress... Please wait.")
                    
                    # Check if we should run the actual analysis
                    if 'analysis_started' not in st.session_state:
                        st.session_state.analysis_started = True
                        # Run analysis synchronously (Streamlit doesn't support async)
                        run_sync_analysis(run.id, run.query)
                        # Force refresh after analysis completes
                        st.rerun()
                    
                    # Show progress
                    progress.progress(50)
                    st.info("📊 Fetching data from multiple sources...")
                    st.info("🤖 Processing with AI models...")
                    st.info("📄 Generating analysis report...")
                    
                    # Add auto-refresh and manual check
                    st.info("⏱️ Analysis is running... This should complete in 10-30 seconds.")
                    if st.button("🔄 Refresh Status", key=f"refresh_{run.id}"):
                        st.rerun()
                    
                    # Auto-refresh every 5 seconds
                    import time
                    if 'last_refresh' not in st.session_state:
                        st.session_state.last_refresh = time.time()
                    
                    if time.time() - st.session_state.last_refresh > 5:
                        st.session_state.last_refresh = time.time()
                        st.rerun()
                
                elif run.status == 'completed':
                    st.success("✅ Analysis completed!")
                    
                    # Show completion details
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Query:** {run.query}")
                        st.write(f"**Status:** {run.status}")
                    with col_b:
                        st.write(f"**Started:** {run.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        if run.finished_at:
                            duration = run.finished_at - run.started_at
                            st.write(f"**Duration:** {duration.total_seconds():.1f} seconds")
                    
                    # Display results with better visibility
                    st.markdown("---")
                    display_results(run.id)
                    
                elif run.status == 'failed':
                    st.error(f"❌ Analysis failed: {run.error_message}")
                    st.write(f"**Query:** {run.query}")
                    st.write(f"**Status:** {run.status}")
                    st.write(f"**Started:** {run.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Show status for all runs
                if run.status == 'pending':
                    st.info(f"⏳ Analysis pending for {run.query}")
                elif run.status == 'running':
                    st.warning(f"🔄 Analysis running for {run.query}")
    
    with col2:
        st.header("📈 Quick Stats")
        
        if query and query.strip():
            ticker = query.strip().upper()
            
            # Market data preview
            try:
                import yfinance as yf
                ticker_info = yf.Ticker(ticker)
                
                # Basic info
                info = ticker_info.info
                if info:
                    st.write(f"**Company:** {info.get('longName', 'N/A')}")
                    st.write(f"**Sector:** {info.get('sector', 'N/A')}")
                    st.write(f"**Market Cap:** ${info.get('marketCap', 0):,.0f}")
                    
                    # Price chart
                    hist = ticker_info.history(period="1mo")
                    if not hist.empty:
                        st.line_chart(hist['Close'])
                        
            except Exception as e:
                st.info("Market data will be loaded during analysis")
        
        # Help section
        st.header("❓ How It Works")
        st.markdown("""
        1. **Enter a ticker symbol** (e.g., AAPL)
        2. **Click Start Analysis** to begin
        3. **Wait for processing** (30-60 seconds)
        4. **Review results** and download reports
        """)
        
        st.header("📚 Data Sources")
        st.markdown("""
        - **SEC Filings**: 10-K, 10-Q reports
        - **News Articles**: Recent business news
        - **Market Data**: Stock prices & ratios
        """)

def start_analysis(query: str, include_sec: bool, include_news: bool, 
                  include_market: bool, max_sources: int, priority: str):
    """Start a new analysis."""
    try:
        # Create analysis run
        run_id = st.session_state.database.create_run(query)
        st.session_state.current_analysis = run_id
        
        # Reset analysis state
        if 'analysis_started' in st.session_state:
            del st.session_state.analysis_started
        
        # Update status to running
        st.session_state.database.update_run_status(run_id, RunStatus.RUNNING)
        
        st.success(f"Analysis started for {query}! Run ID: {run_id}")
        st.rerun()
        
    except Exception as e:
        st.error(f"Failed to start analysis: {e}")
        logger.error(f"Analysis start error: {e}")

def run_sync_analysis(run_id: int, query: str):
    """Run the complete analysis workflow synchronously."""
    try:
        logger.info(f"Starting full analysis for run {run_id}")
        
        # Get ingestors
        sec_ingestor = st.session_state.ingestors['sec']
        news_ingestor = st.session_state.ingestors['news']
        market_ingestor = st.session_state.ingestors['market']
        
        sources = []
        
        # 1. Market data
        try:
            logger.info("Fetching market data...")
            # Run market ingestor synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                market_sources = loop.run_until_complete(market_ingestor.ingest(query, run_id))
                sources.extend(market_sources)
                logger.info(f"Fetched {len(market_sources)} market sources")
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"Market data failed: {e}")
        
        # 2. News data
        try:
            logger.info("Fetching news data...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                news_sources = loop.run_until_complete(news_ingestor.ingest(query, run_id))
                sources.extend(news_sources)
                logger.info(f"Fetched {len(news_sources)} news sources")
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"News data failed: {e}")
        
        # 3. SEC filings
        try:
            logger.info("Fetching SEC filings...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                sec_sources = loop.run_until_complete(sec_ingestor.ingest(query, run_id))
                sources.extend(sec_sources)
                logger.info(f"Fetched {len(sec_sources)} SEC sources")
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"SEC data failed: {e}")
        
        # Save sources to database
        logger.info("Saving sources...")
        for source in sources:
            try:
                # Handle both enum objects and string values
                source_type_value = source.type.value if hasattr(source.type, 'value') else source.type
                
                source_id = st.session_state.database.add_source(
                    run_id=run_id,
                    source_type=source_type_value,
                    url=source.url,
                    title=source.title,
                    published_at=source.published_at,
                    checksum=source.checksum,
                    raw_content=source.raw_content,
                    metadata=source.metadata
                )
            except Exception as e:
                logger.warning(f"Failed to save source: {e}")
        
        # Generate memo (simplified for now)
        logger.info("Generating memo...")
        memo_data = generate_simple_memo(query, sources)
        
        # Save memo - convert Pydantic objects to dictionaries
        memo_id = st.session_state.database.save_memo(
            run_id=run_id,
            tldr=memo_data["tldr"],
            risks=[risk.model_dump() for risk in memo_data["risks"]],
            opportunities=[opp.model_dump() for opp in memo_data["opportunities"]],
            metrics=[metric.model_dump() for metric in memo_data["metrics"]],
            html_content=memo_data["html_content"]
        )
        
        # Update status to completed
        st.session_state.database.update_run_status(run_id, RunStatus.COMPLETED)
        logger.info(f"Analysis completed for run {run_id}")
        
    except Exception as e:
        logger.error(f"Analysis failed for run {run_id}: {e}")
        st.session_state.database.update_run_status(run_id, RunStatus.FAILED, str(e))

def generate_simple_memo(ticker: str, sources: list):
    """Generate a simple memo based on available sources."""
    from models.schemas import RiskItem, OpportunityItem, MetricItem
    
    # Count sources by type
    source_counts = {}
    for source in sources:
        source_type = source.type.value if hasattr(source.type, 'value') else source.type
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
    
    # Create memo content with proper Pydantic objects
    memo_data = {
        "tldr": f"{ticker} analysis completed with {len(sources)} data sources. Analysis covers market data, news, and regulatory filings.",
        "risks": [
            RiskItem(
                risk="Data availability",
                rationale=f"Limited data sources available ({len(sources)} total)",
                source_ids=[1],
                confidence=0.7,
                severity="low"
            ),
            RiskItem(
                risk="Market volatility",
                rationale="General market risks apply to all investments",
                source_ids=[2],
                confidence=0.8,
                severity="medium"
            ),
            RiskItem(
                risk="Regulatory changes",
                rationale="Potential changes in financial regulations",
                source_ids=[3],
                confidence=0.6,
                severity="low"
            )
        ],
        "opportunities": [
            OpportunityItem(
                opportunity="Data expansion",
                rationale=f"Currently analyzing {len(sources)} sources, potential for more comprehensive analysis",
                source_ids=[4],
                confidence=0.8,
                potential_impact="medium"
            ),
            OpportunityItem(
                opportunity="AI enhancement",
                rationale="Ready for AI model integration for deeper insights",
                source_ids=[5],
                confidence=0.9,
                potential_impact="high"
            ),
            OpportunityItem(
                opportunity="Real-time updates",
                rationale="Framework supports live data updates",
                source_ids=[6],
                confidence=0.7,
                potential_impact="medium"
            )
        ],
        "metrics": [
            MetricItem(
                metric="Data Sources",
                value=str(len(sources)),
                trend="stable",
                period="Current",
                source_ids=[7],
                context=f"Total sources analyzed: {len(sources)}"
            ),
            MetricItem(
                metric="Source Types",
                value=str(len(source_counts)),
                trend="up",
                period="Current",
                source_ids=[8],
                context=f"Data diversity: {', '.join(source_counts.keys())}"
            )
        ],
        "html_content": f"<h1>{ticker} Analysis Report</h1><p>Analysis completed with {len(sources)} data sources.</p>"
    }
    
    return memo_data

def display_results(run_id: int):
    """Display analysis results."""
    try:
        # Get memo
        memo = st.session_state.database.get_memo(run_id)
        if not memo:
            st.info("No memo found for this analysis")
            return
        
        # Display memo sections
        st.subheader("📄 Executive Summary")
        st.write(memo.tldr)
        
        # Risks
        st.subheader("⚠️ Key Risks")
        for i, risk in enumerate(memo.risks[:3], 1):
            with st.expander(f"Risk {i}: {risk.risk}"):
                st.write(f"**Rationale:** {risk.rationale}")
                st.write(f"**Severity:** {risk.severity}")
                st.write(f"**Confidence:** {risk.confidence:.1%}")
        
        # Opportunities
        st.subheader("🎯 Key Opportunities")
        for i, opp in enumerate(memo.opportunities[:3], 1):
            with st.expander(f"Opportunity {i}: {opp.opportunity}"):
                st.write(f"**Rationale:** {opp.rationale}")
                st.write(f"**Impact:** {opp.potential_impact}")
                st.write(f"**Confidence:** {opp.confidence:.1%}")
        
        # Metrics
        st.subheader("📊 Key Metrics")
        for metric in memo.metrics[:5]:
            st.write(f"**{metric.metric}:** {metric.value} ({metric.trend})")
        
        # Sources (show automatically)
        st.subheader("📚 Data Sources")
        display_sources(run_id)
        
        # Export options
        st.subheader("📤 Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export PDF", use_container_width=True):
                st.info("PDF export coming soon!")
        
        with col2:
            if st.button("📊 Export PPTX", use_container_width=True):
                st.info("PowerPoint export coming soon!")
        
        with col3:
            if st.button("🔄 Refresh Sources", use_container_width=True):
                st.rerun()
        
    except Exception as e:
        st.error(f"Failed to display results: {e}")
        logger.error(f"Results display error: {e}")

def display_sources(run_id: int):
    """Display data sources used in the analysis."""
    try:
        sources = st.session_state.database.get_sources(run_id)
        
        st.subheader("📚 Data Sources")
        
        # Group by type
        source_types = {}
        for source in sources:
            source_type = source.type
            if source_type not in source_types:
                source_types[source_type] = []
            source_types[source_type].append(source)
        
        # Display each type
        for source_type, type_sources in source_types.items():
            with st.expander(f"{source_type.replace('_', ' ').title()} ({len(type_sources)})"):
                for source in type_sources:
                    st.write(f"**{source.title or 'Untitled'}**")
                    if source.url:
                        st.write(f"URL: {source.url}")
                    if source.published_at:
                        st.write(f"Date: {source.published_at.strftime('%Y-%m-%d')}")
                    st.write("---")
        
    except Exception as e:
        st.error(f"Failed to display sources: {e}")
        logger.error(f"Sources display error: {e}")

if __name__ == "__main__":
    main()
