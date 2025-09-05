# Water Level Monitoring System

A comprehensive water leak detection system using dual eTape sensors, designed for Raspberry Pi with web dashboard and Slack integration.

## Table of Contents

- [Overview](#overview)
- [Hardware Requirements](#hardware-requirements)
- [System Architecture](#system-architecture)
- [Raspberry Pi Setup](#raspberry-pi-setup)
- [Hardware Assembly](#hardware-assembly)
- [Software Installation](#software-installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Advanced Features](#advanced-features)

## Overview

This water monitoring system uses two eTape water level sensors to detect leaks by comparing water levels between a main container (reference sensor) and a control container (control sensor). When the difference exceeds a configurable threshold, the system triggers alerts via web dashboard and optional Slack notifications.

### Key Features

- **Dual-sensor leak detection** with configurable thresholds
- **Web-based dashboard** with real-time monitoring and historical charts
- **Slack integration** for instant notifications
- **Sensor calibration and tare functionality**
- **Health monitoring** with automatic sensor diagnostics
- **SQLite database** for data storage and statistics
- **RESTful API** for integration with other systems

## Hardware Requirements

### Essential Components

1. **Raspberry Pi 5** (or Pi 4/3B+ with minor modifications)
2. **ADS1115 16-bit ADC** (I2C interface)
3. **2x eTape Liquid Level Sensors** (12" or 24" recommended)
4. **2x 560Ω resistors** (for eTape sensor voltage dividers)
5. **Breadboard or PCB** for connections
6. **Jumper wires** (male-to-female and male-to-male)
7. **MicroSD card** (32GB+ recommended, Class 10)

### Optional Components

- **Waterproof enclosure** for electronics
- **Power supply** (USB-C for Pi 5, micro-USB for older models)
- **Ethernet cable** or ensure Wi-Fi connectivity

### eTape Sensor Specifications

- **Operating Voltage**: 5V DC
- **Output**: Variable resistance (increases with fluid level)
- **Accuracy**: ±12mm (0.5")
- **Temperature Range**: -40°C to +125°C
- **Thread**: ½" NPT

## System Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Reference     │    │              │    │    Control      │
│   Container     │    │  Raspberry   │    │   Container     │
│  (Main Tank)    │    │     Pi 5     │    │                 │
│                 │    │              │    │                 │
│  eTape Sensor ──┼────┤ ADS1115 ADC  ├────┼── eTape Sensor  │
│                 │    │              │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │
                              │
                    ┌─────────▼─────────┐
                    │   Web Dashboard   │
                    │   & Slack Alerts  │
                    └───────────────────┘
```

## Raspberry Pi Setup

### 1. Install Raspberry Pi OS

1. Download **Raspberry Pi Imager** from [rpi.org](https://www.raspberrypi.org/software/)
2. Flash **Raspberry Pi OS Lite** (64-bit) to SD card
3. Enable SSH and I2C during setup:
   - In imager, click gear icon for advanced options
   - Enable SSH with password authentication
   - Configure Wi-Fi credentials
   - Set username/password

### 2. Initial Pi Configuration

Boot the Pi and connect via SSH:

```bash
ssh pi@<pi-ip-address>
```

Update the system:
```bash
sudo apt update && sudo apt upgrade -y
```

Enable I2C:
```bash
sudo raspi-config
# Navigate to: Interface Options → I2C → Enable
sudo reboot
```

Install required system packages:
```bash
sudo apt install -y python3-pip python3-venv git i2c-tools
```

### 3. Verify I2C Setup

Test I2C detection:
```bash
i2cdetect -y 1
```

You should see a grid. After connecting the ADS1115, you'll see `48` at address 0x48.

## Hardware Assembly

### ADS1115 Wiring

Connect the ADS1115 to Raspberry Pi 5:

| ADS1115 Pin | Raspberry Pi 5 Pin | Wire Color |
|-------------|-------------------|------------|
| VDD         | 3.3V (Pin 1)      | Red        |
| GND         | GND (Pin 6)       | Black      |
| SCL         | SCL (Pin 5)       | Yellow     |
| SDA         | SDA (Pin 3)       | Blue       |

### eTape Sensor Wiring

Each eTape sensor requires a voltage divider circuit:

```
    3.3V ──┬── 560Ω ──┬── eTape Sensor ── GND
           │          │
           │          └── To ADS1115 Input
           │
    Reference to A0, Control to A1
```

**Reference Sensor (A0):**
- ADS1115 A0 to voltage divider output
- One eTape terminal to 3.3V through 560Ω resistor
- Other eTape terminal to GND

**Control Sensor (A1):**
- ADS1115 A1 to voltage divider output  
- One eTape terminal to 3.3V through 560Ω resistor
- Other eTape terminal to GND

### Physical Installation

1. **Reference Container**: Install eTape sensor in main water container/tank
2. **Control Container**: Install eTape sensor in reference container
3. **Sensor Placement**: Ensure sensors are at same relative height
4. **Sealing**: Use appropriate thread sealant for eTape installation
5. **Electronics**: Place Pi and ADS1115 in waterproof enclosure

## Software Installation

### 1. Clone Repository

```bash
cd /opt
sudo git clone <repository-url> water-monitor
sudo chown -R $USER:$USER /opt/water-monitor
cd /opt/water-monitor
```

### 2. Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
Flask==2.3.3
adafruit-circuitpython-ads1x15==2.2.21
adafruit-blinka==8.22.2
```

If `requirements.txt` doesn't exist, install manually:
```bash
pip install Flask adafruit-circuitpython-ads1x15 adafruit-blinka
```

### 4. Create Systemd Service

Create service file:
```bash
sudo nano /etc/systemd/system/water-monitor.service
```

Add content:
```ini
[Unit]
Description=Water Level Monitoring System
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/water-monitor
Environment=PATH=/opt/water-monitor/venv/bin
ExecStart=/opt/water-monitor/venv/bin/python main.py --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable water-monitor
sudo systemctl start water-monitor
```

### 5. Verify Installation

Check service status:
```bash
sudo systemctl status water-monitor
```

Check I2C device detection:
```bash
i2cdetect -y 1
```
You should see `48` at address 0x48 if ADS1115 is properly connected.

View logs:
```bash
tail -f /opt/water-monitor/water_monitor.log
```

## Configuration

### 1. Basic Configuration

Edit `config.json`:
```bash
nano /opt/water-monitor/config.json
```

**Key Settings:**
```json
{
  "sample_interval": 60,
  "leak_threshold": 5.0,
  "alert_cooldown": 3600,
  "consecutive_readings_for_alert": 3,
  "database_path": "readings.db",
  "i2c_address": 72,
  "reference_sensor": {
    "calibration_empty": 50000,
    "calibration_full": 20000
  },
  "control_sensor": {
    "calibration_empty": 50000,
    "calibration_full": 20000
  }
}
```

### 2. Slack Integration (Optional)

To enable Slack notifications:

1. **Create Slack App:**
   - Go to [api.slack.com/apps](https://api.slack.com/apps)
   - Click "Create New App" → "From scratch"
   - Name: "Water Monitor" 
   - Choose your workspace

2. **Configure OAuth & Permissions:**
   - Go to "OAuth & Permissions"
   - Add Bot Token Scopes:
     - `chat:write`
     - `chat:write.public`
   - Install app to workspace
   - Copy "Bot User OAuth Token" (starts with `xoxb-`)

3. **Update config.json:**
```json
{
  "slack": {
    "enabled": true,
    "bot_token": "xoxb-your-bot-token-here",
    "channel": "#water-alerts",
    "mention_users": ["@channel"]
  }
}
```

4. **Restart service:**
```bash
sudo systemctl restart water-monitor
```

### 3. Sensor Calibration

**Initial Calibration:**
1. Access dashboard at `http://<pi-ip>:5000`
2. Go to calibration section
3. With sensors in empty containers: Click "Calibrate Empty"
4. Fill containers to known level: Click "Calibrate Full"

**Tare Operation:**
- Use "Tare Sensor" to set current level as new 0% baseline
- Useful for field adjustments without full recalibration

## Usage

### Web Dashboard

Access the dashboard at: `http://<raspberry-pi-ip>:5000`

**Dashboard Features:**
- **Real-time readings** with leak detection status
- **Historical charts** (24 hours, 7 days, 30 days)
- **Statistics** and alert management
- **Sensor calibration** and tare controls

### Settings Page

Access settings at: `http://<raspberry-pi-ip>:5000/settings`

**Configurable Parameters:**
- Sample interval (30-600 seconds)
- Leak threshold (1-20%)
- Alert cooldown period
- Slack notification settings

### Alert Management

**Alert Types:**
- **Leak Detected**: Sensor difference exceeds threshold
- **System Alerts**: Sensor failures, startup notifications
- **Recovery Alerts**: System restoration notifications

**Alert Acknowledgment:**
- Click "Dismiss" on dashboard alerts
- Alerts auto-clear when conditions normalize

## API Reference

### Endpoints

#### Get Current Readings
```http
GET /api/current
```

**Response:**
```json
{
  "reference": {
    "percentage": 45.2,
    "raw": 32500,
    "voltage": 2.1
  },
  "control": {
    "percentage": 44.8,
    "raw": 32800,
    "voltage": 2.15
  },
  "difference": 0.4,
  "timestamp": 1693934567.123,
  "status": "normal"
}
```

#### Get Historical Data
```http
GET /api/history/{hours}
```

**Parameters:**
- `hours`: Number of hours (24, 168, 720)

#### Get Statistics
```http
GET /api/statistics/{hours}
```

**Response:**
```json
{
  "avg_reference": 45.1,
  "avg_control": 44.9,
  "avg_difference": 0.2,
  "max_difference": 2.1,
  "min_difference": -1.8,
  "reading_count": 1440,
  "alert_count": 0
}
```

#### Calibrate Sensor
```http
POST /api/calibrate
Content-Type: application/json

{
  "sensor": "reference",
  "is_empty": true
}
```

#### Tare Sensor
```http
POST /api/tare
Content-Type: application/json

{
  "sensor": "reference"
}
```

#### Update Settings
```http
POST /api/settings
Content-Type: application/json

{
  "sample_interval": 60,
  "leak_threshold": 5.0,
  "slack": {
    "enabled": true,
    "bot_token": "xoxb-...",
    "channel": "#alerts"
  }
}
```

## Troubleshooting

### Common Issues

#### 1. "No I2C device at address: 0x48"

**Symptoms:** Log shows ADS1115 initialization failures
**Solutions:**
```bash
# Check I2C is enabled
sudo raspi-config
# Interface Options → I2C → Enable

# Verify wiring connections
i2cdetect -y 1

# Check ADS1115 power (3.3V)
# Verify SDA/SCL connections
```

#### 2. Sensors Reading 0% or Stuck Values

**Symptoms:** Sensor percentages show 0% or don't change
**Solutions:**
- Check eTape sensor wiring
- Verify 560Ω resistors in voltage divider
- Recalibrate sensors with known empty/full levels
- Check for loose connections

#### 3. Web Dashboard Not Accessible

**Symptoms:** Cannot connect to `http://pi-ip:5000`
**Solutions:**
```bash
# Check service status
sudo systemctl status water-monitor

# Check firewall
sudo ufw status

# Verify network connectivity
ping <pi-ip>

# Check logs
tail -f /opt/water-monitor/water_monitor.log
```

#### 4. Slack Notifications Not Working

**Symptoms:** Slack test fails or no alerts received
**Solutions:**
- Verify bot token starts with `xoxb-`
- Check bot permissions include `chat:write`
- Ensure bot is added to target channel
- Test with `/api/test-slack` endpoint

### Log Analysis

**View real-time logs:**
```bash
tail -f /opt/water-monitor/water_monitor.log
```

**Common log patterns:**
- `Sensor initialization failed`: Hardware connectivity issue
- `Slack API error: invalid_auth`: Check bot token
- `Leak alert sent`: Normal leak detection
- `Calibration saved`: Successful sensor calibration

### Performance Optimization

**For high-frequency monitoring:**
- Reduce `sample_interval` to 30 seconds minimum
- Monitor database size: `/opt/water-monitor/readings.db`
- Consider log rotation for `water_monitor.log`

**Database maintenance:**
```bash
# Access SQLite database
sqlite3 /opt/water-monitor/readings.db

# Check database size
.schema
SELECT COUNT(*) FROM readings;

# Manual cleanup (removes data older than 30 days)
# This is done automatically by the system
```

## Advanced Features

### Health Monitoring

The system includes comprehensive sensor health monitoring:

- **Voltage Stability**: Detects unstable readings
- **Calibration Drift**: Identifies long-term sensor drift
- **Stuck Readings**: Detects non-responsive sensors
- **Auto-Recovery**: Attempts automatic sensor recovery

### Remote Access

**Set up reverse SSH tunnel for remote access:**
```bash
# On Pi, create tunnel to remote server
ssh -R 8080:localhost:5000 user@remote-server

# Access via: http://remote-server:8080
```

**Configure dynamic DNS for direct access:**
```bash
# Install ddclient for dynamic DNS updates
sudo apt install ddclient
```

### Data Export

**Export readings to CSV:**
```bash
sqlite3 -header -csv /opt/water-monitor/readings.db \
  "SELECT * FROM readings WHERE timestamp > datetime('now', '-7 days');" \
  > export.csv
```

### Custom Integrations

**MQTT Integration Example:**
```python
# Add to water_monitor.py
import paho.mqtt.client as mqtt

def publish_reading(self, reading):
    client = mqtt.Client()
    client.connect("mqtt-broker", 1883, 60)
    client.publish("water/sensors/reference", reading['reference']['percentage'])
    client.publish("water/sensors/control", reading['control']['percentage'])
    client.disconnect()
```

### Security Considerations

**Basic Security Setup:**
```bash
# Change default passwords
sudo passwd pi

# Configure firewall
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 5000  # Water monitor dashboard

# Disable unused services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

**HTTPS Setup (Optional):**
Use reverse proxy with nginx and Let's Encrypt for HTTPS access.

### Backup and Recovery

**Automated backup script:**
```bash
#!/bin/bash
# /opt/water-monitor/backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backup/water-monitor-$DATE.tar.gz \
  /opt/water-monitor/config.json \
  /opt/water-monitor/readings.db \
  /opt/water-monitor/water_monitor.log
```

**Recovery procedure:**
1. Fresh Pi OS installation
2. Restore backup files
3. Reinstall dependencies
4. Restart services

---

## Support and Contributing

**Documentation:** This README covers comprehensive setup and usage
**Issues:** Check logs first, then review troubleshooting section
**Updates:** Keep system updated with `apt update && apt upgrade`

For technical support, check the log files and verify hardware connections before seeking assistance.
