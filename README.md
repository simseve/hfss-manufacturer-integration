# HFSS DIGI - Manufacturer Integration

Welcome! This guide helps you integrate your GPS tracking devices with the HFSS DIGI platform.

## 🔑 Before You Start - Request Your Manufacturer Secret

**IMPORTANT**: You need a manufacturer secret to integrate your devices. This secret is unique to your company and allows you to register devices on our platform.

### How to Request Your Secret:
1. **Contact HFSS Sales Team**: Email sales@hikeandfly.app with:
   - Your company name
   - Expected number of devices
   - Your technical contact information
2. **Receive Your Credentials**: You'll get:
   - `MANUFACTURER_SECRET`: Your unique 32-character secret key
   - `MANUFACTURER_ID`: Your company identifier (e.g., "DIGIFLY")
   - API endpoints for production
3. **Keep it Secure**: Store your secret safely - it's used to authenticate all your devices

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.7 or higher
- Your manufacturer secret (see above)
- Network access to dg-dev.hikeandfly.app

### Clone the Repository
```bash
git clone https://github.com/hfss/manufacturer-integration.git
cd manufacturer-integration
```

### 1. Set Your Credentials

```bash
# Option 1: Set environment variable
export MANUFACTURER_SECRET="your_32_character_secret_here"

# Option 2: Create .env file (recommended)
cp .env.example .env
# Edit .env and add your secret
```

### 2. Run Integration Tests

```bash
# Run all 4 tests automatically
./run_all_gps_tests.sh
```

This validates your integration by testing all GPS data endpoints.

### 3. What the Tests Do

✅ **Test 1**: Send 1 GPS point via MQTT  
✅ **Test 2**: Send 5 GPS points via MQTT (batch)  
✅ **Test 3**: Send 1 GPS point via HTTP API  
✅ **Test 4**: Send 5 GPS points via HTTP API (batch)  

## 📁 What's in This Folder

```
manufacturer/
├── README.md                           <- You are here
├── GPS_TESTING_GUIDE.md                <- Detailed testing instructions
├── MANUFACTURER_QUICK_REFERENCE.md     <- One-page cheat sheet
├── scripts/                            <- Ready-to-run test scripts
│   ├── run_all_gps_tests.sh           <- Run all 4 tests automatically
│   ├── manufacturer_device_test.py     <- Main device testing tool
│   └── test_http_api.py               <- HTTP API tester
├── examples/                           <- Code examples for your devices
│   └── esp32_gps_tracker/             <- Complete ESP32 example
└── docs/                              <- Additional documentation
    └── archive/                       <- Detailed specs (if needed)
```

## 🎯 Detailed Integration Steps

### Step 1: Configure Your Environment
```bash
# Set your manufacturer secret (provided by HFSS)
export MANUFACTURER_SECRET="GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe"  # Example - use your actual secret

# Set the API endpoint (production)
export API_URL="https://dg-dev.hikeandfly.app/api/v1"
export MQTT_HOST="dg-mqtt.hikeandfly.app"
```

### Step 2: Register a Test Device
```bash
# Register a new device (happens once at factory)
python3 scripts/manufacturer_device_test.py \
  --api-url "$API_URL" \
  --mqtt-host "$MQTT_HOST" \
  --device-id TEST-001 \
  --manufacturer-secret "$MANUFACTURER_SECRET" \
  --num-messages 0

# This simulates:
# 1. Factory provisioning (generating device credentials)
# 2. First boot registration (device self-registers with cloud)
# 3. Saves credentials to /tmp/device_TEST-001_complete.json
```

### Step 3: Send GPS Data
```bash
# Send via MQTT (recommended for real-time tracking)
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_TEST-001_complete.json \
  --skip-registration \
  --num-messages 5

# Send batch via MQTT (power-efficient)
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_TEST-001_complete.json \
  --skip-registration \
  --batch-mode \
  --batch-size 10 \
  --num-batches 3

# Send via HTTP API (for periodic updates)
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_TEST-001_complete.json \
  --skip-registration \
  --test-http-batch
```

## 📊 Understanding the Scripts

### manufacturer_device_test.py
The main integration testing tool that simulates a complete device lifecycle:

```bash
python3 scripts/manufacturer_device_test.py --help
```

**Key Parameters:**
- `--device-id`: Unique device identifier (e.g., "GPS-TRACKER-001")
- `--manufacturer-secret`: Your company's secret key
- `--api-url`: API endpoint (default: https://dg-dev.hikeandfly.app/api/v1)
- `--mqtt-host`: MQTT broker (default: dg-mqtt.hikeandfly.app)
- `--skip-registration`: Use existing device credentials
- `--config-file`: Path to saved device configuration
- `--batch-mode`: Send multiple GPS points in one message
- `--num-messages`: Number of GPS points to send

### run_all_gps_tests.sh
Automated test suite that validates all integration endpoints:

```bash
./run_all_gps_tests.sh
```

**What it tests:**
1. MQTT single message
2. MQTT batch messages
3. HTTP single POST
4. HTTP batch POST

### paraglider_emulator.py
Advanced traffic simulator for load testing:

```bash
python3 scripts/paraglider_emulator.py \
  --domain dg-dev.hikeandfly.app \
  --devices 10 \
  --duration 30
```

**Features:**
- Simulates multiple devices simultaneously
- Realistic flight patterns (takeoff, thermal, landing)
- Configurable device count and duration

## 🔧 Integration Options

### Option A: MQTT (Recommended for Real-time)
- **Protocol**: MQTT over TLS (port 8883)
- **Best for**: Continuous GPS tracking
- **Power efficient**: Batch up to 30 points

### Option B: HTTP API
- **Protocol**: HTTPS REST API
- **Best for**: Periodic updates
- **Simple**: Standard HTTP POST requests

## 📚 Need More Details?

- **Testing Guide**: See [GPS_TESTING_GUIDE.md](GPS_TESTING_GUIDE.md)
- **Quick Reference**: See [MANUFACTURER_QUICK_REFERENCE.md](MANUFACTURER_QUICK_REFERENCE.md)
- **Certificate Info**: See [CERTIFICATE_INFO.md](CERTIFICATE_INFO.md)
- **ESP32 Example**: See [examples/esp32_gps_tracker/](examples/esp32_gps_tracker/)

## 🆘 Getting Help

1. **Common Issues**: Check the troubleshooting section in GPS_TESTING_GUIDE.md
2. **Integration Support**: Contact your HFSS representative
3. **Technical Specs**: See docs/archive/ for detailed documentation

---

**Ready to start?** → Run `./scripts/run_all_gps_tests.sh` and see your GPS data in action!