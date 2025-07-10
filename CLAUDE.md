# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **GPS tracking device emulator** for simulating paraglider flight patterns. It's designed for testing GPS tracking platforms, helping manufacturers integrate with GPS tracking servers, and load testing with realistic flight physics.

Key features:
- Simulates up to 500 concurrent devices
- MQTT over TLS with HMAC message signing
- Realistic flight physics (thermals, gliding, landing)
- Multi-manufacturer support with secure credential management

## Common Development Commands

### Initial Setup
```bash
# Run setup script - creates virtual environment with Python 3.12, installs deps, generates certs
python setup.py
```

This will:
1. Create a virtual environment using Python 3.12 (if available)
2. Install all dependencies in the virtual environment
3. Generate test certificates
4. Create `.env` from template
5. Create `run_emulator.sh` wrapper script

### Running the Emulator

**Always use the virtual environment!** The setup script creates wrapper scripts for this:

```bash
# Basic usage (10 devices, 60 minutes)
./run_emulator.sh

# Custom configuration
./run_emulator.sh --devices 50 --duration 120 --domain your-server.com

# Safe production run (recommended) - also uses virtual environment
./run_safe.sh --devices 100 --duration 60
```

**Alternative: Manual virtual environment activation**
```bash
# Activate virtual environment first
source venv/bin/activate

# Then run normally
python paraglider_emulator.py --devices 50
```

### Configuration
```bash
# Configure manufacturer credentials
python paraglider_emulator.py --config --manufacturer YOUR_MANUFACTURER_NAME

# Generate test certificates
python generate_certs.py
```

### Testing a Single Device
```bash
python paraglider_emulator.py --devices 1 --duration 5
```

## Architecture Overview

### Core Components
1. **ParagliderSimulator** - Main orchestrator managing the simulation
2. **Paraglider** - Individual device with flight state
3. **FlightPhase** enum - GROUND, TAKEOFF, CLIMBING, GLIDING, THERMALING, LANDING, LANDED
4. **RateLimiter** - API call rate limiting

### Key Design Patterns
- **Safety-first**: Single instance lock, graceful shutdown, resource limits
- **Physics simulation**: Realistic flight dynamics with thermals and wind
- **Connection pooling**: Efficient MQTT handling for large simulations
- **Threading**: ThreadPoolExecutor for parallel operations

### Security Model
- TLS encryption for all MQTT traffic
- HMAC-SHA256 message signing
- Secure credential storage (file permissions 600)
- API key authentication

### Message Flow
1. Device registration via REST API → receives API key
2. GPS data + HMAC signature → JSON message
3. Publish to MQTT topic: `gps/{device_id}/data`

## Important Files

- `paraglider_emulator.py` - Main application
- `config_manager.py` - Manufacturer credential management
- `run_safe.sh` - Production wrapper with safety checks
- `.env` - Configuration (create from `.env.example`)
- `MANUFACTURER_GUIDE.md` - Hardware integration guide

## Development Notes

### Dependencies
- Python 3.7+ required (Python 3.12 preferred)
- Virtual environment automatically created by setup.py
- Minimal deps: paho-mqtt, requests, python-dotenv

### Safety Features
- Max 500 devices (override with --force)
- Max 1440 minutes duration
- Process locking prevents multiple instances
- Rate limiting protects backend APIs

### Testing Considerations
- No formal test suite - emulator itself is the testing tool
- Use small device counts for development (5-10 devices)
- Monitor logs in `logs/` directory when using run_safe.sh

### Common Tasks

**Check if running:**
```bash
pgrep -f "paraglider_emulator.py"
```

**Emergency stop:**
```bash
pkill -f paraglider_emulator.py
rm -f /tmp/paraglider_emulator.lock  # if stuck
```

**Large simulations:**
```bash
ulimit -n 4096  # Increase file descriptors
./run_safe.sh --devices 500 --duration 60
```

## Integration Points

- **MQTT Broker**: Port 8883 (TLS)
- **API Endpoint**: `https://{domain}/api/devices/register`
- **Topics**: `gps/{device_id}/data`
- **Message format**: JSON with data, signature, api_key fields

Remember: This emulator simulates realistic paraglider GPS tracking. Always use manufacturer credentials securely and respect rate limits when testing against production systems.