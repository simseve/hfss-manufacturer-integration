# Paraglider Traffic Emulator

A realistic GPS tracking simulator for paraglider devices that generates authentic flight patterns including takeoffs, thermals, gliding, and landings.

## Features

- **Realistic Flight Physics**: Simulates actual paraglider behavior including thermal climbing, gliding ratios, and landing approaches
- **Multiple Flying Sites**: Pre-configured with 5 popular paragliding locations (Chamonix, Interlaken, Annecy, Zermatt, Dolomites)
- **Device Lifecycle**: Full device registration, GPS tracking, and battery management
- **High Performance**: Supports thousands of concurrent devices with connection pooling
- **Secure Communication**: MQTT over TLS with HMAC message signing
- **Safety Features**: Single instance lock, rate limiting, and resource protection
- **Multi-Manufacturer Support**: Configurable for any manufacturer with secure credential management

## Quick Start

### 1. Prerequisites

- Python 3.7 or higher
- OpenSSL (for certificate generation)
- Network access to your GPS tracking server

### 2. Installation

```bash
# Clone or download this package
cd paraglider_emulator

# Run the setup script
python setup.py

# The setup will:
# - Install Python dependencies
# - Generate test certificates (if needed)
# - Create a .env configuration file
```

### 3. Configuration

Configure your manufacturer credentials:

```bash
# Option 1: Interactive configuration (recommended)
python paraglider_emulator.py --config --manufacturer YOUR_MANUFACTURER_NAME

# Option 2: Environment variables
export MANUFACTURER_SECRET_YOUR_NAME="your_secret_key"

# Option 3: Edit .env file
cp .env.example .env
# Then edit .env with your settings
```

### 4. Running the Emulator

```bash
# Basic usage - 10 devices for 60 minutes
python paraglider_emulator.py

# Simulate 50 devices
python paraglider_emulator.py --devices 50

# Run for 2 hours
python paraglider_emulator.py --duration 120

# Use specific server
python paraglider_emulator.py --domain production-server.com

# Combined options
python paraglider_emulator.py --devices 100 --duration 30 --domain test-server.com
```

## Command Line Options

- `--devices N`: Number of paraglider devices to simulate (default: 10, max: 500)
- `--duration M`: Simulation duration in minutes (default: 60, max: 1440)
- `--domain HOST`: Server domain/hostname (overrides .env setting)
- `--manufacturer NAME`: Manufacturer name (default: DIGIFLY)
- `--config`: Configure manufacturer credentials interactively
- `--unsafe`: Disable safety features (1-second updates, no rate limiting)
- `--force`: Override device count limits (use with caution)
- `--help`: Show help message

## Safety Features

The emulator includes built-in safety mechanisms to prevent accidental system overload:

### 1. Single Instance Lock
- Only one emulator can run at a time
- Lock file at `/tmp/paraglider_emulator.lock`
- Shows PID and details of running instance

### 2. Rate Limiting
- API calls limited to 10 requests/second (configurable)
- Prevents overwhelming the registration endpoint
- Automatic throttling with wait times

### 3. Device Limits
- Maximum 500 devices per instance (default)
- Override with `--force` flag if needed
- Prevents accidental resource exhaustion

### 4. Safe Update Intervals
- Default: 5-second GPS updates (safe mode)
- Unsafe mode: 1-second updates (use `--unsafe`)
- Reduces server load significantly

### 5. Resource Protection
- Connection pooling for >50 devices
- Graceful shutdown on SIGINT/SIGTERM
- Automatic cleanup on exit

## Certificate Management

### Using Test Certificates (Default)

The emulator includes a certificate generator for testing:

```bash
# Generate new test certificates
python generate_certs.py
```

⚠️ **Warning**: These are self-signed certificates for TESTING ONLY.

### Using Production Certificates

For production environments, place your certificates in the `certs/` directory:

- `certs/ca.crt` - Certificate Authority certificate
- `certs/client.crt` - Client certificate
- `certs/client.key` - Client private key

## Flight Simulation Details

### Flight Phases

1. **Ground**: Devices start at launch sites, occasional ground movements
2. **Takeoff**: Acceleration and initial climb
3. **Climbing**: Searching for thermals
4. **Thermaling**: Circling in rising air to gain altitude
5. **Gliding**: Cross-country flight between thermals
6. **Landing**: Final approach and touchdown
7. **Landed**: Post-flight ground activities

### Realistic Behaviors

- **Thermal Detection**: Devices search for and circle in thermals
- **Variable Conditions**: Different climb rates, sink rates, and wind effects
- **Battery Management**: Realistic power consumption
- **Dynamic Movement**: Speed and heading changes based on flight phase

## Performance Considerations

### Small Simulations (< 50 devices)
- Each device maintains its own MQTT connection
- Minimal system requirements

### Large Simulations (> 50 devices)
- Automatic connection pooling to prevent resource exhaustion
- Batch registration with retry logic
- Optimized for high throughput

### Very Large Simulations (> 500 devices)
- Shared MQTT connection pool
- Staggered device startup
- Recommended: Increase system file descriptor limits

## Monitoring

During simulation, statistics are displayed every 10 seconds:

```
📊 Paraglider Traffic Simulation Statistics
==================================================
Elapsed Time: 120s
Registered Devices: 100/100
Total GPS Points Sent: 12,000
Average Rate: 100.0 points/sec
Current Throughput: 98.5 msgs/sec

🪂 Active Flights by Phase:
  Ground: 15
  Climbing: 25
  Gliding: 30
  Thermaling: 20
  Landing: 10
  Total Active: 100
```

## Troubleshooting

### Connection Issues

1. **MQTT Connection Failed**
   - Verify MQTT broker is running on port 8883
   - Check certificates are valid
   - Confirm MQTT credentials in .env

2. **API Registration Failed**
   - Ensure API server is accessible
   - Verify MANUFACTURER_SECRET is correct
   - Check network connectivity

### Certificate Issues

1. **OpenSSL Not Found**
   ```bash
   # macOS
   brew install openssl
   
   # Ubuntu/Debian
   apt-get install openssl
   
   # CentOS/RHEL
   yum install openssl
   ```

2. **Certificate Verification Failed**
   - Regenerate certificates: `python generate_certs.py`
   - Ensure server uses matching CA certificate

### Performance Issues

1. **"Too many open files" Error**
   ```bash
   # Increase file descriptor limit
   ulimit -n 4096
   ```

2. **High CPU Usage**
   - Reduce number of devices
   - Increase update interval in code

## Output Files

The emulator creates:

- `paraglider_simulation_results.json`: Summary of simulation results
- `certs/`: Generated certificates (if using test certificates)
- `.env`: Your configuration (created from .env.example)

## Security Notes

- Never commit `.env` or certificates to version control
- Use proper CA-signed certificates in production
- Keep MANUFACTURER_SECRET secure
- Rotate MQTT credentials regularly

## Support

For issues or questions about the emulator, please contact Digi Fly support.

## License

Proprietary - Digi Fly# paraglider-emulator
