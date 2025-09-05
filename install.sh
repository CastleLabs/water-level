 
#!/bin/bash

# Water Monitor Installation Script - ADS1115 I2C Version
# DANGEROUS: This version forces a system-wide pip install.
# UPDATED for 'tech' user.

set -e

echo "================================================"
echo "    Water Level Monitor Installation Script    "
echo "    (System-Wide Install / 'tech' user)        "
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

# Install Python packages system-wide, bypassing the safety check
echo "[4/8] Installing Python packages system-wide..."
pip3 install --break-system-packages flask adafruit-circuitpython-ads1x15 adafruit-blinka

# Create application directory
echo "[5/8] Setting up application directory..."
APP_DIR="/opt/water-monitor"
mkdir -p $APP_DIR
mkdir -p $APP_DIR/templates
mkdir -p $APP_DIR/static

# Copy files to application directory
echo "[6/8] Copying application files..."
cp *.py $APP_DIR/ 2>/dev/null || echo "Python files not found in current directory"
cp config.json $APP_DIR/ 2>/dev/null || echo "config.json not found"
if [ -d "templates" ]; then
    cp templates/*.html $APP_DIR/templates/ 2>/dev/null || echo "Template files not found"
fi
if [ -d "static" ]; then
    cp static/*.* $APP_DIR/static/ 2>/dev/null || echo "Static files not found"
fi

# **MODIFIED**: Set permissions for the 'tech' user
chown -R tech:tech $APP_DIR
chmod +x $APP_DIR/main.py

# **MODIFIED**: Create systemd service to run as 'tech' user
echo "[7/8] Creating systemd service..."
cat > /etc/systemd/system/water-monitor.service <<EOF
[Unit]
Description=Water Level Monitoring System (ADS1115 I2C)
After=network.target

[Service]
Type=simple
User=tech
WorkingDirectory=/opt/water-monitor
ExecStart=/usr/bin/python3 /opt/water-monitor/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable service
echo "[8/8] Enabling service..."
systemctl daemon-reload
systemctl enable water-monitor.service

echo ""
echo "================================================"
echo "          Installation Complete!                "
echo "================================================"
echo ""
echo "Script updated for user 'tech'."
echo "Proceed with connecting hardware and starting the service:"
echo "sudo systemctl start water-monitor"
echo ""

