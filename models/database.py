"""
SQLite database manager for the AI Research Analyst Agent.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from .schemas import (
    AnalysisRun, DataSource, TextChunk, Memo,
    RunStatus, SourceType
)
from core.config import DATABASE_PATH

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager."""
        self.db_path = db_path or str(DATABASE_PATH)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                self._create_tables(conn)
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create database tables."""
        # Analysis runs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                started_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP,
                status TEXT NOT NULL,
                error_message TEXT,
                metadata TEXT
            )
        """)
        
        # Data sources table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                url TEXT,
                title TEXT,
                published_at TIMESTAMP,
                checksum TEXT,
                raw_content TEXT,
                metadata TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            )
        """)
        
        # Text chunks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
            )
        """)
        
        # Memos table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                tldr TEXT NOT NULL,
                risks_json TEXT NOT NULL,
                opportunities_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                html_content TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                metadata TEXT,
                FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_query ON runs(query)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_run_id ON sources(run_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sources_type ON sources(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source_id ON chunks(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memos_run_id ON memos(run_id)")
        
        conn.commit()
    
    def _dict_to_json(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to JSON string."""
        return json.dumps(data) if data else "{}"
    
    def _json_to_dict(self, json_str: str) -> Dict[str, Any]:
        """Convert JSON string to dictionary."""
        try:
            return json.loads(json_str) if json_str else {}
        except json.JSONDecodeError:
            return {}
    
    def create_run(self, query: str) -> int:
        """Create a new analysis run and return its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO runs (query, started_at, status)
                    VALUES (?, ?, ?)
                """, (query, datetime.now(), RunStatus.PENDING.value))
                run_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created analysis run {run_id} for query: {query}")
                return run_id
        except Exception as e:
            logger.error(f"Failed to create run: {e}")
            raise
    
    def update_run_status(self, run_id: int, status: RunStatus, 
                         error_message: Optional[str] = None):
        """Update the status of an analysis run."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if status == RunStatus.COMPLETED:
                    conn.execute("""
                        UPDATE runs 
                        SET status = ?, finished_at = ?, error_message = ?
                        WHERE id = ?
                    """, (status.value, datetime.now(), error_message, run_id))
                else:
                    conn.execute("""
                        UPDATE runs 
                        SET status = ?, error_message = ?
                        WHERE id = ?
                    """, (status.value, error_message, run_id))
                conn.commit()
                logger.info(f"Updated run {run_id} status to {status.value}")
        except Exception as e:
            logger.error(f"Failed to update run status: {e}")
            raise
    
    def add_source(self, run_id: int, source_type: SourceType, url: Optional[str] = None,
                   title: Optional[str] = None, published_at: Optional[datetime] = None,
                   checksum: Optional[str] = None, raw_content: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a data source and return its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO sources (run_id, type, url, title, published_at, checksum, raw_content, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (run_id, source_type.value if hasattr(source_type, 'value') else source_type, url, title, published_at, checksum, 
                      raw_content, self._dict_to_json(metadata or {})))
                source_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Added source {source_id} of type {source_type.value if hasattr(source_type, 'value') else source_type} for run {run_id}")
                return source_id
        except Exception as e:
            logger.error(f"Failed to add source: {e}")
            raise
    
    def add_chunk(self, source_id: int, text: str, chunk_type: str,
                  metadata: Optional[Dict[str, Any]] = None) -> int:
        """Add a text chunk and return its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO chunks (source_id, text, chunk_type, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (source_id, text, chunk_type, self._dict_to_json(metadata or {}), datetime.now()))
                chunk_id = cursor.lastrowid
                conn.commit()
                return chunk_id
        except Exception as e:
            logger.error(f"Failed to add chunk: {e}")
            raise
    
    def save_memo(self, run_id: int, tldr: str, risks: List[Dict], 
                  opportunities: List[Dict], metrics: List[Dict],
                  html_content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """Save a generated memo and return its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO memos (run_id, tldr, risks_json, opportunities_json, metrics_json, html_content, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (run_id, tldr, json.dumps(risks), json.dumps(opportunities), 
                      json.dumps(metrics), html_content, datetime.now(), 
                      self._dict_to_json(metadata or {})))
                memo_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Saved memo {memo_id} for run {run_id}")
                return memo_id
        except Exception as e:
            logger.error(f"Failed to save memo: {e}")
            raise
    
    def get_run(self, run_id: int) -> Optional[AnalysisRun]:
        """Get an analysis run by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, query, started_at, finished_at, status, error_message, metadata
                    FROM runs WHERE id = ?
                """, (run_id,))
                row = cursor.fetchone()
                if row:
                    return AnalysisRun(
                        id=row[0],
                        query=row[1],
                        started_at=datetime.fromisoformat(row[2]),
                        finished_at=datetime.fromisoformat(row[3]) if row[3] else None,
                        status=RunStatus(row[4]),
                        error_message=row[5],
                        metadata=self._json_to_dict(row[6])
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get run: {e}")
            return None
    
    def get_sources(self, run_id: int) -> List[DataSource]:
        """Get all sources for a run."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, run_id, type, url, title, published_at, checksum, raw_content, metadata
                    FROM sources WHERE run_id = ?
                """, (run_id,))
                sources = []
                for row in cursor.fetchall():
                    sources.append(DataSource(
                        id=row[0],
                        run_id=row[1],
                        type=SourceType(row[2]),
                        url=row[3],
                        title=row[4],
                        published_at=datetime.fromisoformat(row[5]) if row[5] else None,
                        checksum=row[6],
                        raw_content=row[7],
                        metadata=self._json_to_dict(row[8])
                    ))
                return sources
        except Exception as e:
            logger.error(f"Failed to get sources: {e}")
            return []
    
    def get_memo(self, run_id: int) -> Optional[Memo]:
        """Get the memo for a run."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, run_id, tldr, risks_json, opportunities_json, metrics_json, html_content, created_at, metadata
                    FROM memos WHERE run_id = ?
                """, (run_id,))
                row = cursor.fetchone()
                if row:
                    return Memo(
                        id=row[0],
                        run_id=row[1],
                        tldr=row[2],
                        risks=json.loads(row[3]),
                        opportunities=json.loads(row[4]),
                        metrics=json.loads(row[5]),
                        html_content=row[6],
                        created_at=datetime.fromisoformat(row[7]),
                        metadata=self._json_to_dict(row[8])
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get memo: {e}")
            return None
    
    def get_recent_runs(self, limit: int = 10) -> List[AnalysisRun]:
        """Get recent analysis runs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, query, started_at, finished_at, status, error_message, metadata
                    FROM runs ORDER BY started_at DESC LIMIT ?
                """, (limit,))
                runs = []
                for row in cursor.fetchall():
                    runs.append(AnalysisRun(
                        id=row[0],
                        query=row[1],
                        started_at=datetime.fromisoformat(row[2]),
                        finished_at=datetime.fromisoformat(row[3]) if row[3] else None,
                        status=RunStatus(row[4]),
                        error_message=row[5],
                        metadata=self._json_to_dict(row[6])
                    ))
                return runs
        except Exception as e:
            logger.error(f"Failed to get recent runs: {e}")
            return []
    
    def cleanup_old_runs(self, days_old: int = 30):
        """Clean up old analysis runs and related data."""
        try:
            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
            
            with sqlite3.connect(self.db_path) as conn:
                # Delete old memos, chunks, sources, and runs
                conn.execute("DELETE FROM memos WHERE created_at < ?", (cutoff_date,))
                conn.execute("DELETE FROM chunks WHERE created_at < ?", (cutoff_date,))
                conn.execute("DELETE FROM sources WHERE run_id IN (SELECT id FROM runs WHERE started_at < ?)", (cutoff_date,))
                conn.execute("DELETE FROM runs WHERE started_at < ?", (cutoff_date,))
                conn.commit()
                
                logger.info(f"Cleaned up runs older than {cutoff_date}")
        except Exception as e:
            logger.error(f"Failed to cleanup old runs: {e}")
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}
                
                # Count records in each table
                for table in ['runs', 'sources', 'chunks', 'memos']:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # Get recent activity
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM runs 
                    WHERE started_at > datetime('now', '-7 days')
                """)
                stats['runs_last_7_days'] = cursor.fetchone()[0]
                
                # Get database size
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                stats['database_size_mb'] = (page_count * page_size) / (1024 * 1024)
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
