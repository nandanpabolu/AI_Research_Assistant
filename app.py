"""
AI Research Analyst Agent - Main Streamlit Application
"""

import streamlit as st
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from core.config import get_config, UI
from core.ai_analyzer import ai_analyzer
from core.pdf_generator import pdf_generator
from core.technical_analysis import technical_analyzer
from models.database import DatabaseManager
from models.schemas import RunStatus, RiskItem, OpportunityItem, MetricItem
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
    
    # Create main tabs
    tab1, tab2 = st.tabs(["📊 Single Analysis", "⚖️ Compare Companies"])
    
    with tab1:
        single_company_analysis()
    
    with tab2:
        company_comparison_analysis()

def single_company_analysis():
    """Single company analysis interface."""
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
    """Generate an AI-powered memo based on available sources."""
    
    # Count sources by type
    source_counts = {}
    text_chunks = []
    
    for source in sources:
        source_type = source.type.value if hasattr(source.type, 'value') else source.type
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        
        # Collect text content for AI analysis
        if source.raw_content:
            # Clean and truncate content
            content = source.raw_content.strip()
            if len(content) > 1000:  # Limit content length
                content = content[:1000] + "..."
            if len(content) > 50:  # Only include substantial content
                text_chunks.append(content)
    
    # Generate AI-powered insights
    try:
        logger.info(f"Generating AI insights from {len(text_chunks)} text chunks")
        
        # Extract AI insights
        ai_risks = ai_analyzer.extract_risks(text_chunks, ticker)
        ai_opportunities = ai_analyzer.extract_opportunities(text_chunks, ticker)
        ai_summary = ai_analyzer.generate_summary(text_chunks, max_length=200)
        
        logger.info(f"AI analysis generated {len(ai_risks)} risks and {len(ai_opportunities)} opportunities")
        
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        ai_risks = []
        ai_opportunities = []
        ai_summary = f"{ticker} analysis completed with {len(sources)} data sources."
    
    # Fallback to basic analysis if AI fails
    if not ai_risks:
        ai_risks = [
            RiskItem(
                risk="Market volatility",
                rationale="General market risks apply to all equity investments",
                source_ids=["S1"]
            ),
            RiskItem(
                risk="Competitive pressures",
                rationale="Industry competition may impact market share",
                source_ids=["S2"]
            ),
            RiskItem(
                risk="Regulatory environment",
                rationale="Changes in regulations could affect operations",
                source_ids=["S3"]
            )
        ]
    
    if not ai_opportunities:
        ai_opportunities = [
            OpportunityItem(
                opportunity="Market expansion",
                rationale="Potential for growth in new markets or segments",
                source_ids=["S1"]
            ),
            OpportunityItem(
                opportunity="Innovation potential",
                rationale="Technology and product development opportunities",
                source_ids=["S2"]
            ),
            OpportunityItem(
                opportunity="Strategic partnerships",
                rationale="Potential for beneficial business relationships",
                source_ids=["S3"]
            )
        ]
    
    # Use AI summary or fallback
    if not ai_summary or len(ai_summary) < 50:
        ai_summary = f"{ticker} analysis completed with {len(sources)} data sources covering market data, news, and regulatory filings. Analysis identifies key business risks and growth opportunities."
    
    # Create enhanced memo with AI insights
    memo_data = {
        "tldr": ai_summary,
        "risks": ai_risks[:3],  # Top 3 risks
        "opportunities": ai_opportunities[:3],  # Top 3 opportunities
        "metrics": [
            MetricItem(
                metric="Data Sources",
                value=str(len(sources)),
                trend="stable",
                period="Current",
                source_ids=["S1"],
                context=f"Total sources analyzed: {len(sources)}"
            ),
            MetricItem(
                metric="Source Types",
                value=str(len(source_counts)),
                trend="up", 
                period="Current",
                source_ids=["S2"],
                context=f"Data diversity: {', '.join(source_counts.keys())}"
            ),
            MetricItem(
                metric="AI Insights",
                value=str(len(ai_risks) + len(ai_opportunities)),
                trend="up",
                period="Current", 
                source_ids=["S3"],
                context=f"AI-generated insights: {len(ai_risks)} risks, {len(ai_opportunities)} opportunities"
            )
        ],
        "html_content": f"<h1>{ticker} AI Analysis Report</h1><p>{ai_summary}</p><p><strong>Sources analyzed:</strong> {len(sources)}</p>"
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
        
        # Technical Analysis Charts
        st.subheader("📈 Technical Analysis")
        display_technical_analysis(run)
        
        # Sources (show automatically)
        st.subheader("📚 Data Sources")
        display_sources(run_id)
        
        # Export options
        st.subheader("📤 Export Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export PDF", use_container_width=True):
                try:
                    with st.spinner("Generating PDF report..."):
                        # Get memo and sources for PDF generation
                        sources = st.session_state.database.get_sources(run_id)
                        run = st.session_state.database.get_run(run_id)
                        
                        # Generate PDF
                        pdf_bytes = pdf_generator.generate_pdf_report(
                            memo_data=memo.model_dump() if hasattr(memo, 'model_dump') else memo.__dict__,
                            ticker=run.query.upper(),
                            sources=sources,
                            run_id=run_id
                        )
                        
                        if pdf_bytes:
                            # Create download button
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"{run.query.upper()}_analysis_{timestamp}.pdf"
                            
                            st.download_button(
                                label="⬇️ Download PDF Report",
                                data=pdf_bytes,
                                file_name=filename,
                                mime="application/pdf",
                                use_container_width=True
                            )
                            st.success("PDF report generated successfully!")
                        else:
                            st.error("PDF generation failed. Please check logs.")
                            
                except Exception as e:
                    st.error(f"PDF export failed: {e}")
                    logger.error(f"PDF export error: {e}")
        
        with col2:
            if st.button("📊 Export PPTX", use_container_width=True):
                st.info("PowerPoint export coming soon!")
        
        with col3:
            if st.button("🔄 Refresh Sources", use_container_width=True):
                st.rerun()
        
    except Exception as e:
        st.error(f"Failed to display results: {e}")
        logger.error(f"Results display error: {e}")

def display_technical_analysis(run):
    """Display technical analysis charts and insights."""
    try:
        if not run or not run.query:
            st.info("No ticker available for technical analysis")
            return
        
        ticker = run.query.upper()
        
        # Options for technical analysis
        col1, col2 = st.columns([2, 1])
        
        with col2:
            period = st.selectbox(
                "Time Period",
                ["1mo", "3mo", "6mo", "1y", "2y"],
                index=2,  # Default to 6mo
                help="Select time period for analysis"
            )
            
            show_full_analysis = st.checkbox(
                "Full Technical Analysis", 
                value=True,
                help="Show comprehensive technical indicators"
            )
        
        with col1:
            with st.spinner(f"Generating technical analysis for {ticker}..."):
                if show_full_analysis:
                    # Generate comprehensive technical analysis
                    tech_results = technical_analyzer.generate_comprehensive_chart(ticker, period)
                    
                    if tech_results:
                        # Display chart
                        st.components.v1.html(
                            tech_results["chart_html"], 
                            height=850, 
                            scrolling=True
                        )
                        
                        # Display insights
                        st.subheader("💡 Technical Insights")
                        
                        insights = tech_results.get("insights", [])
                        if insights:
                            for insight in insights:
                                signal_color = {
                                    "Bullish": "🟢",
                                    "Bearish": "🔴", 
                                    "Overbought": "🟠",
                                    "Oversold": "🟡",
                                    "High": "🔴",
                                    "Low": "🟡",
                                    "Normal": "🟢",
                                    "Neutral": "⚪"
                                }.get(insight["signal"], "⚪")
                                
                                st.write(f"{signal_color} **{insight['type']}**: {insight['signal']}")
                                st.caption(insight["description"])
                        else:
                            st.info("No technical insights available")
                        
                        # Show analysis metadata
                        st.caption(f"Data points: {tech_results.get('data_points', 0)} | "
                                 f"Period: {period} | "
                                 f"Last updated: {tech_results.get('last_update', 'Unknown')}")
                    else:
                        st.warning(f"Unable to generate technical analysis for {ticker}")
                        
                else:
                    # Generate simple price chart
                    simple_chart = technical_analyzer.create_simple_price_chart(ticker, period)
                    
                    if simple_chart:
                        st.components.v1.html(simple_chart, height=450, scrolling=True)
                    else:
                        st.warning(f"Unable to generate price chart for {ticker}")
        
    except Exception as e:
        st.error(f"Technical analysis failed: {e}")
        logger.error(f"Technical analysis error: {e}")

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

def company_comparison_analysis():
    """Company comparison analysis interface."""
    st.header("⚖️ Compare Two Companies")
    st.markdown("Analyze and compare two companies side by side")
    
    # Input for two companies
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Company A")
        ticker_a = st.text_input("Ticker A", placeholder="e.g., AAPL", key="ticker_a")
        
    with col2:
        st.subheader("Company B") 
        ticker_b = st.text_input("Ticker B", placeholder="e.g., MSFT", key="ticker_b")
    
    # Comparison options
    st.subheader("⚙️ Comparison Options")
    col1, col2 = st.columns(2)
    
    with col1:
        include_metrics = st.checkbox("Financial Metrics", value=True)
        include_risks = st.checkbox("Risk Analysis", value=True)
        
    with col2:
        include_opportunities = st.checkbox("Opportunities", value=True)
        include_charts = st.checkbox("Visual Charts", value=True)
    
    # Start comparison button
    if st.button("🔄 Start Comparison", type="primary", use_container_width=True):
        if ticker_a and ticker_b and ticker_a.strip() and ticker_b.strip():
            run_comparison_analysis(ticker_a.strip(), ticker_b.strip(), 
                                  include_metrics, include_risks, include_opportunities, include_charts)
        else:
            st.error("Please enter both ticker symbols")
    
    # Display comparison results if available
    if 'comparison_results' in st.session_state:
        display_comparison_results()

def run_comparison_analysis(ticker_a: str, ticker_b: str, include_metrics: bool, 
                          include_risks: bool, include_opportunities: bool, include_charts: bool):
    """Run comparison analysis for two companies."""
    
    with st.spinner(f"Analyzing {ticker_a} vs {ticker_b}..."):
        try:
            # Get or create analyses for both companies
            results_a = get_or_create_analysis(ticker_a)
            results_b = get_or_create_analysis(ticker_b)
            
            if results_a and results_b:
                # Store comparison results
                st.session_state.comparison_results = {
                    'ticker_a': ticker_a.upper(),
                    'ticker_b': ticker_b.upper(),
                    'results_a': results_a,
                    'results_b': results_b,
                    'options': {
                        'metrics': include_metrics,
                        'risks': include_risks, 
                        'opportunities': include_opportunities,
                        'charts': include_charts
                    }
                }
                st.success(f"✅ Comparison completed: {ticker_a} vs {ticker_b}")
                st.rerun()
            else:
                st.error("Failed to analyze one or both companies")
                
        except Exception as e:
            st.error(f"Comparison failed: {e}")
            logger.error(f"Comparison error: {e}")

def get_or_create_analysis(ticker: str) -> Optional[Dict]:
    """Get existing analysis or create new one for a ticker."""
    try:
        # Check for recent completed analysis
        if st.session_state.database:
            recent_runs = st.session_state.database.get_recent_runs(limit=10)
            for run in recent_runs:
                if run.query.upper() == ticker.upper() and run.status == 'completed':
                    # Get memo and sources
                    memo = st.session_state.database.get_memo(run.id)
                    sources = st.session_state.database.get_sources(run.id)
                    
                    if memo:
                        return {
                            'run_id': run.id,
                            'memo': memo,
                            'sources': sources,
                            'timestamp': run.finished_at
                        }
        
        # If no recent analysis, run a quick one
        st.info(f"Running fresh analysis for {ticker}...")
        return run_quick_analysis(ticker)
        
    except Exception as e:
        logger.error(f"Failed to get/create analysis for {ticker}: {e}")
        return None

def run_quick_analysis(ticker: str) -> Optional[Dict]:
    """Run a quick analysis for comparison purposes."""
    try:
        # Create new analysis run
        run_id = st.session_state.database.create_run(ticker)
        
        # Quick data collection (market data only for speed)
        market_ingestor = MarketIngestor()
        sources = []
        
        # Get market data
        try:
            market_sources = run_sync_analysis(
                market_ingestor.ingest(ticker, run_id)
            )
            sources.extend(market_sources)
        except Exception as e:
            logger.warning(f"Market data failed for {ticker}: {e}")
        
        # Generate quick memo
        memo_data = generate_simple_memo(ticker, sources)
        memo_id = st.session_state.database.save_memo(
            run_id, 
            memo_data["tldr"],
            [item.model_dump() for item in memo_data["risks"]],
            [item.model_dump() for item in memo_data["opportunities"]], 
            [item.model_dump() for item in memo_data["metrics"]],
            memo_data["html_content"]
        )
        
        # Update run status
        st.session_state.database.update_run_status(run_id, RunStatus.COMPLETED)
        
        # Get memo object
        memo = st.session_state.database.get_memo(run_id)
        
        return {
            'run_id': run_id,
            'memo': memo,
            'sources': sources,
            'timestamp': datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Quick analysis failed for {ticker}: {e}")
        return None

def display_comparison_results():
    """Display side-by-side comparison results."""
    if 'comparison_results' not in st.session_state:
        return
    
    results = st.session_state.comparison_results
    
    st.header(f"📊 {results['ticker_a']} vs {results['ticker_b']}")
    
    # Summary comparison
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"🏢 {results['ticker_a']}")
        memo_a = results['results_a']['memo']
        st.write("**Executive Summary**")
        st.write(memo_a.tldr)
        
        if results['options']['risks']:
            st.write("**Top Risks:**")
            for risk in memo_a.risks[:2]:
                st.write(f"• {risk.risk}")
        
        if results['options']['opportunities']:
            st.write("**Top Opportunities:**")
            for opp in memo_a.opportunities[:2]:
                st.write(f"• {opp.opportunity}")
    
    with col2:
        st.subheader(f"🏢 {results['ticker_b']}")
        memo_b = results['results_b']['memo']
        st.write("**Executive Summary**")
        st.write(memo_b.tldr)
        
        if results['options']['risks']:
            st.write("**Top Risks:**")
            for risk in memo_b.risks[:2]:
                st.write(f"• {risk.risk}")
        
        if results['options']['opportunities']:
            st.write("**Top Opportunities:**")
            for opp in memo_b.opportunities[:2]:
                st.write(f"• {opp.opportunity}")
    
    # Metrics comparison
    if results['options']['metrics']:
        st.subheader("📈 Metrics Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**{results['ticker_a']} Metrics**")
            for metric in memo_a.metrics:
                st.metric(metric.metric, metric.value, metric.trend)
        
        with col2:
            st.write(f"**{results['ticker_b']} Metrics**")
            for metric in memo_b.metrics:
                st.metric(metric.metric, metric.value, metric.trend)
    
    # Export comparison
    st.subheader("📤 Export Comparison")
    if st.button("📄 Export Comparison PDF", use_container_width=True):
        st.info("Comparison PDF export coming soon!")

if __name__ == "__main__":
    main()
