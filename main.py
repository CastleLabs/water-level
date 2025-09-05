#!/usr/bin/env python3
"""
Main entry point for water monitoring system
"""

import sys
import signal
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('water_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import components
from water_monitor import WaterMonitor
from web_app import app, set_monitor


# Global monitor instance
monitor = None


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    logger.info("Shutdown signal received")
    if monitor:
        monitor.stop()
    sys.exit(0)


def main():
    """Main application entry point"""
    global monitor
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Water Level Monitoring System')
    parser.add_argument('--config', default='config.json', help='Path to config file')
    parser.add_argument('--port', type=int, default=5000, help='Web server port')
    parser.add_argument('--host', default='0.0.0.0', help='Web server host')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting Water Monitoring System")
        
        # Create necessary directories
        Path("templates").mkdir(exist_ok=True)
        Path("static").mkdir(exist_ok=True)
        
        # Initialize monitor
        monitor = WaterMonitor(config_path=args.config)
        
        # Start monitoring
        monitor.start()
        
        # Set monitor in web app
        set_monitor(monitor)
        
        # Start web server
        logger.info(f"Starting web server on {args.host}:{args.port}")
        logger.info(f"Dashboard available at http://{args.host}:{args.port}")
        
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=False  # Disable reloader to prevent duplicate threads
        )
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        if monitor:
            monitor.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()