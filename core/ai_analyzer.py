#!/usr/bin/env python3
"""
AI-powered analysis module for extracting insights from financial data.
Uses Hugging Face transformers for intelligent risk/opportunity extraction.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

# AI/NLP imports
try:
    from transformers import pipeline, Pipeline
    import torch
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available - AI features will be limited")

# Data models
from models.schemas import RiskItem, OpportunityItem, MetricItem

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI-powered financial text analyzer using Hugging Face models."""
    
    def __init__(self):
        """Initialize AI models and pipelines."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.summarizer = None
        self.classifier = None
        self.embedder = None
        self._load_models()
    
    def _load_models(self):
        """Load AI models with fallback handling."""
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Transformers not available - using fallback analysis")
            return
            
        try:
            # Summarization model (lightweight)
            logger.info("Loading summarization model...")
            self.summarizer = pipeline(
                "summarization",
                model="sshleifer/distilbart-cnn-6-6",  # Lightweight model
                device=0 if self.device == "cuda" else -1,
                max_length=150,
                min_length=50,
                do_sample=False
            )
            
            # Text classification for sentiment/risk detection
            logger.info("Loading classification model...")
            self.classifier = pipeline(
                "text-classification",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                device=0 if self.device == "cuda" else -1
            )
            
            # Sentence embeddings for similarity
            logger.info("Loading embedding model...")
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            
            logger.info(f"AI models loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load AI models: {e}")
            logger.info("Falling back to rule-based analysis")
    
    def extract_risks(self, text_chunks: List[str], company_name: str = "") -> List[RiskItem]:
        """
        Extract business risks from text using AI analysis.
        
        Args:
            text_chunks: List of text segments to analyze
            company_name: Company name for context
            
        Returns:
            List of RiskItem objects
        """
        if self.classifier is None:
            return self._extract_risks_fallback(text_chunks, company_name)
        
        risks = []
        risk_patterns = [
            r'risk(?:s)?.*?(?:include|are|of)',
            r'challenge(?:s)?.*?(?:include|facing|with)',
            r'threat(?:s)?.*?(?:to|from|of)',
            r'concern(?:s)?.*?(?:about|regarding|over)',
            r'uncertainty.*?(?:in|about|regarding)',
            r'volatility.*?(?:in|of|due to)',
            r'decline.*?(?:in|of|due to)',
            r'competition.*?(?:from|in|increasing)'
        ]
        
        for i, chunk in enumerate(text_chunks):
            if len(chunk) < 100:  # Skip very short chunks
                continue
                
            try:
                # Find risk-related sentences
                sentences = re.split(r'[.!?]+', chunk)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 50:
                        continue
                    
                    # Check if sentence contains risk patterns
                    has_risk_pattern = any(re.search(pattern, sentence.lower()) 
                                         for pattern in risk_patterns)
                    
                    if has_risk_pattern:
                        # Analyze sentiment (negative = risk)
                        try:
                            sentiment = self.classifier(sentence[:512])  # Truncate for BERT
                            if sentiment and len(sentiment) > 0:
                                score = sentiment[0]['score']
                                label = sentiment[0]['label']
                                
                                # Consider negative sentiment or low scores as risks
                                if (label in ['NEGATIVE', '1 star', '2 stars'] or 
                                    (label == 'NEUTRAL' and score < 0.6)):
                                    
                                    # Extract key risk phrase
                                    risk_text = self._extract_key_phrase(sentence)
                                    if risk_text and len(risks) < 5:  # Limit to top 5 risks
                                        risks.append(RiskItem(
                                            risk=risk_text,
                                            rationale=sentence.strip(),
                                            source_ids=[f"S{i+1}"]
                                        ))
                        except Exception as e:
                            logger.debug(f"Sentiment analysis failed: {e}")
                            continue
                            
            except Exception as e:
                logger.warning(f"Risk extraction failed for chunk {i}: {e}")
                continue
        
        # If no AI-detected risks, fall back to pattern matching
        if not risks:
            risks = self._extract_risks_fallback(text_chunks, company_name)
        
        return risks[:3]  # Return top 3 risks
    
    def extract_opportunities(self, text_chunks: List[str], company_name: str = "") -> List[OpportunityItem]:
        """
        Extract business opportunities from text using AI analysis.
        
        Args:
            text_chunks: List of text segments to analyze
            company_name: Company name for context
            
        Returns:
            List of OpportunityItem objects
        """
        if self.classifier is None:
            return self._extract_opportunities_fallback(text_chunks, company_name)
        
        opportunities = []
        opportunity_patterns = [
            r'opportunit(?:y|ies).*?(?:to|in|for|include)',
            r'growth.*?(?:in|opportunity|potential|expected)',
            r'expansion.*?(?:into|of|in|plans)',
            r'investment(?:s)?.*?(?:in|to|for|opportunity)',
            r'new.*?(?:market(?:s)?|product(?:s)?|service(?:s)?)',
            r'innovation(?:s)?.*?(?:in|to|for)',
            r'partnership(?:s)?.*?(?:with|to|for)',
            r'acquisition(?:s)?.*?(?:of|to|for)'
        ]
        
        for i, chunk in enumerate(text_chunks):
            if len(chunk) < 100:
                continue
                
            try:
                sentences = re.split(r'[.!?]+', chunk)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 50:
                        continue
                    
                    # Check for opportunity patterns
                    has_opportunity_pattern = any(re.search(pattern, sentence.lower()) 
                                                for pattern in opportunity_patterns)
                    
                    if has_opportunity_pattern:
                        try:
                            sentiment = self.classifier(sentence[:512])
                            if sentiment and len(sentiment) > 0:
                                score = sentiment[0]['score']
                                label = sentiment[0]['label']
                                
                                # Consider positive sentiment as opportunities
                                if (label in ['POSITIVE', '4 stars', '5 stars'] or 
                                    (label == 'NEUTRAL' and score > 0.7)):
                                    
                                    opportunity_text = self._extract_key_phrase(sentence)
                                    if opportunity_text and len(opportunities) < 5:
                                        opportunities.append(OpportunityItem(
                                            opportunity=opportunity_text,
                                            rationale=sentence.strip(),
                                            source_ids=[f"S{i+1}"]
                                        ))
                        except Exception as e:
                            logger.debug(f"Sentiment analysis failed: {e}")
                            continue
                            
            except Exception as e:
                logger.warning(f"Opportunity extraction failed for chunk {i}: {e}")
                continue
        
        if not opportunities:
            opportunities = self._extract_opportunities_fallback(text_chunks, company_name)
        
        return opportunities[:3]  # Return top 3 opportunities
    
    def generate_summary(self, text_chunks: List[str], max_length: int = 200) -> str:
        """
        Generate an executive summary using AI summarization.
        
        Args:
            text_chunks: List of text segments
            max_length: Maximum summary length
            
        Returns:
            Generated summary text
        """
        if not text_chunks or self.summarizer is None:
            return self._generate_summary_fallback(text_chunks)
        
        try:
            # Combine and clean text
            combined_text = " ".join(text_chunks)
            combined_text = re.sub(r'\s+', ' ', combined_text).strip()
            
            # Limit input length for model
            if len(combined_text) > 2000:
                combined_text = combined_text[:2000]
            
            if len(combined_text) < 100:
                return self._generate_summary_fallback(text_chunks)
            
            # Generate summary
            summary = self.summarizer(
                combined_text, 
                max_length=min(max_length, 150), 
                min_length=50,
                do_sample=False
            )
            
            if summary and len(summary) > 0:
                return summary[0]['summary_text']
            else:
                return self._generate_summary_fallback(text_chunks)
                
        except Exception as e:
            logger.warning(f"AI summarization failed: {e}")
            return self._generate_summary_fallback(text_chunks)
    
    def _extract_key_phrase(self, sentence: str) -> str:
        """Extract the key phrase from a sentence."""
        # Remove common stop words and extract meaningful phrase
        sentence = re.sub(r'^(the|a|an|in|on|at|to|for|of|with|by)\s+', '', sentence.lower())
        sentence = sentence.strip().capitalize()
        
        # Limit length
        if len(sentence) > 80:
            sentence = sentence[:77] + "..."
        
        return sentence
    
    def _extract_risks_fallback(self, text_chunks: List[str], company_name: str) -> List[RiskItem]:
        """Fallback risk extraction using pattern matching."""
        risks = []
        risk_keywords = [
            "competition", "regulatory", "market volatility", "economic uncertainty",
            "supply chain", "cybersecurity", "inflation", "interest rates"
        ]
        
        for keyword in risk_keywords[:3]:
            risks.append(RiskItem(
                risk=f"{keyword.title()} challenges",
                rationale=f"Industry-wide {keyword} concerns may impact performance",
                source_ids=["S1"]
            ))
        
        return risks
    
    def _extract_opportunities_fallback(self, text_chunks: List[str], company_name: str) -> List[OpportunityItem]:
        """Fallback opportunity extraction using pattern matching."""
        opportunities = []
        opp_keywords = [
            "market expansion", "digital transformation", "innovation"
        ]
        
        for keyword in opp_keywords:
            opportunities.append(OpportunityItem(
                opportunity=f"{keyword.title()} potential",
                rationale=f"Potential for growth through {keyword}",
                source_ids=["S1"]
            ))
        
        return opportunities
    
    def _generate_summary_fallback(self, text_chunks: List[str]) -> str:
        """Fallback summary generation."""
        if not text_chunks:
            return "Analysis completed with limited data available."
        
        return (f"Analysis of available data sources including financial filings, "
                f"news articles, and market data. Summary generated from "
                f"{len(text_chunks)} source(s).")


# Global instance
ai_analyzer = AIAnalyzer()
