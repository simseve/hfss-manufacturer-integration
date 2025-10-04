# Getting Started with HFSS DIGI Integration

This guide walks you through integrating your GPS devices with HFSS DIGI platform step by step.

## Prerequisites

Before starting, ensure you have:
- ✅ Python 3.7+ installed
- ✅ Network access to `dg-dev.hikeandfly.app`
- ✅ Your manufacturer credentials (see below)

## Step 1: Request Your Manufacturer Credentials

### What You Need
Every manufacturer needs unique credentials to register devices on our platform.

### How to Get Them

#### Option A: Contact Sales
Email **sales@hikeandfly.app** with:
- Company name
- Expected number of devices per year
- Technical contact email
- Use case (paragliding, drones, vehicles, etc.)

#### Option B: Developer Portal
Visit https://dg-dev.hikeandfly.app/developer and:
1. Create a developer account
2. Submit manufacturer application
3. Receive credentials via email

### What You'll Receive
```
MANUFACTURER_ID: YOURCOMPANY
MANUFACTURER_SECRET: abc123def456ghi789jkl012mno345pq  (32 characters)
API_URL: https://dg-dev.hikeandfly.app/api/v1
MQTT_HOST: dg-mqtt.hikeandfly.app
```

**⚠️ IMPORTANT**: Keep your secret secure! It authenticates all your devices.

## Step 2: Set Up Your Environment

### Clone the Integration Repository
```bash
git clone https://github.com/hfss/manufacturer-integration.git
cd manufacturer-integration
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Configure Your Credentials

#### Method 1: Environment File (Recommended)
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Add your credentials to `.env`:
```env
MANUFACTURER_SECRET=your_32_character_secret_here
MANUFACTURER_ID=YOURCOMPANY
API_URL=https://dg-dev.hikeandfly.app/api/v1
MQTT_HOST=dg-mqtt.hikeandfly.app
MQTT_PORT=8883
```

#### Method 2: Environment Variables
```bash
export MANUFACTURER_SECRET="your_32_character_secret_here"
export MANUFACTURER_ID="YOURCOMPANY"
export API_URL="https://dg-dev.hikeandfly.app/api/v1"
export MQTT_HOST="dg-mqtt.hikeandfly.app"
```

## Step 3: Test Your Integration

### Quick Test - Run All Tests
```bash
./run_all_gps_tests.sh
```

This runs 4 tests automatically:
1. ✅ MQTT single GPS point
2. ✅ MQTT batch (5 points)
3. ✅ HTTP single GPS point
4. ✅ HTTP batch (5 points)

### Manual Testing - Step by Step

#### 1. Register a Test Device
```bash
python3 scripts/manufacturer_device_test.py \
  --api-url "https://dg-dev.hikeandfly.app/api/v1" \
  --mqtt-host "dg-mqtt.hikeandfly.app" \
  --device-id "TEST-001" \
  --manufacturer-secret "$MANUFACTURER_SECRET" \
  --num-messages 0
```

**What happens:**
- Generates unique device credentials
- Registers device with platform
- Saves credentials to `/tmp/device_TEST-001_complete.json`
- Device is now ready to send GPS data

#### 2. Send GPS Data via MQTT
```bash
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_TEST-001_complete.json \
  --skip-registration \
  --num-messages 5
```

#### 3. Send GPS Data via HTTP
```bash
python3 scripts/manufacturer_device_test.py \
  --config-file /tmp/device_TEST-001_complete.json \
  --skip-registration \
  --test-http-batch
```

## Step 4: Integrate with Your Device

### For ESP32/Arduino
See `examples/esp32_gps_tracker/` for complete code.

Key steps:
1. Store credentials in secure flash
2. Connect to MQTT with TLS
3. Send GPS data with HMAC signature

### For Python Devices
```python
import json
import hmac
import hashlib
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Load device credentials
with open('device_config.json') as f:
    config = json.load(f)

# Prepare GPS data
gps_data = {
    "device_id": config["device_id"],
    "flight_id": "unique-flight-uuid",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "latitude": 45.9237,
    "longitude": 6.8694,
    "altitude": 2400.0
}

# Calculate HMAC signature
message = json.dumps(gps_data, separators=(',', ':'))
signature = hmac.new(
    config["device_secret"].encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# Send via MQTT
client = mqtt.Client()
client.username_pw_set(config["mqtt_username"], config["mqtt_password"])
client.tls_set(ca_certs="ca.crt")
client.connect("dg-mqtt.hikeandfly.app", 8883)
client.publish(
    f"gps/{config['device_id']}/data",
    json.dumps({"data": gps_data, "signature": signature})
)
```

## Step 5: Understanding Flight Lifecycle

### Complete Flight Flow

1. **Takeoff Detection:**
   - Device detects flight start (altitude/speed threshold)
   - Generate new `flight_id = str(uuid.uuid4())`
   - Start sending GPS points with this flight_id

2. **In-Flight Tracking:**
   - Send GPS points every 10 seconds (or batch every 30 seconds)
   - All points use same flight_id
   - Include altitude, speed, battery level

3. **Landing Detection:**
   - Device detects landing (low speed/stable altitude)
   - Send final GPS points
   - **Close flight session** via MQTT or HTTP

4. **Flight Finalization:**
   - Platform calculates total distance
   - Marks flight as inactive
   - Returns statistics (distance, duration, max altitude)

### MQTT Topics Summary

- **GPS Data**: `gps/{device_id}/data`
- **Close Flight**: `flight/{device_id}/close`
- **Close Confirmation**: `flight/{device_id}/closed` (listen)
- **Errors**: `flight/{device_id}/error` (listen)

## Step 6: Production Deployment

### Device Manufacturing Process

1. **At Factory - Provision Each Device:**
```python
# Generate unique credentials for each device
device_id = f"PROD-{serial_number}"
device_secret = generate_random_secret()
registration_token = calculate_registration_token(device_id, device_secret)

# Store in device's secure storage
store_in_secure_flash({
    "device_id": device_id,
    "device_secret": device_secret,
    "registration_token": registration_token
})
```

2. **First Boot - Device Self-Registers:**
```python
# Device reads credentials from secure storage
credentials = read_secure_flash()

# Register with platform
response = requests.post(
    "https://dg-dev.hikeandfly.app/api/v1/devices/register",
    json={
        "device_id": credentials["device_id"],
        "registration_token": credentials["registration_token"]
    }
)

# Store MQTT credentials
mqtt_creds = response.json()
store_mqtt_credentials(mqtt_creds)
```

3. **Normal Operation - Send GPS Data:**
- Connect to MQTT on boot
- Send GPS updates every 10 seconds
- Batch points if offline
- Reconnect automatically

4. **Flight Close - Finalize Session:**
```python
# When flight ends, close the session
close_payload = {
    "flight_id": current_flight_id,
    "api_key": credentials["api_key"]
}

# Via MQTT (recommended)
client.publish(
    f"flight/{device_id}/close",
    json.dumps(close_payload),
    qos=1
)

# Listen for confirmation
def on_message(client, userdata, msg):
    if msg.topic == f"flight/{device_id}/closed":
        result = json.loads(msg.payload)
        print(f"Flight closed: {result['distance']}km, {result['duration']} duration")
```

## Troubleshooting

### Common Issues

#### "Invalid manufacturer secret"
- Check secret is exactly 32 characters
- No extra spaces or newlines
- Correct secret from HFSS team

#### "MQTT connection timeout"
- Check network connectivity
- Verify MQTT_HOST is correct: `dg-mqtt.hikeandfly.app`
- Ensure port 8883 is not blocked
- CA certificate downloaded correctly

#### "Registration failed"
- Device ID must be unique
- Registration token calculated correctly
- Manufacturer secret is valid

#### "No GPS data received"
- Check HMAC signature calculation
- Timestamp must be UTC ISO format
- Flight ID must be valid UUID
- GPS coordinates in valid range

### Debug Commands

```bash
# Test network connectivity
ping dg-dev.hikeandfly.app
nslookup dg-mqtt.hikeandfly.app

# Test MQTT connection
openssl s_client -connect dg-mqtt.hikeandfly.app:8883

# Check certificate
curl -o ca.crt https://dg-dev.hikeandfly.app/ca.crt
openssl x509 -in ca.crt -text -noout

# Monitor MQTT messages (if you have mosquitto-clients)
mosquitto_sub -h dg-mqtt.hikeandfly.app -p 8883 \
  --cafile ca.crt \
  -u "device_TEST-001" \
  -P "your_mqtt_password" \
  -t "#" -v
```

## Support

### Documentation
- [GPS Testing Guide](GPS_TESTING_GUIDE.md)
- [API Reference](MANUFACTURER_QUICK_REFERENCE.md)
- [Certificate Setup](CERTIFICATE_INFO.md)
- [ESP32 Example](examples/esp32_gps_tracker/)

### Getting Help
- **Technical Issues**: support@hikeandfly.app
- **Sales/Credentials**: sales@hikeandfly.app
- **Emergency**: +41 XX XXX XX XX (Business hours CET)

## Next Steps

1. ✅ Complete integration testing
2. 📱 Implement in your device firmware
3. 🔬 Test with real GPS hardware
4. 📊 Monitor data on dashboard
5. 🚀 Deploy to production

---

**Ready to integrate?** Start with `./run_all_gps_tests.sh` to validate your setup!