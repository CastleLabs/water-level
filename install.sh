#!/bin/bash

# Water Monitor Installation Script - ADS1115 I2C Version
# Run with: sudo bash install.sh

set -e

echo "================================================"
echo "    Water Level Monitor Installation Script    "
echo "    ADS1115 I2C Version                        "
echo "================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

# Update system
echo "[1/8] Updating system packages..."
apt-get update
apt-get upgrade -y

# Install system dependencies
echo "[2/8] Installing system dependencies..."
apt-get install -y python3-pip python3-dev
apt-get install -y git build-essential
apt-get install -y i2c-tools python3-smbus

# Enable I2C interface (required for ADS1115)
echo "[3/8] Enabling I2C interface..."
raspi-config nonint do_i2c 0
echo "I2C enabled"

# Install Python packages system-wide
echo "[4/8] Installing Python packages..."
pip3 install flask
pip3 install adafruit-circuitpython-ads1x15
pip3 install adafruit-blinka

# Create application directory
echo "[5/8] Setting up application directory..."
APP_DIR="/opt/water-monitor"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/templates
mkdir -p $APP_DIR/static

# Copy files to application directory (assuming proper file structure)
echo "[6/8] Copying application files..."
cp *.py $APP_DIR/ 2>/dev/null || echo "Python files not found in current directory"
cp config.json $APP_DIR/ 2>/dev/null || echo "config.json not found"

# Copy templates if they exist
if [ -d "templates" ]; then
    cp templates/*.html $APP_DIR/templates/ 2>/dev/null || echo "Template files not found"
fi

# Copy static files if they exist
if [ -d "static" ]; then
    cp static/*.css $APP_DIR/static/ 2>/dev/null || echo "CSS files not found"
    cp static/*.js $APP_DIR/static/ 2>/dev/null || echo "JS files not found"
fi

# Set permissions
chown -R pi:pi $APP_DIR
chmod +x $APP_DIR/main.py

# Create systemd service
echo "[7/8] Creating systemd service..."
cat > /etc/systemd/system/water-monitor.service <<EOF
[Unit]
Description=Water Level Monitoring System (ADS1115 I2C)
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/opt/water-monitor
ExecStart=/usr/bin/python3 /opt/water-monitor/main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/water-monitor/water_monitor.log
StandardError=append:/opt/water-monitor/water_monitor.log

[Install]
WantedBy=multi-user.target
EOF

# Enable service (but don't start yet)
echo "[8/8] Enabling service..."
systemctl daemon-reload
systemctl enable water-monitor.service

# Test I2C functionality
echo ""
echo "Testing I2C setup..."
if command -v i2cdetect &> /dev/null; then
    echo "I2C tools installed successfully"
    echo "After connecting your ADS1115, run: sudo i2cdetect -y 1"
    echo "You should see device at address 48 (0x48)"
else
    echo "Warning: i2cdetect not available"
fi

echo ""
echo "================================================"
echo "          Installation Complete!                "
echo "================================================"
echo ""
echo "Hardware Setup Instructions:"
echo "1. Connect your ADS1115 ADC to Raspberry Pi I2C pins:"
echo "   ADS1115 VDD  -> Pi Pin 1  (3.3V)"
echo "   ADS1115 GND  -> Pi Pin 6  (GND)"
echo "   ADS1115 SCL  -> Pi Pin 5  (GPIO3/SCL)"
echo "   ADS1115 SDA  -> Pi Pin 3  (GPIO2/SDA)"
echo "   ADS1115 ADDR -> Pi Pin 6  (GND) [for address 0x48]"
echo ""
echo "2. Connect your eTape sensors to ADS1115:"
echo "   Reference Sensor (main container):"
echo "     Red wire   -> 3.3V"
echo "     Black wire -> GND"
echo "     White wire -> [10kΩ resistor to GND] + ADS1115 A0"
echo ""
echo "   Control Sensor (sealed container):"
echo "     Red wire   -> 3.3V"
echo "     Black wire -> GND"
echo "     White wire -> [10kΩ resistor to GND] + ADS1115 A1"
echo ""
echo "Software Setup:"
echo "3. Test I2C connection: sudo i2cdetect -y 1"
echo "4. Start the service: sudo systemctl start water-monitor"
echo "5. Access dashboard: http://$(hostname -I | cut -d' ' -f1):5000"
echo "6. Calibrate your sensors using the web interface"
echo ""
echo "Useful commands:"
echo "  Start service:   sudo systemctl start water-monitor"
echo "  Stop service:    sudo systemctl stop water-monitor"
echo "  View logs:       sudo journalctl -u water-monitor -f"
echo "  Service status:  sudo systemctl status water-monitor"
echo "  Test I2C:        sudo i2cdetect -y 1"
echo ""
echo "Troubleshooting:"
echo "  If no I2C device found, check wiring and ensure I2C is enabled"
echo "  If permission errors, ensure files are owned by pi user"
echo "  If import errors, ensure adafruit libraries are installed"
echo ""