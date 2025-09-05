#!/usr/bin/env python3
"""
SQLite database operations for water monitoring system
"""

import sqlite3
import json
import logging
import queue
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage SQLite database for sensor readings and alerts"""
    
    def __init__(self, db_path: str = "readings.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.init_database()
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Main readings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reference_percentage REAL,
                    reference_raw INTEGER,
                    control_percentage REAL,
                    control_raw INTEGER,
                    difference REAL,
                    status TEXT
                )
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    alert_type TEXT NOT NULL,
                    message TEXT,
                    difference REAL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    acknowledged_at DATETIME
                )
            ''')
            
            # Create indices for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
                ON readings(timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp DESC)
            ''')
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def add_reading(self, data: Dict) -> int:
        """
        Add sensor reading to database
        
        Args:
            data: Reading data from sensors
            
        Returns:
            ID of inserted record
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO readings (
                    reference_percentage, reference_raw,
                    control_percentage, control_raw,
                    difference, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('reference', {}).get('percentage', 0),
                data.get('reference', {}).get('raw', 0),
                data.get('control', {}).get('percentage', 0),
                data.get('control', {}).get('raw', 0),
                data.get('difference', 0),
                data.get('status', 'unknown')
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_latest_reading(self) -> Optional[Dict]:
        """Get the most recent reading"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM readings 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_readings(self, hours: int = 24, limit: Optional[int] = None) -> List[Dict]:
        """
        Get readings from the last N hours
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of records
            
        Returns:
            List of reading dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            since = datetime.now() - timedelta(hours=hours)
            
            query = '''
                SELECT * FROM readings 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, (since.isoformat(),))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_readings_for_chart(self, hours: int = 24) -> Dict:
        """
        Get readings formatted for chart display
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with chart data
        """
        readings = self.get_readings(hours)
        
        # Reverse to get chronological order
        readings.reverse()
        
        # Downsample if too many points
        max_points = 200
        if len(readings) > max_points:
            step = len(readings) // max_points
            readings = readings[::step]
        
        return {
            'timestamps': [r['timestamp'] for r in readings],
            'reference': [r['reference_percentage'] for r in readings],
            'control': [r['control_percentage'] for r in readings],
            'difference': [r['difference'] for r in readings]
        }
    
    def add_alert(self, alert_type: str, message: str, difference: float) -> int:
        """
        Add alert to database
        
        Args:
            alert_type: Type of alert (e.g., 'leak_detected')
            message: Alert message
            difference: Sensor difference that triggered alert
            
        Returns:
            Alert ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO alerts (alert_type, message, difference)
                VALUES (?, ?, ?)
            ''', (alert_type, message, difference))
            
            conn.commit()
            logger.warning(f"Alert created: {alert_type} - {message}")
            return cursor.lastrowid
    
    def get_active_alerts(self) -> List[Dict]:
        """Get unacknowledged alerts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM alerts 
                WHERE acknowledged = FALSE 
                ORDER BY timestamp DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        Acknowledge an alert
        
        Args:
            alert_id: ID of alert to acknowledge
            
        Returns:
            Success status
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE alerts 
                SET acknowledged = TRUE, acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_statistics(self, hours: int = 24) -> Dict:
        """
        Get statistics for the specified time period
        
        Args:
            hours: Number of hours to analyze
            
        Returns:
            Statistics dictionary
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            since = datetime.now() - timedelta(hours=hours)
            
            # Get average values
            cursor.execute('''
                SELECT 
                    AVG(reference_percentage) as avg_reference,
                    AVG(control_percentage) as avg_control,
                    AVG(difference) as avg_difference,
                    MAX(difference) as max_difference,
                    MIN(difference) as min_difference,
                    COUNT(*) as reading_count
                FROM readings 
                WHERE timestamp > ?
            ''', (since.isoformat(),))
            
            stats = dict(cursor.fetchone())
            
            # Get alert count
            cursor.execute('''
                SELECT COUNT(*) as alert_count
                FROM alerts 
                WHERE timestamp > ?
            ''', (since.isoformat(),))
            
            stats['alert_count'] = cursor.fetchone()['alert_count']
            
            # Round values
            for key in ['avg_reference', 'avg_control', 'avg_difference', 
                       'max_difference', 'min_difference']:
                if stats.get(key) is not None:
                    stats[key] = round(stats[key], 1)
            
            return stats
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Remove data older than specified days
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            cursor.execute('''
                DELETE FROM readings 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            cursor.execute('''
                DELETE FROM alerts 
                WHERE timestamp < ? AND acknowledged = TRUE
            ''', (cutoff_date.isoformat(),))
            
            conn.commit()
            
            deleted_readings = cursor.rowcount
            logger.info(f"Cleaned up {deleted_readings} old records")