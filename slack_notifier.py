#!/usr/bin/env python3
"""
Slack notification service for water monitoring alerts
"""

import json
import logging
import time
from typing import Dict, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Send notifications to Slack via Bot Token"""
    
    def __init__(self, config: Dict):
        """
        Initialize Slack notifier
        
        Args:
            config: Slack configuration dictionary
        """
        self.enabled = config.get('enabled', False)
        self.bot_token = config.get('bot_token')
        self.channel = config.get('channel', '#alerts')
        self.mention_users = config.get('mention_users', [])
        
        if self.enabled and not self.bot_token:
            logger.error("Slack enabled but no bot token provided")
            self.enabled = False
        
        if self.enabled:
            logger.info(f"Slack notifications enabled for channel: {self.channel}")
    
    def send_leak_alert(self, reading: Dict) -> bool:
        """
        Send leak detection alert to Slack
        
        Args:
            reading: Sensor reading data that triggered the alert
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            # Build alert message
            message = self._build_leak_message(reading)
            
            # Send to Slack
            return self._send_message(message, urgent=True)
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def send_system_alert(self, alert_type: str, message: str) -> bool:
        """
        Send system status alert to Slack
        
        Args:
            alert_type: Type of system alert
            message: Alert message
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            slack_message = f":warning: *System Alert: {alert_type}*\n{message}"
            return self._send_message(slack_message, urgent=False)
            
        except Exception as e:
            logger.error(f"Failed to send system alert to Slack: {e}")
            return False
    
    def send_recovery_alert(self, message: str) -> bool:
        """
        Send system recovery notification
        
        Args:
            message: Recovery message
            
        Returns:
            True if message sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            slack_message = f":white_check_mark: *System Recovery*\n{message}"
            return self._send_message(slack_message, urgent=False)
            
        except Exception as e:
            logger.error(f"Failed to send recovery alert to Slack: {e}")
            return False
    
    def _build_leak_message(self, reading: Dict) -> str:
        """Build formatted leak alert message"""
        ref_pct = reading.get('reference', {}).get('percentage', 0)
        ctrl_pct = reading.get('control', {}).get('percentage', 0)
        difference = reading.get('difference', 0)
        
        # Format timestamp
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Build message with mentions
        mentions = ' '.join(self.mention_users) if self.mention_users else ''
        
        message = f""":rotating_light: *WATER LEAK DETECTED* :rotating_light:

{mentions}

*Alert Details:*
• Sensor Difference: {abs(difference):.1f}%
• Reference Sensor: {ref_pct:.1f}%
• Control Sensor: {ctrl_pct:.1f}%
• Detection Time: {timestamp}

*Action Required:*
Check water system immediately for potential leaks."""

        return message
    
    def _send_message(self, message: str, urgent: bool = False) -> bool:
        """
        Send message to Slack using Web API
        
        Args:
            message: Message text to send
            urgent: Whether this is an urgent alert
            
        Returns:
            True if successful
        """
        url = "https://slack.com/api/chat.postMessage"
        
        # Prepare payload
        payload = {
            'channel': self.channel,
            'text': message,
            'parse': 'full',
            'link_names': True
        }
        
        # Add urgent formatting if needed
        if urgent:
            payload['attachments'] = [{
                'color': 'danger',
                'text': message,
                'footer': 'Water Monitoring System',
                'ts': int(time.time())
            }]
        
        # Prepare request
        headers = {
            'Authorization': f'Bearer {self.bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Make request
            request = Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers,
                method='POST'
            )
            
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if result.get('ok'):
                    logger.info("Slack message sent successfully")
                    return True
                else:
                    logger.error(f"Slack API error: {result.get('error')}")
                    return False
                    
        except HTTPError as e:
            logger.error(f"HTTP error sending to Slack: {e.code} - {e.reason}")
            return False
        except URLError as e:
            logger.error(f"Network error sending to Slack: {e.reason}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to Slack: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test Slack connection and configuration
        
        Returns:
            True if connection works
        """
        if not self.enabled:
            logger.info("Slack notifications disabled")
            return False
        
        test_message = ":gear: Water monitoring system startup - Slack notifications active"
        return self._send_message(test_message, urgent=False)
