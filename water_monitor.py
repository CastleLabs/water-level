#!/usr/bin/env python3
"""
Core water monitoring logic with Slack integration and tare functionality
"""

import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

from sensor import DualSensorMonitor
from database import DatabaseManager
from slack_notifier import SlackNotifier

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
        
        # Initialize Slack notifier
        slack_config = self.config.get('slack', {})
        self.slack = SlackNotifier(slack_config)
        
        # Monitoring state
        self.running = False
        self.monitor_thread = None
        self.last_alert_time = None
        self.consecutive_leak_readings = 0
        self.system_startup_alerted = False
        
        # Initialize sensors (gracefully handle failure)
        if not self.sensors.initialize(self.config):
            logger.error("Failed to initialize sensors – continuing in degraded mode")
            # Send system alert to Slack
            self.slack.send_system_alert(
                "Sensor Initialization Failed", 
                "Water monitoring system started but sensors could not be initialized. Running in degraded mode. Check I2C connections and ADS1115 wiring."
            )
            # Do not raise; allow system to start with sensors disabled
        else:
            # Send startup notification and test connection
            self.slack.test_connection()
    
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
            'slack': {
                'enabled': False,
                'bot_token': '',
                'channel': '#water-alerts',
                'mention_users': ['@channel']
            },
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
            
            # Send startup alert to Slack
            if not self.system_startup_alerted:
                self.slack.send_recovery_alert("Water monitoring system started successfully with sensors active.")
                self.system_startup_alerted = True
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.sensors.cleanup()
        
        # Send shutdown notification
        self.slack.send_system_alert("System Shutdown", "Water monitoring system has been stopped.")
        
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
                    # Send system alert for persistent sensor errors
                    self.slack.send_system_alert(
                        "Sensor Read Error", 
                        f"Failed to read sensors: {reading['error']}"
                    )
                
                # Wait for next sample
                time.sleep(self.config.get('sample_interval', 60))
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                # Send system alert for unexpected errors
                self.slack.send_system_alert(
                    "Monitor Loop Error", 
                    f"Unexpected error in monitoring loop: {str(e)}"
                )
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
            if self.consecutive_leak_readings > 0:
                logger.debug("Leak readings reset - sensor difference back to normal")
            self.consecutive_leak_readings = 0
    
    def _trigger_alert(self, reading: Dict):
        """
        Trigger a leak alert with Slack notification
        
        Args:
            reading: Sensor reading that triggered the alert
        """
        # Check cooldown period
        cooldown = self.config.get('alert_cooldown', 3600)
        
        if self.last_alert_time:
            time_since_last = time.time() - self.last_alert_time
            if time_since_last < cooldown:
                logger.debug(f"Alert suppressed - still in cooldown ({int(cooldown - time_since_last)}s remaining)")
                return  # Still in cooldown
        
        # Create alert message
        message = (f"Potential leak detected! "
                  f"Difference: {reading['difference']:.1f}% "
                  f"(Reference: {reading['reference']['percentage']:.1f}%, "
                  f"Control: {reading['control']['percentage']:.1f}%)")
        
        # Store in database
        alert_id = self.db.add_alert('leak_detected', message, reading['difference'])
        self.last_alert_time = time.time()
        
        # Send to Slack
        slack_sent = self.slack.send_leak_alert(reading)
        
        if slack_sent:
            logger.warning(f"Leak alert sent to Slack: {message}")
        else:
            logger.warning(f"Leak alert created (Slack failed): {message}")
        
        # Reset consecutive counter after alerting
        self.consecutive_leak_readings = 0
    
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
            
            # Send calibration notification to Slack
            cal_type = "empty" if is_empty else "full"
            self.slack.send_system_alert(
                "Sensor Calibrated",
                f"{sensor_name.title()} sensor calibrated at {cal_type} level. Raw value: {result.get('raw_value', 'unknown')}"
            )
        
        return result
    
    def tare_sensor(self, sensor_name: str) -> Dict:
        """
        Tare (zero out) a sensor at current level
        
        Args:
            sensor_name: 'reference' or 'control'
            
        Returns:
            Tare result
        """
        if not self.sensors.initialized:
            return {'success': False, 'error': 'Sensors not initialized'}
        
        result = self.sensors.tare_sensor(sensor_name)
        
        if result.get('success'):
            # Save updated calibration
            self.save_config()
            
            # Send notification to Slack
            old_empty = result.get('old_empty', 'unknown')
            new_empty = result.get('new_empty', 'unknown')
            voltage = result.get('voltage', 'unknown')
            
            self.slack.send_system_alert(
                "Sensor Tared",
                f"{sensor_name.title()} sensor tared (zeroed out).\n"
                f"• Previous empty level: {old_empty}\n"
                f"• New empty level: {new_empty}\n"
                f"• Current voltage: {voltage}V\n"
                f"This sensor will now read 0% at current water level."
            )
            
            logger.info(f"{sensor_name} sensor tared successfully")
        
        return result
    
    def update_settings(self, settings: Dict):
        """
        Update configuration settings
        
        Args:
            settings: Dictionary of settings to update
        """
        # Update configuration
        old_config = self.config.copy()
        self.config.update(settings)
        
        # Check if Slack settings changed
        if 'slack' in settings:
            slack_config = self.config.get('slack', {})
            self.slack = SlackNotifier(slack_config)
            
            # Test new Slack configuration
            if slack_config.get('enabled'):
                success = self.slack.test_connection()
                if success:
                    logger.info("Slack configuration updated and tested successfully")
                else:
                    logger.warning("Slack configuration updated but test failed")
        
        # Save to file
        self.save_config()
        
        # Log significant setting changes
        if old_config.get('leak_threshold') != self.config.get('leak_threshold'):
            self.slack.send_system_alert(
                "Settings Updated",
                f"Leak detection threshold changed from {old_config.get('leak_threshold')}% to {self.config.get('leak_threshold')}%"
            )
        
        logger.info("Settings updated")
    
    def get_status(self) -> Dict:
        """Get system status"""
        latest = self.db.get_latest_reading()
        stats = self.db.get_statistics(24)
        alerts = self.db.get_active_alerts()
        
        return {
            'running': self.running,
            'sensors_initialized': self.sensors.initialized,
            'slack_enabled': self.slack.enabled if hasattr(self, 'slack') else False,
            'latest_reading': latest,
            'statistics': stats,
            'active_alerts': len(alerts),
            'consecutive_leak_readings': self.consecutive_leak_readings,
            'config': {
                'sample_interval': self.config.get('sample_interval'),
                'leak_threshold': self.config.get('leak_threshold'),
                'alert_cooldown': self.config.get('alert_cooldown'),
                'consecutive_readings_for_alert': self.config.get('consecutive_readings_for_alert')
            }
        }
