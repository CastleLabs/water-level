#!/usr/bin/env python3
"""
Sensor interface for eTape water level sensors with ADS1115 ADC
"""

import time
import logging
from typing import Optional, Dict, List
from collections import deque
from datetime import datetime, timedelta

# Try to import ADS1115 library
try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    ADS_AVAILABLE = True
except ImportError:
    ADS_AVAILABLE = False
    logging.warning("ADS1115 library not installed. Install with: pip3 install adafruit-circuitpython-ads1x15")

logger = logging.getLogger(__name__)


class SensorHealthMonitor:
    """Monitor sensor health and detect failures"""
    
    def __init__(self, sensor_name: str):
        self.sensor_name = sensor_name
        self.voltage_history = deque(maxlen=100)
        self.raw_history = deque(maxlen=100)
        self.last_calibration_check = time.time()
        self.drift_baseline = None
        self.consecutive_errors = 0
        self.health_status = 'healthy'  # healthy, degraded, failed
        
    def update_readings(self, voltage: float, raw: int):
        """Update sensor readings for health analysis"""
        self.voltage_history.append((time.time(), voltage))
        self.raw_history.append((time.time(), raw))
        self.consecutive_errors = 0
        
    def record_error(self):
        """Record a sensor read error"""
        self.consecutive_errors += 1
        
    def check_health(self) -> Dict:
        """Comprehensive sensor health check"""
        issues = []
        
        # Check for consistent errors
        if self.consecutive_errors > 5:
            self.health_status = 'failed'
            issues.append(f"Consecutive read errors: {self.consecutive_errors}")
        
        # Check voltage stability
        voltage_issue = self._check_voltage_stability()
        if voltage_issue:
            issues.append(voltage_issue)
        
        # Check for drift
        drift_issue = self._check_calibration_drift()
        if drift_issue:
            issues.append(drift_issue)
        
        # Check for stuck readings
        stuck_issue = self._check_stuck_readings()
        if stuck_issue:
            issues.append(stuck_issue)
        
        # Update health status
        if not issues and self.health_status == 'failed':
            self.health_status = 'healthy'
        elif issues and self.health_status == 'healthy':
            self.health_status = 'degraded'
        
        return {
            'sensor': self.sensor_name,
            'status': self.health_status,
            'issues': issues,
            'last_voltage': self.voltage_history[-1][1] if self.voltage_history else 0,
            'voltage_stability': self._calculate_voltage_stability(),
            'consecutive_errors': self.consecutive_errors
        }
    
    def _check_voltage_stability(self) -> Optional[str]:
        """Check if voltage readings are stable"""
        if len(self.voltage_history) < 10:
            return None
        
        recent_voltages = [v[1] for v in list(self.voltage_history)[-10:]]
        voltage_range = max(recent_voltages) - min(recent_voltages)
        
        # Flag if voltage varies more than 0.5V
        if voltage_range > 0.5:
            return f"Unstable voltage: {voltage_range:.3f}V range"
        
        # Check for extremely low/high voltages
        avg_voltage = sum(recent_voltages) / len(recent_voltages)
        if avg_voltage < 0.1:
            return "Voltage too low - possible disconnection"
        if avg_voltage > 3.2:
            return "Voltage too high - possible short circuit"
        
        return None
    
    def _check_calibration_drift(self) -> Optional[str]:
        """Check for calibration drift over time"""
        # Only check every 24 hours
        if time.time() - self.last_calibration_check < 86400:
            return None
        
        if len(self.voltage_history) < 50:
            return None
        
        # Get readings from 24 hours ago vs recent
        now = time.time()
        old_readings = [v[1] for t, v in self.voltage_history if now - t > 82800]  # 23+ hours ago
        new_readings = [v[1] for t, v in self.voltage_history if now - t < 3600]   # Last hour
        
        if len(old_readings) < 5 or len(new_readings) < 5:
            return None
        
        old_avg = sum(old_readings) / len(old_readings)
        new_avg = sum(new_readings) / len(new_readings)
        drift = abs(new_avg - old_avg)
        
        self.last_calibration_check = now
        
        if drift > 0.2:  # 200mV drift
            return f"Possible calibration drift: {drift:.3f}V change in 24h"
        
        return None
    
    def _check_stuck_readings(self) -> Optional[str]:
        """Check for stuck/unchanging readings"""
        if len(self.raw_history) < 20:
            return None
        
        recent_raw = [r[1] for r in list(self.raw_history)[-20:]]
        unique_values = len(set(recent_raw))
        
        # If less than 3 unique values in 20 readings, sensor might be stuck
        if unique_values < 3:
            return f"Sensor appears stuck: only {unique_values} unique values in 20 readings"
        
        return None
    
    def _calculate_voltage_stability(self) -> float:
        """Calculate voltage stability score (0-100)"""
        if len(self.voltage_history) < 5:
            return 50  # Neutral score
        
        voltages = [v[1] for v in list(self.voltage_history)[-20:]]
        voltage_range = max(voltages) - min(voltages)
        
        # Convert range to stability score (lower range = higher stability)
        stability = max(0, 100 - (voltage_range * 100))
        return round(stability, 1)


class ADS1115Interface:
    """Interface for ADS1115 16-bit ADC"""
    
    def __init__(self, address: int = 0x48):
        """
        Initialize I2C connection to ADS1115
        
        Args:
            address: I2C address (default 0x48)
        """
        if not ADS_AVAILABLE:
            raise ImportError("ADS1115 library not available. Please install adafruit-circuitpython-ads1x15")
        
        try:
            # Create the I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Create the ADC object using the I2C bus
            self.ads = ADS.ADS1115(i2c, address=address)
            
            # Set gain to 1 (±4.096V range - good for 3.3V systems)
            self.ads.gain = 1
            
            logger.info(f"ADS1115 initialized at address 0x{address:02X}")
        except Exception as e:
            logger.error(f"Failed to initialize ADS1115: {e}")
            raise
    
    def read_channel(self, channel: int) -> float:
        """
        Read voltage from channel
        
        Args:
            channel: ADC channel (0-3)
            
        Returns:
            Voltage reading
        """
        if channel < 0 or channel > 3:
            raise ValueError("Channel must be 0-3")
        
        try:
            # Create analog input on the specified channel
            if channel == 0:
                chan = AnalogIn(self.ads, ADS.P0)
            elif channel == 1:
                chan = AnalogIn(self.ads, ADS.P1)
            elif channel == 2:
                chan = AnalogIn(self.ads, ADS.P2)
            else:
                chan = AnalogIn(self.ads, ADS.P3)
            
            return chan.voltage
        except Exception as e:
            logger.error(f"Error reading channel {channel}: {e}")
            return 0.0
    
    def read_raw(self, channel: int) -> int:
        """
        Read raw ADC value from channel
        
        Args:
            channel: ADC channel (0-3)
            
        Returns:
            Raw ADC value (0-65535)
        """
        if channel < 0 or channel > 3:
            raise ValueError("Channel must be 0-3")
        
        try:
            # Create analog input on the specified channel
            if channel == 0:
                chan = AnalogIn(self.ads, ADS.P0)
            elif channel == 1:
                chan = AnalogIn(self.ads, ADS.P1)
            elif channel == 2:
                chan = AnalogIn(self.ads, ADS.P2)
            else:
                chan = AnalogIn(self.ads, ADS.P3)
            
            return chan.value
        except Exception as e:
            logger.error(f"Error reading channel {channel}: {e}")
            return 0


class WaterLevelSensor:
    """eTape water level sensor interface with health monitoring"""
    
    def __init__(self, adc: ADS1115Interface, channel: int, name: str, config: Dict):
        """
        Initialize sensor
        
        Args:
            adc: ADS1115Interface instance
            channel: ADC channel (0-3)
            name: Sensor name
            config: Configuration dict with calibration values
        """
        self.adc = adc
        self.channel = channel
        self.name = name
        # Updated default values for 16-bit ADC (0-65535 range)
        self.calibration_empty = config.get('calibration_empty', 50000)
        self.calibration_full = config.get('calibration_full', 20000)
        self.last_reading = None
        self.last_voltage = None
        self.last_percentage = None
        
        # Health monitoring
        self.health_monitor = SensorHealthMonitor(name)
        self.auto_recovery_enabled = config.get('auto_recovery', True)
        self.last_health_report = time.time()
        
    def read_raw(self, samples: int = 10) -> int:
        """
        Read raw ADC value with averaging
        
        Args:
            samples: Number of samples to average
            
        Returns:
            Average ADC value (0-65535)
        """
        readings = []
        for _ in range(samples):
            value = self.adc.read_raw(self.channel)
            if value > 0:  # Filter out error readings
                readings.append(value)
            time.sleep(0.01)
        
        if readings:
            self.last_reading = int(sum(readings) / len(readings))
            return self.last_reading
        return 0
    
    def read_voltage(self, samples: int = 10) -> float:
        """
        Read voltage with averaging
        
        Args:
            samples: Number of samples to average
            
        Returns:
            Average voltage
        """
        voltages = []
        for _ in range(samples):
            voltage = self.adc.read_channel(self.channel)
            if voltage > 0:
                voltages.append(voltage)
            time.sleep(0.01)
        
        if voltages:
            self.last_voltage = sum(voltages) / len(voltages)
            return self.last_voltage
        return 0.0
    
    def read_percentage(self) -> float:
        """
        Read water level as percentage (0-100) with health monitoring
        
        Returns:
            Water level percentage
        """
        try:
            raw = self.read_raw()
            voltage = self.read_voltage()
            
            # Update health monitoring
            self.health_monitor.update_readings(voltage, raw)
            
            # eTape resistance decreases as water level increases
            # So lower ADC values = more water
            if self.calibration_empty > self.calibration_full:
                percentage = ((self.calibration_empty - raw) / 
                             (self.calibration_empty - self.calibration_full)) * 100
            else:
                # Fallback if calibration values are inverted
                percentage = ((raw - self.calibration_full) / 
                             (self.calibration_empty - self.calibration_full)) * 100
            
            # Clamp between 0 and 100
            percentage = max(0, min(100, percentage))
            self.last_percentage = round(percentage, 1)
            
            # Auto-recovery attempt if sensor seems stuck
            if self._should_attempt_recovery():
                self._attempt_auto_recovery()
            
            return self.last_percentage
            
        except Exception as e:
            self.health_monitor.record_error()
            logger.error(f"Error reading {self.name}: {e}")
            return self.last_percentage or 0
    
    def calibrate(self, is_empty: bool = True) -> int:
        """
        Calibrate sensor at empty or full level
        
        Args:
            is_empty: True for empty calibration, False for full
            
        Returns:
            Raw ADC value used for calibration
        """
        # Take more samples for calibration
        raw = self.read_raw(samples=50)
        
        if is_empty:
            self.calibration_empty = raw
            logger.info(f"{self.name}: Empty calibration set to {raw}")
        else:
            self.calibration_full = raw
            logger.info(f"{self.name}: Full calibration set to {raw}")
        
        return raw
    
    def get_calibration(self) -> Dict:
        """Get current calibration values"""
        return {
            'calibration_empty': self.calibration_empty,
            'calibration_full': self.calibration_full
        }
    
    def get_health_status(self) -> Dict:
        """Get comprehensive health status"""
        return self.health_monitor.check_health()
    
    def _should_attempt_recovery(self) -> bool:
        """Check if auto-recovery should be attempted"""
        if not self.auto_recovery_enabled:
            return False
        
        health = self.health_monitor.check_health()
        return health['status'] == 'degraded' and 'stuck' in str(health['issues'])
    
    def _attempt_auto_recovery(self):
        """Attempt automatic sensor recovery"""
        logger.info(f"Attempting auto-recovery for {self.name}")
        
        try:
            # Power cycle simulation - wait and re-read
            time.sleep(2)
            
            # Take several readings to clear any stuck values
            for _ in range(5):
                self.adc.read_raw(self.channel)
                time.sleep(0.1)
            
            logger.info(f"Auto-recovery completed for {self.name}")
            
        except Exception as e:
            logger.error(f"Auto-recovery failed for {self.name}: {e}")


class DualSensorMonitor:
    """Monitor for comparing reference and control sensors"""
    
    def __init__(self):
        """Initialize dual sensor monitor"""
        self.adc = None
        self.reference_sensor = None
        self.control_sensor = None
        self.initialized = False
        
    def initialize(self, config: Dict) -> bool:
        """
        Initialize sensors with configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if successful
        """
        try:
            # Initialize ADC with I2C address from config or default
            i2c_address = config.get('i2c_address', 0x48)
            self.adc = ADS1115Interface(address=i2c_address)
            
            # Initialize reference sensor (main container)
            self.reference_sensor = WaterLevelSensor(
                self.adc, 
                channel=0,
                name="Reference",
                config=config.get('reference_sensor', {})
            )
            
            # Initialize control sensor (sealed container)
            self.control_sensor = WaterLevelSensor(
                self.adc,
                channel=1,
                name="Control",
                config=config.get('control_sensor', {})
            )
            
            self.initialized = True
            logger.info("Dual sensor monitor initialized successfully with ADS1115")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize sensors: {e}")
            self.cleanup()
            return False
    
    def read_both(self) -> Dict:
        """
        Read both sensors and calculate difference
        
        Returns:
            Dictionary with sensor readings and analysis
        """
        if not self.initialized:
            return {'error': 'Sensors not initialized'}
        
        try:
            ref_percentage = self.reference_sensor.read_percentage()
            ref_voltage = self.reference_sensor.last_voltage
            ctrl_percentage = self.control_sensor.read_percentage()
            ctrl_voltage = self.control_sensor.last_voltage
            difference = ref_percentage - ctrl_percentage
            
            return {
                'reference': {
                    'percentage': ref_percentage,
                    'raw': self.reference_sensor.last_reading,
                    'voltage': round(ref_voltage, 3) if ref_voltage else 0
                },
                'control': {
                    'percentage': ctrl_percentage,
                    'raw': self.control_sensor.last_reading,
                    'voltage': round(ctrl_voltage, 3) if ctrl_voltage else 0
                },
                'difference': round(difference, 1),
                'timestamp': time.time(),
                'status': 'normal' if abs(difference) < 5 else 'leak_detected'
            }
            
        except Exception as e:
            logger.error(f"Error reading sensors: {e}")
            return {'error': str(e)}
    
    def calibrate_sensor(self, sensor_name: str, is_empty: bool) -> Dict:
        """
        Calibrate specific sensor
        
        Args:
            sensor_name: 'reference' or 'control'
            is_empty: True for empty, False for full
            
        Returns:
            Calibration result
        """
        if not self.initialized:
            return {'error': 'Sensors not initialized'}
        
        sensor = (self.reference_sensor if sensor_name == 'reference' 
                 else self.control_sensor)
        
        raw_value = sensor.calibrate(is_empty)
        
        return {
            'sensor': sensor_name,
            'type': 'empty' if is_empty else 'full',
            'raw_value': raw_value,
            'success': True
        }
    
    def get_calibration_values(self) -> Dict:
        """Get all calibration values"""
        if not self.initialized:
            return {}
        
        return {
            'reference_sensor': self.reference_sensor.get_calibration(),
            'control_sensor': self.control_sensor.get_calibration()
        }
    
    def get_system_health(self) -> Dict:
        """Get comprehensive system health report"""
        if not self.initialized:
            return {'status': 'failed', 'message': 'Sensors not initialized'}
        
        ref_health = self.reference_sensor.get_health_status()
        ctrl_health = self.control_sensor.get_health_status()
        
        # Overall system health
        system_status = 'healthy'
        if ref_health['status'] == 'failed' or ctrl_health['status'] == 'failed':
            system_status = 'failed'
        elif ref_health['status'] == 'degraded' or ctrl_health['status'] == 'degraded':
            system_status = 'degraded'
        
        return {
            'system_status': system_status,
            'reference_sensor': ref_health,
            'control_sensor': ctrl_health,
            'last_reading': None,  # Will be populated by caller
        }
    
    def cleanup(self):
        """Clean up resources"""
        # No specific cleanup needed for I2C
        self.initialized = False
        logger.info("Sensor resources cleaned up")