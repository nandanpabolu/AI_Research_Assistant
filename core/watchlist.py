#!/usr/bin/env python3
"""
Watchlist management system for tracking multiple stocks.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)


class WatchlistManager:
    """Manage stock watchlists and automated monitoring."""
    
    def __init__(self, db_path: str = "data/watchlist.db"):
        """Initialize watchlist manager."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize watchlist database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchlists (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        watchlist_id INTEGER,
                        ticker TEXT NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_analyzed_at TIMESTAMP,
                        alert_enabled BOOLEAN DEFAULT TRUE,
                        price_target_high REAL,
                        price_target_low REAL,
                        notes TEXT,
                        FOREIGN KEY (watchlist_id) REFERENCES watchlists (id),
                        UNIQUE(watchlist_id, ticker)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchlist_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        watchlist_item_id INTEGER,
                        alert_type TEXT NOT NULL,
                        message TEXT NOT NULL,
                        triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        acknowledged BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (watchlist_item_id) REFERENCES watchlist_items (id)
                    )
                """)
                
                conn.commit()
                logger.info("Watchlist database initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize watchlist database: {e}")
    
    def create_watchlist(self, name: str, description: str = "") -> int:
        """Create a new watchlist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO watchlists (name, description) VALUES (?, ?)",
                    (name, description)
                )
                watchlist_id = cursor.lastrowid
                conn.commit()
                logger.info(f"Created watchlist '{name}' with ID {watchlist_id}")
                return watchlist_id
        except sqlite3.IntegrityError:
            logger.warning(f"Watchlist '{name}' already exists")
            return self.get_watchlist_by_name(name)["id"]
        except Exception as e:
            logger.error(f"Failed to create watchlist: {e}")
            raise
    
    def get_watchlists(self) -> List[Dict[str, Any]]:
        """Get all watchlists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT w.*, COUNT(wi.id) as item_count
                    FROM watchlists w
                    LEFT JOIN watchlist_items wi ON w.id = wi.watchlist_id
                    GROUP BY w.id
                    ORDER BY w.updated_at DESC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get watchlists: {e}")
            return []
    
    def get_watchlist_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get watchlist by name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM watchlists WHERE name = ?", (name,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get watchlist: {e}")
            return None
    
    def add_to_watchlist(self, watchlist_id: int, ticker: str, 
                        price_target_high: Optional[float] = None,
                        price_target_low: Optional[float] = None,
                        notes: str = "") -> bool:
        """Add ticker to watchlist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO watchlist_items 
                    (watchlist_id, ticker, price_target_high, price_target_low, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (watchlist_id, ticker.upper(), price_target_high, price_target_low, notes))
                
                # Update watchlist timestamp
                conn.execute(
                    "UPDATE watchlists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (watchlist_id,)
                )
                conn.commit()
                logger.info(f"Added {ticker} to watchlist {watchlist_id}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Ticker {ticker} already in watchlist {watchlist_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to add ticker to watchlist: {e}")
            return False
    
    def get_watchlist_items(self, watchlist_id: int) -> List[Dict[str, Any]]:
        """Get all items in a watchlist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT wi.*, COUNT(wa.id) as alert_count
                    FROM watchlist_items wi
                    LEFT JOIN watchlist_alerts wa ON wi.id = wa.watchlist_item_id 
                        AND wa.acknowledged = FALSE
                    WHERE wi.watchlist_id = ?
                    GROUP BY wi.id
                    ORDER BY wi.added_at ASC
                """, (watchlist_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get watchlist items: {e}")
            return []
    
    def remove_from_watchlist(self, watchlist_id: int, ticker: str) -> bool:
        """Remove ticker from watchlist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM watchlist_items 
                    WHERE watchlist_id = ? AND ticker = ?
                """, (watchlist_id, ticker.upper()))
                
                if cursor.rowcount > 0:
                    # Update watchlist timestamp
                    conn.execute(
                        "UPDATE watchlists SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (watchlist_id,)
                    )
                    conn.commit()
                    logger.info(f"Removed {ticker} from watchlist {watchlist_id}")
                    return True
                else:
                    logger.warning(f"Ticker {ticker} not found in watchlist {watchlist_id}")
                    return False
        except Exception as e:
            logger.error(f"Failed to remove ticker from watchlist: {e}")
            return False
    
    def update_last_analyzed(self, watchlist_id: int, ticker: str):
        """Update last analyzed timestamp for a ticker."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE watchlist_items 
                    SET last_analyzed_at = CURRENT_TIMESTAMP
                    WHERE watchlist_id = ? AND ticker = ?
                """, (watchlist_id, ticker.upper()))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update last analyzed: {e}")
    
    def create_alert(self, watchlist_item_id: int, alert_type: str, message: str):
        """Create an alert for a watchlist item."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO watchlist_alerts 
                    (watchlist_item_id, alert_type, message)
                    VALUES (?, ?, ?)
                """, (watchlist_item_id, alert_type, message))
                conn.commit()
                logger.info(f"Created alert for item {watchlist_item_id}: {alert_type}")
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
    
    def get_pending_alerts(self, watchlist_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get pending (unacknowledged) alerts."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if watchlist_id:
                    cursor = conn.execute("""
                        SELECT wa.*, wi.ticker, w.name as watchlist_name
                        FROM watchlist_alerts wa
                        JOIN watchlist_items wi ON wa.watchlist_item_id = wi.id
                        JOIN watchlists w ON wi.watchlist_id = w.id
                        WHERE wa.acknowledged = FALSE AND w.id = ?
                        ORDER BY wa.triggered_at DESC
                    """, (watchlist_id,))
                else:
                    cursor = conn.execute("""
                        SELECT wa.*, wi.ticker, w.name as watchlist_name
                        FROM watchlist_alerts wa
                        JOIN watchlist_items wi ON wa.watchlist_item_id = wi.id
                        JOIN watchlists w ON wi.watchlist_id = w.id
                        WHERE wa.acknowledged = FALSE
                        ORDER BY wa.triggered_at DESC
                    """)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get pending alerts: {e}")
            return []
    
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE watchlist_alerts SET acknowledged = TRUE WHERE id = ?",
                    (alert_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
    
    def get_stale_items(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get watchlist items that haven't been analyzed recently."""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT wi.*, w.name as watchlist_name
                    FROM watchlist_items wi
                    JOIN watchlists w ON wi.watchlist_id = w.id
                    WHERE wi.last_analyzed_at IS NULL 
                       OR wi.last_analyzed_at < ?
                    ORDER BY wi.last_analyzed_at ASC NULLS FIRST
                """, (cutoff,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get stale items: {e}")
            return []


# Global instance
watchlist_manager = WatchlistManager()
