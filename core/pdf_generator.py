#!/usr/bin/env python3
"""
PDF generation module for AI Research Assistant reports.
Generates professional PDF reports from analysis data.
"""

import os
import io
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import logging

# PDF generation imports
try:
    import weasyprint
    from jinja2 import Environment, FileSystemLoader
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    import plotly.io as pio
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    logging.warning("PDF generation dependencies not available")

logger = logging.getLogger(__name__)


class PDFGenerator:
    """Professional PDF report generator."""
    
    def __init__(self):
        """Initialize PDF generator with templates."""
        self.template_dir = Path("templates")
        self.output_dir = Path("exports")
        self.output_dir.mkdir(exist_ok=True)
        
        if PDF_AVAILABLE:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                trim_blocks=True,
                lstrip_blocks=True
            )
    
    def generate_pdf_report(self, memo_data: Dict[str, Any], ticker: str, 
                          sources: List[Any], run_id: int) -> Optional[bytes]:
        """
        Generate a professional PDF report.
        
        Args:
            memo_data: Analysis memo data
            ticker: Company ticker symbol
            sources: List of data sources
            run_id: Analysis run ID
            
        Returns:
            PDF bytes or None if generation fails
        """
        if not PDF_AVAILABLE:
            logger.error("PDF generation not available - missing dependencies")
            return None
        
        try:
            # Prepare data for template
            report_data = self._prepare_report_data(memo_data, ticker, sources, run_id)
            
            # Generate charts
            charts_data = self._generate_charts(sources, ticker)
            report_data.update(charts_data)
            
            # Render HTML from template
            html_content = self._render_html_template(report_data)
            
            # Convert HTML to PDF
            pdf_bytes = self._html_to_pdf(html_content)
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{ticker}_analysis_{timestamp}.pdf"
            filepath = self.output_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(pdf_bytes)
            
            logger.info(f"PDF report generated: {filepath}")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return None
    
    def _prepare_report_data(self, memo_data: Dict[str, Any], ticker: str, 
                           sources: List[Any], run_id: int) -> Dict[str, Any]:
        """Prepare data for PDF template."""
        
        # Convert Pydantic objects to dicts if needed
        risks = []
        for risk in memo_data.get("risks", []):
            if hasattr(risk, 'model_dump'):
                risks.append(risk.model_dump())
            else:
                risks.append(risk)
        
        opportunities = []
        for opp in memo_data.get("opportunities", []):
            if hasattr(opp, 'model_dump'):
                opportunities.append(opp.model_dump())
            else:
                opportunities.append(opp)
        
        metrics = []
        for metric in memo_data.get("metrics", []):
            if hasattr(metric, 'model_dump'):
                metrics.append(metric.model_dump())
            else:
                metrics.append(metric)
        
        # Count sources by type
        source_counts = {}
        for source in sources:
            source_type = source.type.value if hasattr(source.type, 'value') else source.type
            source_counts[source_type] = source_counts.get(source_type, 0) + 1
        
        return {
            "ticker": ticker.upper(),
            "company_name": f"{ticker.upper()} Corporation",  # Could be enhanced with real company names
            "generated_at": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            "run_id": run_id,
            "tldr": memo_data.get("tldr", ""),
            "risks": risks,
            "opportunities": opportunities,
            "metrics": metrics,
            "total_sources": len(sources),
            "source_counts": source_counts,
            "source_breakdown": [
                {"type": k.replace("_", " ").title(), "count": v} 
                for k, v in source_counts.items()
            ]
        }
    
    def _generate_charts(self, sources: List[Any], ticker: str) -> Dict[str, str]:
        """Generate charts for the PDF report."""
        charts = {}
        
        try:
            # Source distribution pie chart
            source_counts = {}
            for source in sources:
                source_type = source.type.value if hasattr(source.type, 'value') else source.type
                source_counts[source_type] = source_counts.get(source_type, 0) + 1
            
            if source_counts:
                # Create plotly pie chart
                fig = go.Figure(data=[go.Pie(
                    labels=[k.replace("_", " ").title() for k in source_counts.keys()],
                    values=list(source_counts.values()),
                    hole=0.3,
                    marker_colors=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
                )])
                
                fig.update_layout(
                    title=f"{ticker} Data Sources Distribution",
                    font_size=12,
                    width=400,
                    height=300,
                    margin=dict(t=40, b=40, l=40, r=40)
                )
                
                # Convert to base64 for embedding
                img_bytes = pio.to_image(fig, format="png", width=400, height=300)
                import base64
                charts["source_chart"] = base64.b64encode(img_bytes).decode()
            
        except Exception as e:
            logger.warning(f"Chart generation failed: {e}")
        
        return charts
    
    def _render_html_template(self, data: Dict[str, Any]) -> str:
        """Render HTML template with data."""
        
        # Use a built-in template if file doesn't exist
        template_content = self._get_pdf_template()
        
        try:
            template = self.jinja_env.from_string(template_content)
            return template.render(**data)
        except Exception as e:
            logger.warning(f"Template rendering failed: {e}")
            # Return basic HTML
            return self._generate_basic_html(data)
    
    def _html_to_pdf(self, html_content: str) -> bytes:
        """Convert HTML to PDF using WeasyPrint."""
        try:
            pdf_doc = weasyprint.HTML(string=html_content)
            pdf_bytes = pdf_doc.write_pdf()
            return pdf_bytes
        except Exception as e:
            logger.error(f"HTML to PDF conversion failed: {e}")
            raise
    
    def _get_pdf_template(self) -> str:
        """Get PDF template content."""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ ticker }} Analysis Report</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 40px; 
            line-height: 1.6; 
            color: #333;
        }
        .header { 
            text-align: center; 
            border-bottom: 3px solid #007acc; 
            padding-bottom: 20px; 
            margin-bottom: 30px; 
        }
        .company-name { 
            font-size: 28px; 
            font-weight: bold; 
            color: #007acc; 
            margin-bottom: 5px; 
        }
        .report-title { 
            font-size: 18px; 
            color: #666; 
            margin-bottom: 10px; 
        }
        .metadata { 
            font-size: 12px; 
            color: #888; 
        }
        .section { 
            margin-bottom: 25px; 
            page-break-inside: avoid; 
        }
        .section-title { 
            font-size: 18px; 
            font-weight: bold; 
            color: #007acc; 
            border-bottom: 1px solid #ddd; 
            padding-bottom: 5px; 
            margin-bottom: 15px; 
        }
        .summary-box { 
            background: #f8f9fa; 
            border-left: 4px solid #007acc; 
            padding: 15px; 
            margin-bottom: 20px; 
        }
        .risk-item, .opportunity-item { 
            background: #fff; 
            border: 1px solid #e0e0e0; 
            border-radius: 5px; 
            padding: 12px; 
            margin-bottom: 10px; 
        }
        .risk-item { 
            border-left: 4px solid #dc3545; 
        }
        .opportunity-item { 
            border-left: 4px solid #28a745; 
        }
        .item-title { 
            font-weight: bold; 
            margin-bottom: 5px; 
        }
        .item-rationale { 
            color: #666; 
            font-size: 14px; 
        }
        .metrics-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
            margin-top: 15px; 
        }
        .metric-card { 
            background: #f8f9fa; 
            border: 1px solid #e0e0e0; 
            border-radius: 5px; 
            padding: 15px; 
            text-align: center; 
        }
        .metric-value { 
            font-size: 24px; 
            font-weight: bold; 
            color: #007acc; 
        }
        .metric-label { 
            font-size: 12px; 
            color: #666; 
            margin-top: 5px; 
        }
        .sources-table { 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 15px; 
        }
        .sources-table th, .sources-table td { 
            border: 1px solid #ddd; 
            padding: 8px; 
            text-align: left; 
        }
        .sources-table th { 
            background-color: #f8f9fa; 
            font-weight: bold; 
        }
        .chart-container { 
            text-align: center; 
            margin: 20px 0; 
        }
        .chart-image { 
            max-width: 100%; 
            height: auto; 
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">{{ ticker }} Analysis Report</div>
        <div class="report-title">AI-Powered Financial Analysis</div>
        <div class="metadata">
            Generated on {{ generated_at }} | Run ID: {{ run_id }}
        </div>
    </div>

    <div class="section">
        <div class="section-title">Executive Summary</div>
        <div class="summary-box">
            {{ tldr }}
        </div>
    </div>

    <div class="section">
        <div class="section-title">Key Risks</div>
        {% for risk in risks %}
        <div class="risk-item">
            <div class="item-title">{{ risk.risk }}</div>
            <div class="item-rationale">{{ risk.rationale }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="section">
        <div class="section-title">Key Opportunities</div>
        {% for opportunity in opportunities %}
        <div class="opportunity-item">
            <div class="item-title">{{ opportunity.opportunity }}</div>
            <div class="item-rationale">{{ opportunity.rationale }}</div>
        </div>
        {% endfor %}
    </div>

    <div class="section">
        <div class="section-title">Key Metrics</div>
        <div class="metrics-grid">
            {% for metric in metrics %}
            <div class="metric-card">
                <div class="metric-value">{{ metric.value }}</div>
                <div class="metric-label">{{ metric.metric }}</div>
            </div>
            {% endfor %}
        </div>
    </div>

    {% if source_chart %}
    <div class="section">
        <div class="section-title">Data Sources</div>
        <div class="chart-container">
            <img src="data:image/png;base64,{{ source_chart }}" class="chart-image" alt="Source Distribution">
        </div>
        <table class="sources-table">
            <thead>
                <tr>
                    <th>Source Type</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
                {% for source in source_breakdown %}
                <tr>
                    <td>{{ source.type }}</td>
                    <td>{{ source.count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <div class="section">
        <div class="section-title">Analysis Details</div>
        <p><strong>Total Sources Analyzed:</strong> {{ total_sources }}</p>
        <p><strong>Analysis Method:</strong> AI-powered extraction using natural language processing</p>
        <p><strong>Report Generated:</strong> {{ generated_at }}</p>
    </div>
</body>
</html>
        """
    
    def _generate_basic_html(self, data: Dict[str, Any]) -> str:
        """Generate basic HTML if template fails."""
        return f"""
        <html>
        <head><title>{data['ticker']} Analysis</title></head>
        <body>
            <h1>{data['ticker']} Analysis Report</h1>
            <h2>Executive Summary</h2>
            <p>{data['tldr']}</p>
            <h2>Key Risks</h2>
            <ul>
                {''.join([f"<li><strong>{r['risk']}:</strong> {r['rationale']}</li>" for r in data['risks']])}
            </ul>
            <h2>Key Opportunities</h2>
            <ul>
                {''.join([f"<li><strong>{o['opportunity']}:</strong> {o['rationale']}</li>" for o in data['opportunities']])}
            </ul>
            <p>Generated on {data['generated_at']}</p>
        </body>
        </html>
        """


# Global instance
pdf_generator = PDFGenerator()
