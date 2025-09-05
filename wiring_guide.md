# Water Monitor Hardware Wiring Guide - ADS1115 Version

## Required Components

### Main Components
- 1x Raspberry Pi 5 (or compatible model with I2C)
- 1x ADS1115 16-bit ADC Module
- 2x eTape Liquid Level Sensors (5 inch)
- Jumper wires
- 2x 10kΩ resistors (for voltage divider)

### Optional Components
- Terminal blocks for secure connections
- Project box/enclosure
- Power supply for Raspberry Pi

## ADS1115 Module Pinout

```
    ADS1115 Module (Common Breakout Board)
    
    VDD -------- Power (3.3V or 5V)
    GND -------- Ground
    SCL -------- I2C Clock
    SDA -------- I2C Data
    ADDR ------- Address Select (to GND for 0x48)
    ALRT ------- Alert/Ready (not used)
    A0 --------- Analog Input 0
    A1 --------- Analog Input 1
    A2 --------- Analog Input 2
    A3 --------- Analog Input 3
```

## Raspberry Pi to ADS1115 Connections

### I2C Connections (Much Simpler than SPI!)
| ADS1115 Pin | RPi Physical Pin | RPi GPIO | Description |
|-------------|------------------|----------|-------------|
| VDD | Pin 1 | 3.3V | Power |
| GND | Pin 6 | GND | Ground |
| SCL | Pin 5 | GPIO3/SCL | I2C Clock |
| SDA | Pin 3 | GPIO2/SDA | I2C Data |
| ADDR | Pin 6 | GND | Address = 0x48 |

## eTape Sensor Connections

### Sensor 1 - Reference (Main Container)
```
eTape Sensor 1:
    Red Wire (Vin) --------> 3.3V
    White Wire (Vout) -----> [10kΩ to GND] + ADS1115 A0
    Black Wire (GND) ------> GND
    Blue Wire (Substrate) -> Not connected
```

### Sensor 2 - Control (Sealed Container)
```
eTape Sensor 2:
    Red Wire (Vin) --------> 3.3V
    White Wire (Vout) -----> [10kΩ to GND] + ADS1115 A1
    Black Wire (GND) ------> GND
    Blue Wire (Substrate) -> Not connected
```

## Complete Wiring Diagram

```
Raspberry Pi 5                     ADS1115                    eTape Sensors
--------------                     -------                    -------------
                                                              
3.3V (Pin 1) ---------+----------> VDD                       Reference Sensor
                      |                                       Red ------------> 3.3V
                      |                                       White ----+-----> A0
                      |                                                 |
                      |                                              [10kΩ]
                      |                                                 |
GND (Pin 6) ----------+----------> GND <-----------------------+------+
                      |            ADDR                         |
                      |                                       Black
                      |                                       
GPIO3/SCL (Pin 5) ---------------> SCL                       Control Sensor
GPIO2/SDA (Pin 3) ---------------> SDA                       Red ------------> 3.3V
                                                             White ----+-----> A1
                                                                      |
                                                                   [10kΩ]
                                                                      |
                                                                     GND
```

## Voltage Divider Circuit

Each eTape sensor needs a pull-down resistor:

```
eTape Output (White) ----+-----> To ADS1115 Input (A0 or A1)
                         |
                      [10kΩ]
                         |
                        GND
```

The 10kΩ resistor creates a voltage divider with the variable resistance of the eTape sensor.

## Step-by-Step Assembly

### 1. Enable I2C on Raspberry Pi
```bash
sudo raspi-config
# Navigate to: Interface Options -> I2C -> Enable
# Or run:
sudo raspi-config nonint do_i2c 0
```

### 2. Connect ADS1115 to Raspberry Pi
- Connect VDD to 3.3V (Pin 1)
- Connect GND to Ground (Pin 6)
- Connect SCL to GPIO3/SCL (Pin 5)
- Connect SDA to GPIO2/SDA (Pin 3)
- Connect ADDR to GND for address 0x48

### 3. Connect eTape Sensors
- Wire each sensor's red wire to 3.3V
- Wire each sensor's black wire to GND
- Connect white wire from Sensor 1 to A0 with 10kΩ pull-down
- Connect white wire from Sensor 2 to A1 with 10kΩ pull-down
- Leave blue wires unconnected

### 4. Testing I2C Connection
```bash
# Install i2c tools if not already installed
sudo apt-get install -y i2c-tools

# Scan for I2C devices (should show 48)
sudo i2cdetect -y 1

# Expected output:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- --
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --
# 50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
# 70: -- -- -- -- -- -- -- --
```

## Testing the Sensors

Create a simple test script:

```python
#!/usr/bin/env python3
import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Create the ADC object
ads = ADS.ADS1115(i2c)

# Create analog inputs
chan0 = AnalogIn(ads, ADS.P0)  # Reference sensor
chan1 = AnalogIn(ads, ADS.P1)  # Control sensor

while True:
    print(f"Reference: {chan0.value:5} ({chan0.voltage:.3f}V)")
    print(f"Control:   {chan1.value:5} ({chan1.voltage:.3f}V)")
    print("-" * 40)
    time.sleep(1)
```

## ADS1115 Advantages

### Higher Resolution
- **16-bit resolution** (65,536 values) vs 10-bit (1,024 values)
- Much more precise water level measurements
- Better for detecting small changes

### Simpler Wiring
- Only 4 wires to connect (vs 7 for MCP3008)
- I2C bus can support multiple devices
- Built-in pull-up resistors on module

### Better Features
- Programmable gain amplifier (PGA)
- Internal voltage reference
- Continuous or single-shot conversion modes
- Alert/ready pin for interrupt-driven reading

## I2C Address Configuration

The ADDR pin sets the I2C address:
- ADDR to GND: 0x48 (default)
- ADDR to VDD: 0x49
- ADDR to SDA: 0x4A
- ADDR to SCL: 0x4B

This allows up to 4 ADS1115 modules on the same I2C bus.

## Troubleshooting

### No I2C Device Found
- Check wiring connections
- Ensure I2C is enabled: `ls /dev/i2c*`
- Try slower I2C speed in `/boot/config.txt`:
  ```
  dtparam=i2c_arm=on
  dtparam=i2c_arm_baudrate=10000
  ```

### Erratic Readings
- Check pull-down resistors are properly connected
- Ensure solid ground connections
- Add 0.1µF capacitor between VDD and GND
- Keep sensor wires away from power lines

### All Readings Zero
- Verify 3.3V power to sensors
- Check resistor values (should be 10kΩ)
- Test with multimeter at sensor output

### Readings Don't Change
- Check sensor is properly submerged
- Verify sensor orientation (vertical)
- Clean sensor surface if dirty

## Safety Considerations

- The ADS1115 can handle 5V but sensors work fine at 3.3V
- Keep all electronics away from water
- Use proper enclosure for humid environments
- Secure all connections to prevent shorts

## Next Steps

After wiring is complete:
1. Test I2C connection with `i2cdetect`
2. Run the test script above
3. Install the monitoring software
4. Calibrate sensors via web interface
5. Begin monitoring!

## Notes on Your Specific Module

The module you linked includes:
- Pre-soldered headers (easier to use)
- Built-in pull-up resistors on I2C lines
- Address selection jumpers
- Power LED indicator
- Compact form factor

This makes it perfect for your project - just connect with jumper wires, no soldering required!