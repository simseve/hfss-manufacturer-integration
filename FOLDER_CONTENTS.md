# 📦 Manufacturer Folder Contents

## Essential Files for Testing

### 🚀 Main Test Script
- **`run_all_gps_tests.sh`** - Executes all 4 GPS tests automatically
  - Test 1: MQTT single point
  - Test 2: MQTT batch (5 points)
  - Test 3: HTTP single point  
  - Test 4: HTTP batch (15 points)

### 🐍 Core Python Script
- **`scripts/manufacturer_device_test.py`** - Complete device lifecycle simulation
  - Device provisioning
  - Registration with platform
  - MQTT/HTTP data transmission

### 📚 Documentation
- **`GUIDA_ITALIANA.md`** - Simple guide in Italian for non-technical users
- **`README.md`** - Main technical documentation
- **`QUICK_START.md`** - 5-minute quick start guide
- **`GPS_TESTING_GUIDE.md`** - Detailed GPS testing instructions
- Other guides for reference

### 💻 Examples
- **`examples/esp32_gps_tracker/`** - Arduino code for ESP32 devices
- **`examples/manufacturer_integration_example.py`** - Python integration example

### 🔧 Configuration
- **`.env.example`** - Environment configuration template

## What Was Removed
- All hardcoded test scripts with credentials
- Redundant test files
- Scripts specific to remote testing

## Ready for Distribution
This folder is now clean and ready to be shared with Digifly's engineering team. All sensitive credentials have been removed and replaced with environment variables.