# eTape Sensor Wiring Guide for Water Monitoring System

## Required Components

### Electronic Components
- Raspberry Pi 5 (or Pi 4/3B+)
- ADS1115 16-bit ADC module
- 2x eTape liquid level sensors (12" or 24" recommended)
- 2x 560Ω resistors (1/4 watt, 5% tolerance)
- Breadboard or perfboard
- Jumper wires (male-to-female and male-to-male)

### Tools
- Wire strippers
- Soldering iron and solder (for permanent connections)
- Multimeter (for testing)

## Step 1: ADS1115 to Raspberry Pi Wiring

Connect the ADS1115 ADC to your Raspberry Pi I2C pins:

| ADS1115 Pin | Raspberry Pi 5 Pin | Function | Wire Color (suggested) |
|-------------|-------------------|----------|----------------------|
| VDD         | Pin 1 (3.3V)      | Power    | Red                  |
| GND         | Pin 6 (GND)       | Ground   | Black                |
| SCL         | Pin 5 (SCL)       | I2C Clock| Yellow               |
| SDA         | Pin 3 (SDA)       | I2C Data | Blue                 |

**⚠️ Important:** Do NOT connect VDD to 5V - the ADS1115 operates at 3.3V.

## Step 2: eTape Sensor Voltage Divider Circuits

Each eTape sensor requires a voltage divider circuit. The eTape sensors are variable resistors that change resistance based on water level.

### Circuit for Each Sensor:
```
3.3V ──┬── 560Ω Resistor ──┬── eTape Sensor ── GND
       │                   │
       │                   └── To ADS1115 Analog Input
       │
    Power Rail          Signal Wire
```

## Step 3: Reference Sensor Wiring (Channel A0)

### Breadboard Connections:
1. Connect 3.3V from Pi to positive power rail on breadboard
2. Connect GND from Pi to ground rail on breadboard
3. Place 560Ω resistor between 3.3V rail and a junction point
4. Connect one eTape sensor terminal to the junction point (after the resistor)
5. Connect other eTape sensor terminal to ground rail
6. Connect ADS1115 A0 pin to the junction point between resistor and eTape sensor

### Wire Details:
- **Red wire:** 3.3V to breadboard positive rail
- **Black wire:** GND to breadboard ground rail  
- **Green wire:** Junction point to ADS1115 A0
- **560Ω resistor:** Between 3.3V and junction
- **eTape sensor:** One terminal to junction, other to ground

## Step 4: Control Sensor Wiring (Channel A1)

Repeat the same voltage divider circuit for the second sensor:

1. Use another 560Ω resistor between 3.3V rail and a second junction point
2. Connect second eTape sensor: one terminal to junction, other to ground
3. Connect ADS1115 A1 pin to this second junction point

### Wire Details:
- **Orange wire:** Second junction point to ADS1115 A1
- **560Ω resistor:** Between 3.3V and second junction
- **eTape sensor:** One terminal to junction, other to ground

## Step 5: Complete Wiring Diagram (Terminal Block Method)

```
Raspberry Pi 5              ADS1115              Terminal Blocks & eTape Sensors
                                                      
Pin 1 (3.3V) ────────────── VDD                    
Pin 3 (SDA)  ────────────── SDA                    
Pin 5 (SCL)  ────────────── SCL                    
Pin 6 (GND)  ────────────── GND                    
                            
              3.3V ─── [Terminal Block] ─┬─ 560Ω ─┬─ Reference eTape ─┐
                                         │        │                   │
              GND  ─── [Terminal Block] ─┼────────┼───────────────────┼─ GND
                                         │        └─ A0               │
                                         │                            │
                                         └─ 560Ω ─┬─ Control eTape ───┘
                                                   │                    
                                                   └─ A1               
```

### Alternative: Direct Solder Connections
```
Raspberry Pi 5              ADS1115              Direct Connections
                                                      
Pin 1 (3.3V) ────────────── VDD                    
Pin 3 (SDA)  ────────────── SDA                    
Pin 5 (SCL)  ────────────── SCL                    
Pin 6 (GND)  ────────────── GND                    
                            
              3.3V ─ Wire Nuts ─┬─ 560Ω ─┬─ Reference eTape ── GND
                                │        └─ A0
                                │        
                                └─ 560Ω ─┬─ Control eTape ── GND
                                         └─ A1
```

## Step 6: Physical Sensor Installation

### Reference Sensor (Main Container):
- Install in your primary water container/tank
- Thread into 1/2" NPT fitting with thread sealant
- Ensure sensor extends into water area you want to monitor
- Route wire to electronics enclosure

### Control Sensor (Sealed Container):
- Install in a separate, sealed reference container
- This container should have the same water source initially
- Keep sealed to detect when main container loses water
- Route wire to electronics enclosure

## Step 7: Testing and Verification

### Before Powering On:
1. **Double-check all connections** with multimeter
2. **Verify voltage levels:** 3.3V between VDD and GND
3. **Check I2C connections:** SCL and SDA properly connected
4. **Confirm no shorts:** No unwanted connections between power and ground

### After Powering On:
1. **Test I2C detection:**
   ```bash
   i2cdetect -y 1
   ```
   Should show device at address 0x48

2. **Check sensor readings:** Both sensors should provide reasonable voltage readings (typically 1-3V depending on water level)

## Step 8: Software Configuration

### Update config.json for PN-12110215TC-5 sensors:
```json
{
  "reference_sensor": {
    "calibration_empty": 51500,
    "calibration_full": 24000
  },
  "control_sensor": {
    "calibration_empty": 51500, 
    "calibration_full": 24000
  }
}
```

**Why these values for 5-inch sensors:**
- **Empty sensor** (~1150Ω + 1.8kΩ voltage divider): ~1.29V → ~51,500 ADC reading
- **Full sensor** (~400Ω + 1.8kΩ voltage divider): ~0.6V → ~24,000 ADC reading
- **16-bit ADC**: 0-65535 range (higher numbers = higher voltage)

### Initial calibration process:
1. Start the system: `sudo systemctl start water-monitor`
2. Access web dashboard: `http://<pi-ip>:5000`
3. **Empty calibration**: With sensors in air/empty containers, click "Calibrate Empty"
4. **Full calibration**: Submerge sensors to known level, click "Calibrate Full"

### Expected voltage behavior:
- **Empty sensor** (~1150Ω): ~1.3V reading
- **Full sensor** (~400Ω): ~0.6V reading  
- **Voltage range**: Approximately 0.6V to 1.3V depending on water level

## Troubleshooting Common Issues

### "No I2C device at address 0x48":
- Check VDD connected to 3.3V (not 5V)
- Verify SCL/SDA connections
- Ensure I2C is enabled: `sudo raspi-config`

### Sensors reading 0% or stuck values:
- Check 560Ω resistor placement
- Verify eTape sensor connections not reversed
- Test sensor resistance with multimeter (should vary with water level)

### Unstable readings:
- Ensure good connections (consider soldering)
- Check for electromagnetic interference
- Verify adequate power supply to Pi

## Safety Considerations

- **Electrical safety:** Keep all electronics in waterproof enclosure
- **Water compatibility:** Ensure eTape sensors are suitable for your water type
- **Power isolation:** Use proper 3.3V levels only
- **Grounding:** Maintain proper ground connections throughout

## eTape Sensor Specifications

- **Operating Voltage:** 5V DC (but we use 3.3V with voltage divider)
- **Output:** Variable resistance (increases with fluid level)
- **Accuracy:** ±12mm (0.5")
- **Temperature Range:** -40°C to +125°C
- **Thread:** 1/2" NPT

## Final Notes

This wiring setup will give you a reliable dual-sensor water monitoring system capable of detecting leaks by comparing water levels between your main container and a sealed reference container. The system works by detecting differences between the two sensors - if water is lost from the main container but not the sealed reference, it indicates a leak.

Take your time with the wiring and double-check all connections before powering on. A systematic approach will save time troubleshooting later.
