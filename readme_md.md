WATER LEVEL MONITORING SYSTEM
==============================

A Raspberry Pi-based dual-sensor water level monitoring system with leak detection capabilities.


OVERVIEW
--------
This system uses two eTape liquid level sensors to monitor water levels and detect leaks:
- Reference Sensor: Monitors the main water container.
- Control Sensor: Placed in a sealed container inside the main container.

When both sensors show a similar level (factoring out environmental changes), the system is operating normally. A significant difference between the sensors indicates a potential leak in the main container.


FEATURES
--------
- Real-time Monitoring: Continuous water level monitoring with configurable intervals.
- Leak Detection: Automatic detection when sensor readings diverge.
- Web Dashboard: Browser-based interface for monitoring and configuration.
- Alert System: Visual alerts when leaks are detected.
- Historical Data: Charts showing water levels over time.
- Sensor Calibration: Easy calibration through the web interface.
- Auto-start Service: Runs automatically on system boot.


HARDWARE REQUIREMENTS
---------------------
- Raspberry Pi (3, 4, 5, or Zero with I2C interface)
- ADS1115 16-bit ADC Module (Analog-to-Digital Converter)
- 2x eTape Liquid Level Sensors (5 inch)
- 2x 10kΩ resistors
- Breadboard and jumper wires
- Two water containers (one sealed, placed inside the other)


SOFTWARE REQUIREMENTS
---------------------
- Raspberry Pi OS (Bullseye or newer)
- Python 3.7+
- I2C interface enabled


INSTALLATION
------------

### 1. Enable I2C Interface
    sudo raspi-config
    # Navigate to Interface Options -> I2C -> Enable

### 2. Clone or Copy Files
Create a project directory and copy all project files:
    mkdir ~/water-monitor
    cd ~/water-monitor
    # Copy all .py files, config.json, install.sh, templates/, and static/ folders here

### 3. Run Installation Script
    sudo bash install.sh

This will:
- Install system dependencies
- Install Python packages
- Set up the systemd service
- Configure auto-start on boot

### 4. Connect Hardware
Follow the wiring guide in `wiring_guide.md` to connect:
- ADS1115 to Raspberry Pi I2C pins
- eTape sensors to ADS1115 channels 0 and 1

### 5. Start the Service
    sudo systemctl start water-monitor

### 6. Access Dashboard
Open a web browser and navigate to:
    http://[your-pi-ip-address]:5000


CONFIGURATION
-------------

### Initial Calibration
1. Open the web dashboard.
2. Ensure the containers are empty.
3. On the dashboard, click "Calibrate Empty" for both the Reference and Control sensors.
4. Fill the main container to your desired "full" level.
5. Click "Calibrate Full" for both sensors.

### Settings
Access the Settings page to configure:
- Sample Interval: How often to read sensors (30-600 seconds).
- Leak Threshold: The percentage difference that triggers an alert (1-20%).
- Consecutive Readings: The number of consecutive readings before an alert is created (1-10).
- Alert Cooldown: The minimum time between new alerts (300-7200 seconds).


USAGE COMMANDS
--------------
# Start the monitoring service
sudo systemctl start water-monitor

# Stop the service
sudo systemctl stop water-monitor

# Restart the service
sudo systemctl restart water-monitor

# View the service's current status
sudo systemctl status water-monitor

# View live logs
sudo journalctl -u water-monitor -f

# Disable auto-start
sudo systemctl disable water-monitor

# Enable auto-start
sudo systemctl enable water-monitor


FILE STRUCTURE
--------------
water-monitor/
├── main.py                 # Main entry point
├── water_monitor.py        # Core monitoring logic
├── sensor.py               # Sensor interface (for ADS1115)
├── database.py             # Database operations
├── web_app.py              # Flask web application
├── config.json             # Configuration file
├── readings.db             # SQLite database (created at runtime)
├── templates/
│   ├── dashboard.html      # Main dashboard
│   └── settings.html       # Settings page
├── static/
│   ├── style.css           # Styles
│   └── dashboard.js        # Dashboard JavaScript
├── install.sh              # Installation script
├── wiring_guide.md         # Hardware connection guide (for ADS1115)
└── README.md               # This file


API ENDPOINTS
-------------
The system provides REST API endpoints for integration:

- GET /api/current                 - Current sensor readings
- GET /api/history/<hours>         - Historical data
- GET /api/statistics/<hours>      - Statistics
- GET /api/alerts                  - Active alerts
- POST /api/alerts/acknowledge/<id> - Acknowledge alert
- GET/POST /api/settings           - System settings
- POST /api/calibrate              - Calibrate sensors
- GET /api/status                  - System status


TROUBLESHOOTING
---------------

### No Sensor Readings
1. Check that the I2C interface is enabled.
2. Verify I2C wiring connections.
3. Scan for the device. The ADS1115 should appear at address 48.
   sudo i2cdetect -y 1
4. Check service logs for errors: sudo journalctl -u water-monitor -f

### Incorrect Readings
1. Recalibrate sensors from the dashboard.
2. Check the 10kΩ pull-down resistors are correctly wired.
3. Ensure sensors are placed vertically and are secure.
4. Verify the power supply is a stable 3.3V.

### Web Interface Not Loading
1. Check that the service is running: sudo systemctl status water-monitor
2. Verify your device is on the same network as the Pi.
3. Check if port 5000 is in use by another application: sudo lsof -i :5000

### Database Errors
1. Check file permissions on readings.db in the install directory.
2. If corrupted, delete readings.db (the application will recreate it).
3. Check available disk space: df -h


MAINTENANCE
-----------
- Weekly: Check calibration accuracy.
- Monthly: Clean sensor surfaces to prevent buildup.
- Quarterly: Backup the readings.db database file.
- Annually: Consider replacing resistors if readings begin to drift significantly.
