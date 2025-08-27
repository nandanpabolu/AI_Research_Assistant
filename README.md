# 🤖 AI Research Analyst Agent

A **local, free, and powerful** AI-powered research assistant that analyzes stocks, companies, and market trends using public data sources.

## ✨ Features

- **📊 Multi-Source Data Collection**: SEC filings, news articles, market data, financial ratios
- **🤖 AI-Powered Analysis**: Risk assessment, opportunity identification, key metrics extraction
- **📄 Professional Reports**: Generate analyst memos in HTML, PDF, and PowerPoint formats
- **🔒 100% Local & Free**: No API keys, no cloud dependencies, no data privacy concerns
- **⚡ Fast Analysis**: Complete analysis in 10-30 seconds
- **📱 Modern UI**: Clean Streamlit interface with real-time progress tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/ai-research-assistant.git
   cd ai-research-assistant
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Open your browser** and navigate to `http://localhost:8501`

## 🎯 Usage

### Basic Analysis
1. **Enter a ticker symbol** (e.g., "AAPL", "TSLA", "MSFT")
2. **Click "Start Analysis"**
3. **Wait for completion** (10-30 seconds)
4. **Review results**: Executive summary, risks, opportunities, key metrics
5. **Export reports** in HTML, PDF, or PowerPoint format

### Data Sources Collected
- **Market Data**: Company info, financial ratios, historical prices, earnings
- **News Articles**: Business news from Reuters, Bloomberg, CNBC, Yahoo Finance
- **SEC Filings**: 10-K, 10-Q reports (when available)
- **Total Sources**: Typically 10-30 data points per analysis

## 🏗️ Architecture

```
AI Research Assistant/
├── app.py                 # Main Streamlit application
├── core/                  # Core configuration and utilities
│   ├── config.py         # Application settings
│   └── utils.py          # Helper functions
├── ingestors/            # Data collection modules
│   ├── base.py           # Base ingestor class
│   ├── market_ingestor.py # Market data collection
│   ├── news_ingestor.py  # News article collection
│   └── sec_ingestor.py   # SEC filings collection
├── models/               # Data models and database
│   ├── schemas.py        # Pydantic data schemas
│   └── database.py       # SQLite database manager
├── templates/            # HTML templates for reports
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🔧 Configuration

### RSS Feeds
Edit `core/config.py` to customize news sources:
```python
"rss_feeds": [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    # Add your preferred news sources
]
```

### Market Data
Configure market data collection parameters:
```python
"market": {
    "data_provider": "yfinance",
    "period": "1y",           # Data timeframe
    "interval": "1d",         # Data granularity
    "max_retries": 3
}
```

## 📊 Example Output

### Executive Summary
```
AAPL analysis completed with 24 data sources. Analysis covers market data, 
news, and regulatory filings. Apple shows strong financial performance with 
increasing revenue and market share in key segments.
```

### Key Risks
- **Supply Chain Disruption**: Global semiconductor shortages affecting production
- **Regulatory Changes**: Potential antitrust investigations in multiple jurisdictions
- **Market Competition**: Intensifying competition in smartphone and services markets

### Key Opportunities
- **Services Growth**: Expanding Apple One and subscription services
- **Emerging Markets**: Untapped potential in India and other developing regions
- **AI Integration**: Siri improvements and AI-powered features

## 🛠️ Development

### Adding New Data Sources
1. Create a new ingestor class inheriting from `BaseIngestor`
2. Implement the `ingest()` method
3. Add configuration in `core/config.py`
4. Update the main analysis pipeline in `app.py`

### Adding New Analysis Types
1. Extend the data schemas in `models/schemas.py`
2. Add new memo sections in the generation logic
3. Update the UI to display new analysis types

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Yahoo Finance**: Market data and financial information
- **RSS Feeds**: News sources from major financial outlets
- **Streamlit**: Modern web application framework
- **Pydantic**: Data validation and serialization
- **SQLite**: Lightweight database for local storage

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/ai-research-assistant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-research-assistant/discussions)
- **Wiki**: [Project Wiki](https://github.com/yourusername/ai-research-assistant/wiki)

---

**Made with ❤️ for the open-source community**
