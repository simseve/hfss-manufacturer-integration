# Paraglider Traffic Emulator

A sophisticated GPS tracking emulator that simulates realistic paraglider flight patterns, including takeoffs, thermals, flights, and landings.

## Overview

The paraglider emulator creates virtual devices that transmit GPS coordinates via MQTT to simulate real paraglider tracking devices. It includes realistic flight physics, multiple flight phases, and various flying sites.

## Features

- **Realistic Flight Simulation**: Simulates ground preparation, takeoff, thermal soaring, gliding, and landing phases
- **Multiple Flying Sites**: Pre-configured with 5 popular paragliding locations (Chamonix, Interlaken, Annecy, Zermatt, Dolomites)
- **MQTT Integration**: Connects to MQTT broker with TLS encryption
- **Device Lifecycle**: Handles device registration, authentication, and continuous GPS transmission
- **Configurable Parameters**: Number of devices, simulation duration, and target domain

## Installation

1. Ensure you have Python 3.7+ installed
2. Install required dependencies:
   ```bash
   pip install paho-mqtt requests python-dotenv
   ```

## Usage

### Basic Usage (Production Endpoints)

```bash
cd manufacturer
python3 scripts/paraglider_emulator.py --devices 10 --duration 60
```

This will:
- Automatically download the CA certificate from production
- Register 10 virtual paraglider devices
- Run the simulation for 60 minutes
- Connect to production MQTT broker at `dg-mqtt.hikeandfly.app`

### Command Line Options

```bash
python3 scripts/paraglider_emulator.py [OPTIONS]

Options:
  --devices DEVICES     Number of paraglider devices to simulate (default: 10)
  --duration DURATION   Simulation duration in minutes (default: 60, max: 1440)
  --domain DOMAIN       Domain for API and MQTT connections (default: dg-dev.hikeandfly.app)
```

### Examples

1. **Quick Test** - Run 1 device for 5 minutes:
   ```bash
   python3 scripts/paraglider_emulator.py --devices 1 --duration 5
   ```

2. **Load Test** - Run 50 devices for 2 hours:
   ```bash
   python3 scripts/paraglider_emulator.py --devices 50 --duration 120
   ```

3. **Custom Domain** - Use a different server:
   ```bash
   python3 scripts/paraglider_emulator.py --devices 5 --domain custom.domain.com
   ```

## CA Certificate

The emulator requires a CA certificate for secure MQTT connections. It will automatically:
1. Check if `./manufacturer/ca.crt` exists
2. If not, download it from `https://{domain}/ca.crt`
3. Save it for future use

To manually download the certificate:
```bash
curl -o manufacturer/ca.crt https://dg-dev.hikeandfly.app/ca.crt
```

## Flight Phases

The emulator simulates realistic paraglider behavior through these phases:

1. **Ground Phase** (10-30 min)
   - Device at landing zone
   - Pilot preparation and equipment checks
   - Occasional small movements

2. **Takeoff Phase** (2-5 min)
   - Movement to takeoff area
   - Altitude gain during launch
   - Transition to flight

3. **Thermal Soaring** (20-120 min)
   - Circular patterns in thermals
   - Altitude gains up to 3000m
   - Realistic thermal behavior

4. **Gliding Phase** (10-60 min)
   - Cross-country flight
   - Gradual altitude loss
   - Speed variations

5. **Landing Phase** (2-5 min)
   - Landing pattern approach
   - Controlled descent
   - Ground contact

## Output

The emulator provides:
- Real-time statistics every 10 seconds
- Device registration confirmation
- MQTT connection status
- GPS points transmission rate
- Active flights by phase
- Final simulation results saved to `paraglider_simulation_results.json`

## Troubleshooting

### Certificate Issues
- Ensure you have internet access to download the CA certificate
- Check if the certificate URL is accessible: `curl https://dg-dev.hikeandfly.app/ca.crt`
- Verify certificate permissions: `ls -la manufacturer/ca.crt`

### Connection Issues
- Verify MQTT port 8883 is not blocked by firewall
- Check domain resolution: `nslookup dg-mqtt.hikeandfly.app`
- Test MQTT connection: `openssl s_client -connect dg-mqtt.hikeandfly.app:8883 -CAfile manufacturer/ca.crt`

### Registration Failures
- Verify the manufacturer secret in environment variables
- Check API endpoint accessibility
- Review device registration response in logs

## Environment Variables

Optional environment variables (defaults are usually fine):
- `MQTT_USER`: MQTT username (default: mqtt_user)
- `MQTT_PASSWORD`: MQTT password (default: mqtt_secure_password)
- `MANUFACTURER_SECRET_DIGIFLY`: Manufacturer secret for device registration

## Log Files

The emulator creates:
- `paraglider_emulator.log`: Detailed debug information
- `paraglider_simulation_results.json`: Final statistics and results

## Security Notes

- All MQTT connections use TLS encryption
- Device credentials are generated securely
- HMAC signatures protect message integrity
- Certificates are verified (hostname check disabled for flexibility)