#!/usr/bin/env python3
"""
Flask web application for water monitoring system
"""

from flask import Flask, render_template, jsonify, request, redirect, url_for
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'

# Global reference to monitor (set by main.py)
monitor = None


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html')


@app.route('/api/current')
def api_current():
    """Get current sensor readings"""
    if monitor:
        reading = monitor.get_current_reading()
        return jsonify(reading)
    return jsonify({'error': 'Monitor not initialized'}), 500


@app.route('/api/history/<int:hours>')
def api_history(hours):
    """Get historical data for charts"""
    if monitor:
        data = monitor.db.get_readings_for_chart(hours)
        return jsonify(data)
    return jsonify({'error': 'Monitor not initialized'}), 500


@app.route('/api/statistics/<int:hours>')
def api_statistics(hours):
    """Get statistics for specified time period"""
    if monitor:
        stats = monitor.db.get_statistics(hours)
        return jsonify(stats)
    return jsonify({'error': 'Monitor not initialized'}), 500


@app.route('/api/alerts')
def api_alerts():
    """Get active alerts"""
    if monitor:
        alerts = monitor.db.get_active_alerts()
        return jsonify(alerts)
    return jsonify({'error': 'Monitor not initialized'}), 500


@app.route('/api/alerts/acknowledge/<int:alert_id>', methods=['POST'])
def api_acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    if monitor:
        success = monitor.db.acknowledge_alert(alert_id)
        return jsonify({'success': success})
    return jsonify({'error': 'Monitor not initialized'}), 500


@app.route('/api/calibrate', methods=['POST'])
def api_calibrate():
    """Calibrate a sensor"""
    if monitor:
        data = request.json
        sensor_name = data.get('sensor', 'reference')
        is_empty = data.get('is_empty', True)
        
        # Validate sensor name
        if sensor_name not in ['reference', 'control']:
            return jsonify({'error': 'Invalid sensor name'}), 400
        
        result = monitor.calibrate_sensor(sensor_name, is_empty)
        return jsonify(result)
    return jsonify({'error': 'Monitor not initialized'}), 500


@app.route('/api/tare', methods=['POST'])
def api_tare():
    """Tare (zero out) a sensor"""
    if monitor:
        data = request.json
        sensor_name = data.get('sensor', 'reference')
        
        # Validate sensor name
        if sensor_name not in ['reference', 'control']:
            return jsonify({'error': 'Invalid sensor name'}), 400
        
        result = monitor.tare_sensor(sensor_name)
        return jsonify(result)
    return jsonify({'error': 'Monitor not initialized'}), 500


@app.route('/api/test-slack', methods=['POST'])
def api_test_slack():
    """Test Slack notification"""
    if not monitor:
        return jsonify({'error': 'Monitor not initialized'}), 500
    
    if not hasattr(monitor, 'slack') or not monitor.slack.enabled:
        return jsonify({'error': 'Slack notifications not enabled'}), 400
    
    try:
        success = monitor.slack.send_system_alert(
            "Test Alert", 
            "This is a test notification from your water monitoring system. If you see this message, Slack integration is working correctly!"
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Test message sent successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to send test message'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update settings"""
    if not monitor:
        return jsonify({'error': 'Monitor not initialized'}), 500
    
    if request.method == 'POST':
        # Update settings
        data = request.json
        
        # Validate and convert values
        settings = {}
        
        if 'sample_interval' in data:
            try:
                settings['sample_interval'] = int(data['sample_interval'])
                if settings['sample_interval'] < 30 or settings['sample_interval'] > 600:
                    return jsonify({'error': 'Sample interval must be between 30-600 seconds'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid sample_interval'}), 400
        
        if 'leak_threshold' in data:
            try:
                settings['leak_threshold'] = float(data['leak_threshold'])
                if settings['leak_threshold'] < 1 or settings['leak_threshold'] > 20:
                    return jsonify({'error': 'Leak threshold must be between 1-20%'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid leak_threshold'}), 400
        
        if 'alert_cooldown' in data:
            try:
                settings['alert_cooldown'] = int(data['alert_cooldown'])
                if settings['alert_cooldown'] < 300 or settings['alert_cooldown'] > 7200:
                    return jsonify({'error': 'Alert cooldown must be between 300-7200 seconds'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid alert_cooldown'}), 400
        
        if 'consecutive_readings_for_alert' in data:
            try:
                settings['consecutive_readings_for_alert'] = int(data['consecutive_readings_for_alert'])
                if settings['consecutive_readings_for_alert'] < 1 or settings['consecutive_readings_for_alert'] > 10:
                    return jsonify({'error': 'Consecutive readings must be between 1-10'}), 400
            except ValueError:
                return jsonify({'error': 'Invalid consecutive_readings_for_alert'}), 400
        
        # Handle Slack settings
        if 'slack' in data:
            slack_settings = data['slack']
            
            # Validate Slack configuration
            if slack_settings.get('enabled'):
                if not slack_settings.get('bot_token'):
                    return jsonify({'error': 'Bot token required when Slack is enabled'}), 400
                if not slack_settings.get('channel'):
                    return jsonify({'error': 'Channel required when Slack is enabled'}), 400
                
                # Ensure channel starts with #
                channel = slack_settings['channel'].strip()
                if not channel.startswith('#'):
                    channel = '#' + channel
                slack_settings['channel'] = channel
            
            settings['slack'] = slack_settings
        
        monitor.update_settings(settings)
        return jsonify({'success': True})
    
    else:
        # Get current settings
        return jsonify(monitor.config)


@app.route('/api/status')
def api_status():
    """Get system status"""
    if monitor:
        status = monitor.get_status()
        return jsonify(status)
    return jsonify({'error': 'Monitor not initialized'}), 500


def set_monitor(monitor_instance):
    """Set the monitor instance (called from main.py)"""
    global monitor
    monitor = monitor_instance

