#!/usr/bin/env python3
"""
Technical analysis module for generating financial charts and indicators.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import pandas as pd

# Technical analysis imports
try:
    import yfinance as yf
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import numpy as np
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    logging.warning("Technical analysis dependencies not available")

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Technical analysis and chart generation."""
    
    def __init__(self):
        """Initialize technical analyzer."""
        self.chart_theme = "plotly_white"
        
    def generate_comprehensive_chart(self, ticker: str, period: str = "6mo") -> Optional[Dict[str, Any]]:
        """
        Generate a comprehensive technical analysis chart.
        
        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            Dictionary with chart data and insights
        """
        if not CHARTS_AVAILABLE:
            logger.error("Technical analysis not available - missing dependencies")
            return None
        
        try:
            # Get stock data
            stock = yf.Ticker(ticker)
            hist_data = stock.history(period=period)
            
            if hist_data.empty:
                logger.warning(f"No historical data found for {ticker}")
                return None
            
            # Calculate technical indicators
            indicators = self._calculate_indicators(hist_data)
            
            # Create comprehensive chart
            chart_html = self._create_multi_panel_chart(ticker, hist_data, indicators)
            
            # Generate insights
            insights = self._generate_technical_insights(ticker, hist_data, indicators)
            
            return {
                "chart_html": chart_html,
                "insights": insights,
                "data_points": len(hist_data),
                "period": period,
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Technical analysis failed for {ticker}: {e}")
            return None
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate technical indicators."""
        indicators = {}
        
        try:
            # Moving Averages
            indicators['sma_20'] = data['Close'].rolling(window=20).mean()
            indicators['sma_50'] = data['Close'].rolling(window=50).mean()
            indicators['ema_12'] = data['Close'].ewm(span=12).mean()
            indicators['ema_26'] = data['Close'].ewm(span=26).mean()
            
            # RSI (Relative Strength Index)
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            indicators['macd'] = indicators['ema_12'] - indicators['ema_26']
            indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
            indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
            
            # Bollinger Bands
            sma_20 = indicators['sma_20']
            std_20 = data['Close'].rolling(window=20).std()
            indicators['bb_upper'] = sma_20 + (std_20 * 2)
            indicators['bb_lower'] = sma_20 - (std_20 * 2)
            
            # Volume indicators
            indicators['volume_sma'] = data['Volume'].rolling(window=20).mean()
            
        except Exception as e:
            logger.warning(f"Some indicators calculation failed: {e}")
        
        return indicators
    
    def _create_multi_panel_chart(self, ticker: str, data: pd.DataFrame, 
                                indicators: Dict[str, pd.Series]) -> str:
        """Create a multi-panel technical analysis chart."""
        
        # Create subplots
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f'{ticker} Price & Moving Averages', 'Volume', 'RSI', 'MACD'),
            row_heights=[0.5, 0.2, 0.15, 0.15]
        )
        
        # 1. Price Chart with Moving Averages and Bollinger Bands
        fig.add_trace(
            go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close'],
                name='OHLC',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1, col=1
        )
        
        # Moving averages
        if 'sma_20' in indicators:
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['sma_20'], 
                          line=dict(color='orange', width=2), name='SMA 20'),
                row=1, col=1
            )
        
        if 'sma_50' in indicators:
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['sma_50'], 
                          line=dict(color='blue', width=2), name='SMA 50'),
                row=1, col=1
            )
        
        # Bollinger Bands
        if 'bb_upper' in indicators and 'bb_lower' in indicators:
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['bb_upper'], 
                          line=dict(color='gray', width=1, dash='dash'), name='BB Upper'),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['bb_lower'], 
                          line=dict(color='gray', width=1, dash='dash'), name='BB Lower'),
                row=1, col=1
            )
        
        # 2. Volume Chart
        colors = ['green' if row['Close'] >= row['Open'] else 'red' 
                 for _, row in data.iterrows()]
        
        fig.add_trace(
            go.Bar(x=data.index, y=data['Volume'], name='Volume', 
                   marker_color=colors, opacity=0.7),
            row=2, col=1
        )
        
        if 'volume_sma' in indicators:
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['volume_sma'], 
                          line=dict(color='purple', width=2), name='Volume SMA'),
                row=2, col=1
            )
        
        # 3. RSI Chart
        if 'rsi' in indicators:
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['rsi'], 
                          line=dict(color='orange', width=2), name='RSI'),
                row=3, col=1
            )
            
            # RSI levels
            fig.add_hline(y=70, line_dash="dash", line_color="red", 
                         annotation_text="Overbought", row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", 
                         annotation_text="Oversold", row=3, col=1)
        
        # 4. MACD Chart
        if 'macd' in indicators:
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['macd'], 
                          line=dict(color='blue', width=2), name='MACD'),
                row=4, col=1
            )
            
        if 'macd_signal' in indicators:
            fig.add_trace(
                go.Scatter(x=data.index, y=indicators['macd_signal'], 
                          line=dict(color='red', width=1), name='Signal'),
                row=4, col=1
            )
            
        if 'macd_histogram' in indicators:
            colors = ['green' if val >= 0 else 'red' for val in indicators['macd_histogram']]
            fig.add_trace(
                go.Bar(x=data.index, y=indicators['macd_histogram'], 
                      name='MACD Histogram', marker_color=colors, opacity=0.6),
                row=4, col=1
            )
        
        # Update layout
        fig.update_layout(
            title=f'{ticker} Technical Analysis',
            xaxis_rangeslider_visible=False,
            height=800,
            showlegend=True,
            template=self.chart_theme
        )
        
        # Update y-axis labels
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=3, col=1)
        fig.update_yaxes(title_text="MACD", row=4, col=1)
        
        # Convert to HTML
        return fig.to_html(include_plotlyjs='cdn', div_id="technical-chart")
    
    def _generate_technical_insights(self, ticker: str, data: pd.DataFrame, 
                                   indicators: Dict[str, pd.Series]) -> List[Dict[str, str]]:
        """Generate technical analysis insights."""
        insights = []
        
        try:
            current_price = data['Close'].iloc[-1]
            
            # Price trend analysis
            if 'sma_20' in indicators and 'sma_50' in indicators:
                sma_20_current = indicators['sma_20'].iloc[-1]
                sma_50_current = indicators['sma_50'].iloc[-1]
                
                if not pd.isna(sma_20_current) and not pd.isna(sma_50_current):
                    if sma_20_current > sma_50_current:
                        trend = "Bullish"
                        trend_desc = "20-day SMA is above 50-day SMA, indicating upward momentum"
                    else:
                        trend = "Bearish"
                        trend_desc = "20-day SMA is below 50-day SMA, indicating downward momentum"
                    
                    insights.append({
                        "type": "Trend",
                        "signal": trend,
                        "description": trend_desc
                    })
            
            # RSI analysis
            if 'rsi' in indicators:
                rsi_current = indicators['rsi'].iloc[-1]
                if not pd.isna(rsi_current):
                    if rsi_current > 70:
                        rsi_signal = "Overbought"
                        rsi_desc = f"RSI at {rsi_current:.1f} indicates potential selling pressure"
                    elif rsi_current < 30:
                        rsi_signal = "Oversold"
                        rsi_desc = f"RSI at {rsi_current:.1f} indicates potential buying opportunity"
                    else:
                        rsi_signal = "Neutral"
                        rsi_desc = f"RSI at {rsi_current:.1f} is in normal range"
                    
                    insights.append({
                        "type": "Momentum",
                        "signal": rsi_signal,
                        "description": rsi_desc
                    })
            
            # MACD analysis
            if 'macd' in indicators and 'macd_signal' in indicators:
                macd_current = indicators['macd'].iloc[-1]
                signal_current = indicators['macd_signal'].iloc[-1]
                
                if not pd.isna(macd_current) and not pd.isna(signal_current):
                    if macd_current > signal_current:
                        macd_signal = "Bullish"
                        macd_desc = "MACD line above signal line suggests upward momentum"
                    else:
                        macd_signal = "Bearish"
                        macd_desc = "MACD line below signal line suggests downward momentum"
                    
                    insights.append({
                        "type": "MACD",
                        "signal": macd_signal,
                        "description": macd_desc
                    })
            
            # Volume analysis
            recent_volume = data['Volume'].tail(5).mean()
            avg_volume = data['Volume'].mean()
            
            if recent_volume > avg_volume * 1.5:
                volume_signal = "High"
                volume_desc = "Recent volume significantly above average"
            elif recent_volume < avg_volume * 0.5:
                volume_signal = "Low"
                volume_desc = "Recent volume below average"
            else:
                volume_signal = "Normal"
                volume_desc = "Volume in normal range"
            
            insights.append({
                "type": "Volume",
                "signal": volume_signal,
                "description": volume_desc
            })
            
            # Bollinger Bands analysis
            if 'bb_upper' in indicators and 'bb_lower' in indicators:
                bb_upper = indicators['bb_upper'].iloc[-1]
                bb_lower = indicators['bb_lower'].iloc[-1]
                
                if not pd.isna(bb_upper) and not pd.isna(bb_lower):
                    if current_price > bb_upper:
                        bb_signal = "Overbought"
                        bb_desc = "Price above upper Bollinger Band"
                    elif current_price < bb_lower:
                        bb_signal = "Oversold" 
                        bb_desc = "Price below lower Bollinger Band"
                    else:
                        bb_signal = "Normal"
                        bb_desc = "Price within Bollinger Bands"
                    
                    insights.append({
                        "type": "Bollinger Bands",
                        "signal": bb_signal,
                        "description": bb_desc
                    })
        
        except Exception as e:
            logger.warning(f"Insights generation failed: {e}")
            insights.append({
                "type": "Error",
                "signal": "Unable to analyze",
                "description": "Technical analysis encountered an error"
            })
        
        return insights

    def create_simple_price_chart(self, ticker: str, period: str = "3mo") -> Optional[str]:
        """Create a simple price chart for quick viewing."""
        if not CHARTS_AVAILABLE:
            return None
        
        try:
            # Get stock data
            stock = yf.Ticker(ticker)
            hist_data = stock.history(period=period)
            
            if hist_data.empty:
                return None
            
            # Create simple candlestick chart
            fig = go.Figure(data=[go.Candlestick(
                x=hist_data.index,
                open=hist_data['Open'],
                high=hist_data['High'],
                low=hist_data['Low'],
                close=hist_data['Close'],
                name=ticker
            )])
            
            fig.update_layout(
                title=f'{ticker} Price Chart ({period})',
                yaxis_title='Price ($)',
                xaxis_rangeslider_visible=False,
                height=400,
                template=self.chart_theme
            )
            
            return fig.to_html(include_plotlyjs='cdn', div_id=f"price-chart-{ticker}")
        
        except Exception as e:
            logger.error(f"Simple chart creation failed: {e}")
            return None


# Global instance
technical_analyzer = TechnicalAnalyzer()
