# Script Usage Documentation

Complete guide for all integration testing scripts.

## Table of Contents
1. [manufacturer_device_test.py](#manufacturer_device_testpy)
2. [run_all_gps_tests.sh](#run_all_gps_testssh)
3. [paraglider_emulator.py](#paraglider_emulatorpy)

---

## manufacturer_device_test.py

Main integration testing tool that simulates complete device lifecycle.

### Basic Usage

```bash
python3 scripts/manufacturer_device_test.py [OPTIONS]
```

### Common Use Cases

#### 1. First-Time Device Registration
```bash
python3 scripts/manufacturer_device_test.py \
  --api-url "https://dg-dev.hikeandfly.app/api/v1" \
  --mqtt-host "dg-mqtt.hikeandfly.app" \
  --device-id "MY-DEVICE-001" \
  --manufacturer-secret "GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe" \
  --num-messages 5
```

**What it does:**
1. Generates device credentials
2. Registers device with platform
3. Connects to MQTT broker
4. Sends 5 GPS points
5. Saves config to `/tmp/device_MY-DEVICE-001_complete.json`

#### 2. Send Data with Existing Device
```bash
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_MY-DEVICE-001_complete.json \
  --skip-registration \
  --num-messages 10
```

#### 3. Batch Mode (Power Efficient)
```bash
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_MY-DEVICE-001_complete.json \
  --skip-registration \
  --batch-mode \
  --batch-size 20 \
  --num-batches 3
```

**Sends:** 3 batches × 20 points = 60 GPS points total

#### 4. HTTP API Testing
```bash
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_MY-DEVICE-001_complete.json \
  --skip-registration \
  --test-http-batch
```

### All Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `--api-url` | API endpoint URL | https://dg-dev.hikeandfly.app/api/v1 | No |
| `--mqtt-host` | MQTT broker hostname | dg-mqtt.hikeandfly.app | No |
| `--mqtt-port` | MQTT broker port | 8883 | No |
| `--device-id` | Unique device identifier | Generated | No |
| `--device-num` | Device number for auto ID | 1 | No |
| `--manufacturer-secret` | Your 32-char secret | - | Yes (first time) |
| `--ca-cert` | Path to CA certificate | Auto-download | No |
| `--skip-registration` | Skip device registration | False | No |
| `--config-file` | Load existing config | - | No |
| `--batch-mode` | Send in batches | False | No |
| `--batch-size` | Points per batch | 10 | No |
| `--num-batches` | Number of batches | 3 | No |
| `--test-http-batch` | Test HTTP batch API | False | No |
| `--num-messages` | Individual messages | 10 | No |

### Output Files

The script creates these files:
- `/tmp/device_config_[num].json` - Initial device config
- `/tmp/device_[ID]_complete.json` - Full config with credentials
- `/tmp/mqtt_ca.crt` - Downloaded CA certificate

### Exit Codes
- `0` - Success
- `1` - Registration failed
- `2` - MQTT connection failed
- `3` - Data transmission failed

---

## run_all_gps_tests.sh

Automated test suite running all 4 integration tests.

### Basic Usage

```bash
./run_all_gps_tests.sh
```

### What It Tests

1. **MQTT Single Point** - Basic GPS transmission
2. **MQTT Batch** - 5 points in one message
3. **HTTP Single Point** - REST API test
4. **HTTP Batch** - 5 points via HTTP

### Configuration

Edit the script to change defaults:
```bash
# Production settings
API_URL="https://dg-dev.hikeandfly.app/api/v1"
MQTT_HOST="dg-mqtt.hikeandfly.app"
MANUFACTURER_SECRET="GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe"
```

### Expected Output

```
=== Testing All 4 GPS Endpoints (PRODUCTION) ===
🔗 Production Endpoints:
   API: https://dg-dev.hikeandfly.app/api/v1
   MQTT: dg-mqtt.hikeandfly.app:8883

1. Testing MQTT Single GPS Point
✅ DEVICE INTEGRATION TEST COMPLETED SUCCESSFULLY!

2. Testing MQTT Batch GPS Points
✅ DEVICE INTEGRATION TEST COMPLETED SUCCESSFULLY!

3. Testing HTTP Single GPS Point
✅ DEVICE INTEGRATION TEST COMPLETED SUCCESSFULLY!

4. Testing HTTP Batch GPS Points
✅ DEVICE INTEGRATION TEST COMPLETED SUCCESSFULLY!

=== All Tests Complete ===
✅ If all tests passed, your integration is working correctly!
```

### Troubleshooting

If a test fails:
1. Check network connectivity
2. Verify manufacturer secret
3. Ensure ports 8883 and 443 are open
4. Check `/tmp/device_*.json` for saved configs

---

## paraglider_emulator.py

Advanced traffic simulator for load testing and realistic flight patterns.

### Basic Usage

```bash
python3 scripts/paraglider_emulator.py [OPTIONS]
```

### Common Scenarios

#### 1. Single Device Test
```bash
python3 scripts/paraglider_emulator.py \
  --domain dg-dev.hikeandfly.app \
  --devices 1 \
  --duration 10
```

#### 2. Load Testing (100 Devices)
```bash
python3 scripts/paraglider_emulator.py \
  --domain dg-dev.hikeandfly.app \
  --devices 100 \
  --duration 60
```

#### 3. Long Duration Test
```bash
python3 scripts/paraglider_emulator.py \
  --domain dg-dev.hikeandfly.app \
  --devices 10 \
  --duration 1440  # 24 hours
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--domain` | Server domain | dg-dev.hikeandfly.app |
| `--devices` | Number of devices | 5 |
| `--duration` | Test duration (minutes) | 30 |

### Simulation Features

The emulator simulates realistic paraglider behavior:

1. **Device Lifecycle**
   - Registration
   - Activation
   - Flight sessions
   - Landing
   - Deactivation

2. **Flight Patterns**
   - Takeoff sequence
   - Thermal circling
   - Cross-country flight
   - Landing approach
   - Emergency scenarios

3. **Data Patterns**
   - Variable update frequency (1-10 seconds)
   - Altitude changes
   - Speed variations
   - Battery drain
   - GPS accuracy changes

### Performance Metrics

The emulator reports:
- Messages sent per device
- Success/failure rates
- Average latency
- Connection stability
- Data throughput

### Example Output

```
🚀 Starting Paraglider Emulator
📡 Domain: dg-dev.hikeandfly.app
✈️ Devices: 10
⏱️ Duration: 30 minutes

Device PG-001: ✅ Registered | 🛫 Taking off
Device PG-002: ✅ Registered | 🛫 Taking off
...
Device PG-001: 🔄 Thermal at 2850m | 📍 Sent 150 points
Device PG-002: ➡️ Gliding at 2650m | 📍 Sent 145 points
...
Device PG-001: 🛬 Landing | Total: 450 points
Device PG-002: 🛬 Landing | Total: 442 points

📊 Summary:
- Total devices: 10
- Total points sent: 4,485
- Success rate: 99.8%
- Average points/device: 448.5
- Test duration: 30:00
```

---

## Best Practices

### 1. Development Workflow

```bash
# Step 1: Test with single device
python3 scripts/manufacturer_device_test.py \
  --device-id DEV-001 \
  --manufacturer-secret $SECRET \
  --num-messages 1

# Step 2: Test batch mode
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_DEV-001_complete.json \
  --skip-registration \
  --batch-mode

# Step 3: Run full test suite
./run_all_gps_tests.sh

# Step 4: Load test with emulator
python3 scripts/paraglider_emulator.py \
  --devices 50 \
  --duration 10
```

### 2. Production Testing

```bash
# Register production device
python3 scripts/manufacturer_device_test.py \
  --device-id PROD-$(date +%s) \
  --manufacturer-secret $PROD_SECRET \
  --num-messages 0

# Test with real GPS data
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_PROD_*.json \
  --skip-registration \
  --batch-mode \
  --batch-size 30
```

### 3. Debugging

```bash
# Verbose output
python3 scripts/manufacturer_device_test.py \
  --device-id DEBUG-001 \
  --manufacturer-secret $SECRET \
  --num-messages 1 \
  2>&1 | tee debug.log

# Check saved configs
cat /tmp/device_DEBUG-001_complete.json | jq .

# Monitor MQTT traffic (if mosquitto-clients installed)
mosquitto_sub -h dg-mqtt.hikeandfly.app -p 8883 \
  --cafile /tmp/mqtt_ca.crt \
  -u "device_DEBUG-001" \
  -P "password_from_config" \
  -t "#" -v
```

---

## Troubleshooting Script Issues

### Script Won't Run
```bash
# Make executable
chmod +x run_all_gps_tests.sh

# Check Python version
python3 --version  # Must be 3.7+

# Install dependencies
pip install -r requirements.txt
```

### Import Errors
```bash
# Install missing modules
pip install paho-mqtt requests python-dotenv

# Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Permission Denied
```bash
# Check file permissions
ls -la scripts/

# Fix permissions
chmod +x scripts/*.sh
chmod +r scripts/*.py
```

### Certificate Issues
```bash
# Download manually
curl -o ca.crt https://dg-dev.hikeandfly.app/ca.crt

# Verify certificate
openssl x509 -in ca.crt -text -noout

# Use specific certificate
python3 scripts/manufacturer_device_test.py \
  --ca-cert ./ca.crt \
  ...
```

---

## Support

For script issues or questions:
- Check logs in `/tmp/device_*.json`
- Review error messages carefully
- Contact support@hikeandfly.app with:
  - Script output
  - Device ID
  - Timestamp of issue
  - Error messages