#!/usr/bin/env python3
"""
Core water monitoring logic
"""

import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from sensor import DualSensorMonitor
from database import DatabaseManager

logger = logging.getLogger(__name__)


class WaterMonitor:
    """Main water monitoring service"""
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize water monitor"""
        self.config_path = config_path
        self.config = self.load_config()
        
        # Initialize components
        self.sensors = DualSensorMonitor()
        self.db = DatabaseManager(self.config.get('database_path', 'readings.db'))
        
        # Monitoring state
        self.running = False
        self.monitor_thread = None
        self.last_alert_time = None
        self.consecutive_leak_readings = 0
        
        # Initialize sensors (gracefully handle failure)
        if not self.sensors.initialize(self.config):
            logger.error("Failed to initialize sensors – continuing in degraded mode")
            # Do not raise; allow system to start with sensors disabled
    
    def load_config(self) -> Dict:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except FileNotFoundError:
            logger.warning(f"Config file not found, using defaults")
            return self.get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'sample_interval': 60,  # seconds
            'leak_threshold': 5.0,  # percentage difference
            'alert_cooldown': 3600,  # seconds between alerts
            'consecutive_readings_for_alert': 3,  # readings before alert
            'database_path': 'readings.db',
            'reference_sensor': {
                'calibration_empty': 800,
                'calibration_full': 400
            },
            'control_sensor': {
                'calibration_empty': 800,
                'calibration_full': 400
            }
        }
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            # Update sensor calibration values
            calibration = self.sensors.get_calibration_values()
            self.config.update(calibration)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def start(self):
        """Start monitoring"""
        if not self.sensors.initialized:
            logger.warning("Sensors not initialized – monitoring loop will not run")
            return
        
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logger.info("Water monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.sensors.cleanup()
        logger.info("Water monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Monitoring loop started")
        
        while self.running:
            try:
                # Read sensors
                reading = self.sensors.read_both()
                
                if 'error' not in reading:
                    # Store reading
                    self.db.add_reading(reading)
                    
                    # Check for leaks
                    self._check_for_leak(reading)
                    
                    logger.debug(f"Reading stored: Ref={reading['reference']['percentage']:.1f}%, "
                               f"Ctrl={reading['control']['percentage']:.1f}%, "
                               f"Diff={reading['difference']:.1f}%")
                else:
                    logger.error(f"Sensor read error: {reading['error']}")
                
                # Wait for next sample
                time.sleep(self.config.get('sample_interval', 60))
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(5)  # Brief pause before retry
    
    def _check_for_leak(self, reading: Dict):
        """
        Check if reading indicates a leak
        
        Args:
            reading: Sensor reading dictionary
        """
        threshold = self.config.get('leak_threshold', 5.0)
        difference = abs(reading.get('difference', 0))
        
        if difference > threshold:
            self.consecutive_leak_readings += 1
            
            # Check if we should trigger an alert
            readings_needed = self.config.get('consecutive_readings_for_alert', 3)
            
            if self.consecutive_leak_readings >= readings_needed:
                self._trigger_alert(reading)
        else:
            # Reset counter if reading is normal
            self.consecutive_leak_readings = 0
    
    def _trigger_alert(self, reading: Dict):
        """
        Trigger a leak alert
        
        Args:
            reading: Sensor reading that triggered the alert
        """
        # Check cooldown period
        cooldown = self.config.get('alert_cooldown', 3600)
        
        if self.last_alert_time:
            time_since_last = time.time() - self.last_alert_time
            if time_since_last < cooldown:
                return  # Still in cooldown
        
        # Create alert
        message = (f"Potential leak detected! "
                  f"Difference: {reading['difference']:.1f}% "
                  f"(Reference: {reading['reference']['percentage']:.1f}%, "
                  f"Control: {reading['control']['percentage']:.1f}%)")
        
        self.db.add_alert('leak_detected', message, reading['difference'])
        self.last_alert_time = time.time()
        
        logger.warning(message)
    
    def get_current_reading(self) -> Dict:
        """Get current sensor reading"""
        return self.sensors.read_both()
    
    def calibrate_sensor(self, sensor_name: str, is_empty: bool) -> Dict:
        """
        Calibrate a sensor
        
        Args:
            sensor_name: 'reference' or 'control'
            is_empty: True for empty, False for full
            
        Returns:
            Calibration result
        """
        result = self.sensors.calibrate_sensor(sensor_name, is_empty)
        
        if result.get('success'):
            # Save updated calibration
            self.save_config()
        
        return result
    
    def update_settings(self, settings: Dict):
        """
        Update configuration settings
        
        Args:
            settings: Dictionary of settings to update
        """
        # Update configuration
        self.config.update(settings)
        
        # Save to file
        self.save_config()
        
        logger.info("Settings updated")
    
    def get_status(self) -> Dict:
        """Get system status"""
        latest = self.db.get_latest_reading()
        stats = self.db.get_statistics(24)
        alerts = self.db.get_active_alerts()
        
        return {
            'running': self.running,
            'sensors_initialized': self.sensors.initialized,
            'latest_reading': latest,
            'statistics': stats,
            'active_alerts': len(alerts),
            'config': {
                'sample_interval': self.config.get('sample_interval'),
                'leak_threshold': self.config.get('leak_threshold'),
                'alert_cooldown': self.config.get('alert_cooldown')
            }
        }
