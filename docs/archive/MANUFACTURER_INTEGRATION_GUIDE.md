# Manufacturer Integration Guide

This guide provides manufacturers with the necessary information to integrate GPS tracking devices with the HFSS-DIGI platform.

## 🔐 Production Endpoints & Credentials

### API Endpoint
- **Base URL**: `https://dg-dev.hikeandfly.app/api/v1`
- **Device Registration**: `https://dg-dev.hikeandfly.app/api/v1/devices/register`
- **Health Check**: `https://dg-dev.hikeandfly.app/health`

### MQTT Broker
- **Host**: `dg-mqtt.hikeandfly.app`
- **Port**: `8883` (TLS/SSL required)
- **Protocol**: MQTT 3.1.1
- **Authentication**: Username/Password (received after device registration)

### Manufacturer Credentials
- **Manufacturer ID**: `DIGIFLY`
- **Manufacturer Secret**: `GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe`

> ⚠️ **IMPORTANT**: Keep the manufacturer secret secure. It should be stored in your secure production systems only.

## 📜 CA Certificate

### Option 1: Download from API (Recommended)
```bash
# Download the CA certificate
curl https://dg-dev.hikeandfly.app/ca.crt -o ca.crt

# Verify the certificate
openssl x509 -in ca.crt -text -noout
```

### Option 2: Embedded Certificate
For production devices, you may want to embed the CA certificate. Here's the current certificate:

```
-----BEGIN CERTIFICATE-----
MIIDiTCCAnGgAwIBAgIUcS9mwe18q7pvyZVnD9JvPCfP9ZswDQYJKoZIhvcNAQEL
BQAwVDELMAkGA1UEBhMCVVMxDjAMBgNVBAgMBVN0YXRlMQ0wCwYDVQQHDARDaXR5
MRUwEwYDVQQKDAxHUFMtVHJhY2tpbmcxDzANBgNVBAMMBkdQUy1DQTAeFw0yNTA3
MTExMDIzNDVaFw0zNTA3MDkxMDIzNDVaMFQxCzAJBgNVBAYTAlVTMQ4wDAYDVQQI
DAVTdGF0ZTENMAsGA1UEBwwEQ2l0eTEVMBMGA1UECgwMR1BTLVRyYWNraW5nMQ8w
DQYDVQQDDAZHUFMtQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC8
vhO5s/a0k8XKHoUYIVhgE8rKfwdwLgOlYsjm0lHLr0pqpXU9JgZ9WvKlVA8X4iL7
CQdHFxT2xvvKLQrRzI1zEP3iHJl8hQ75iR7i55BnqQBEO3NA7wo9JAoGJrW+UJEm
rUKKRGBJo3IE6q3IQvTOOsNT49d7BtKJnVLdN4WLoEg0Y0rq4pCOW9MU3lkmuLHa
WiWO5Y0dhaHPKc9S4dEgCSeNb2aOi3O12A8LHt0T7TOKgL7bI3gOL5+/fzO4RG72
G0q3xCVESDiomxgKsjvW6s8lf7a9LsFRHJ9sYDR72SXCOb7hnCUGEf3tqOI3A6pv
w0ajaqnb9RaD6dQQKHLXAgMBAAGjUzBRMB0GA1UdDgQWBBQhWMkQCxjvKbqOj+Kw
xYHRQVBWyzAfBgNVHSMEGDAWgBQhWMkQCxjvKbqOj+KwxYHRQVBWyzAPBgNVHRMB
Af8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQCupNy/IjOPb9kJtSmk4vXQYJCz
EySnsZ5Lq0oXR7QMuuBINKPLO6AsBEVJ8sCyZE2RKF7gYu8/5VH3+odG7cUa8mrd
5mGfM+4pZI3G4PJH9FQFAUiXxh2xLJNdE1vEFYa9yBqLgqjNdMQRC1kZJBGt0Syj
eKvyl9xR5yfhfwqvKBYGSGk4I9VUMfPcvBPK5AwpC5MfOzdcLaYJxMhYINPz9wW3
6j9c7+5OhnRTKpVFp7gQZYKGCQP/iw76v5vM49+IpWIhS9mLQJVOlGYLUUcJf6Nj
ZH9Xy7o0gv8yPRdltanBcT1a9Z7iXvH3qNT1/wBaJOx/VdaG7Gcv8fnQXkTt
-----END CERTIFICATE-----
```

> **Note**: The certificate is valid until 2035-07-09. You should implement certificate updates in your device firmware.

## 🧪 Testing Your Integration

### Quick Test Script

Save this as `test_device.sh`:

```bash
#!/bin/bash

# Configuration
API_URL="https://dg-dev.hikeandfly.app/api/v1"
MQTT_HOST="dg-mqtt.hikeandfly.app"
MQTT_PORT="8883"
MANUFACTURER_SECRET="GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe"

# Download CA certificate if not present
if [ ! -f ca.crt ]; then
    echo "Downloading CA certificate..."
    curl -s https://dg-dev.hikeandfly.app/ca.crt -o ca.crt
fi

# Run the test
python3 scripts/manufacturer_device_test.py \
    --api-url "$API_URL" \
    --mqtt-host "$MQTT_HOST" \
    --mqtt-port "$MQTT_PORT" \
    --manufacturer-secret "$MANUFACTURER_SECRET" \
    --ca-cert ca.crt \
    --device-num $RANDOM
```

### Python Integration Example

```python
import requests
import paho.mqtt.client as mqtt
import ssl
import json
import hmac
import hashlib
from datetime import datetime, timezone

# Configuration
API_BASE = "https://dg-dev.hikeandfly.app/api/v1"
MQTT_HOST = "dg-mqtt.hikeandfly.app"
MQTT_PORT = 8883
MANUFACTURER_SECRET = "GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe"

# 1. Generate device credentials (at factory)
device_id = f"PARA-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}-0001"
device_secret = secrets.token_hex(32)

# 2. Calculate registration token
message = f"{device_id}:{device_secret}:DIGIFLY"
registration_token = hmac.new(
    MANUFACTURER_SECRET.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# 3. Register device (on first boot)
response = requests.post(
    f"{API_BASE}/devices/register",
    json={
        "device_id": device_id,
        "device_secret": device_secret,
        "registration_token": registration_token,
        "manufacturer": "DIGIFLY",
        "device_metadata": {
            "model": "TRACKER-X1",
            "firmware": "1.0.0"
        }
    }
)

if response.status_code == 200:
    creds = response.json()
    mqtt_username = creds["mqtt_username"]  # device_PARA-20250711-1234-0001
    mqtt_password = creds["mqtt_password"]
    api_key = creds["api_key"]
    
    # 4. Connect to MQTT
    client = mqtt.Client(client_id=device_id)
    client.username_pw_set(mqtt_username, mqtt_password)
    
    # Set up TLS
    client.tls_set(
        ca_certs="ca.crt",
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    
    client.connect(MQTT_HOST, MQTT_PORT)
    
    # 5. Send GPS data
    gps_data = {
        "device_id": device_id,
        "flight_id": "550e8400-e29b-41d4-a716-446655440000",  # UUID v4 for flight session
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latitude": 45.9237,
        "longitude": 6.8694,
        "altitude": 2400.0,
        "speed": 0.0,
        "heading": 0.0,
        "accuracy": 5.0,
        "battery": 85.0,
        "temperature": 22.5
    }
    
    # Calculate HMAC signature
    signature = hmac.new(
        api_key.encode(),
        json.dumps(gps_data, sort_keys=True).encode(),
        hashlib.sha256
    ).hexdigest()
    
    message = {
        "data": gps_data,
        "signature": signature
    }
    
    client.publish(
        f"gps/{device_id}/data",
        json.dumps(message),
        qos=1
    )
```

## 📱 ESP32 Integration Example

For ESP32 devices, here's a simplified Arduino sketch:

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>

// Configuration
const char* API_BASE = "https://dg-dev.hikeandfly.app/api/v1";
const char* MQTT_HOST = "dg-mqtt.hikeandfly.app";
const int MQTT_PORT = 8883;
const char* MANUFACTURER_SECRET = "GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe";

// CA Certificate (embed this in your code)
const char* CA_CERT = R"EOF(
-----BEGIN CERTIFICATE-----
MIIDiTCCAnGgAwIBAgIUcS9mwe18q7pvyZVnD9JvPCfP9ZswDQYJKoZIhvcNAQEL
... (full certificate here) ...
-----END CERTIFICATE-----
)EOF";

// Device credentials (generate these at factory)
String device_id = "PARA-20250711-ESP32-0001";
String device_secret = "your-device-secret-here";
String mqtt_username = "";
String mqtt_password = "";
String api_key = "";

void setup() {
    // 1. Connect to WiFi
    WiFi.begin("SSID", "PASSWORD");
    
    // 2. Register device (only on first boot)
    if (needsRegistration()) {
        registerDevice();
    }
    
    // 3. Connect to MQTT
    connectMQTT();
}

void registerDevice() {
    HTTPClient http;
    http.begin(String(API_BASE) + "/devices/register", CA_CERT);
    http.addHeader("Content-Type", "application/json");
    
    // Calculate registration token
    String message = device_id + ":" + device_secret + ":DIGIFLY";
    String token = calculateHMAC(message, MANUFACTURER_SECRET);
    
    // Prepare JSON
    StaticJsonDocument<512> doc;
    doc["device_id"] = device_id;
    doc["device_secret"] = device_secret;
    doc["registration_token"] = token;
    doc["manufacturer"] = "DIGIFLY";
    
    String json;
    serializeJson(doc, json);
    
    int httpCode = http.POST(json);
    if (httpCode == 200) {
        String response = http.getString();
        // Parse response and save credentials
        saveCredentials(response);
    }
}
```

## 🔒 Security Best Practices

1. **Manufacturer Secret**
   - Never expose in client-side code
   - Use secure storage in factory systems
   - Rotate periodically

2. **Device Secrets**
   - Generate unique 256-bit secrets per device
   - Store in secure flash/TPM on device
   - Never transmit over insecure channels

3. **TLS/SSL**
   - Always verify CA certificate
   - Use TLS 1.2 or higher
   - Implement certificate pinning in production

4. **HMAC Signatures**
   - Sign all GPS data with device API key
   - Verify timestamps to prevent replay attacks
   - Use consistent JSON serialization

## 📊 Data Format

### GPS Data Message Format
```json
{
    "data": {
        "device_id": "PARA-20250711-1234-0001",
        "flight_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2025-07-11T10:30:00.000Z",
        "latitude": 45.9237,
        "longitude": 6.8694,
        "altitude": 2400.0,
        "speed": 0.0,
        "heading": 0.0,
        "accuracy": 5.0,
        "battery": 85.0,
        "temperature": 22.5,
        "satellites": 12,
        "hdop": 0.9
    },
    "signature": "hmac-sha256-signature-here"
}
```

**Note on flight_id**:
- Generate a new UUID v4 when takeoff is detected (e.g., altitude increase, speed > threshold)
- Keep the same flight_id throughout the entire flight
- Set to null when on ground or between flights
- This allows the system to automatically track individual flight sessions

### Batch GPS Data Message Format (NEW)

For devices that collect multiple GPS points before sending (e.g., to save power), you can send an array of GPS points in a single message:

```json
{
    "data": [
        {
            "device_id": "PARA-20250711-1234-0001",
            "flight_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2025-07-11T10:30:00.000Z",
            "latitude": 45.9237,
            "longitude": 6.8694,
            "altitude": 2400.0,
            "speed": 35.0,
            "heading": 180.0,
            "accuracy": 5.0,
            "battery": 85.0
        },
        {
            "device_id": "PARA-20250711-1234-0001",
            "flight_id": "550e8400-e29b-41d4-a716-446655440000", 
            "timestamp": "2025-07-11T10:30:30.000Z",
            "latitude": 45.9238,
            "longitude": 6.8695,
            "altitude": 2405.0,
            "speed": 36.0,
            "heading": 185.0,
            "accuracy": 5.0,
            "battery": 84.9
        }
    ],
    "signature": "hmac-sha256-signature-of-entire-array",
    "api_key": "gps_xxxxxxxxxxxxx"
}
```

**Benefits of Batch Sending**:
- **Power Efficiency**: Single MQTT/HTTP connection for multiple points
- **Network Efficiency**: Less overhead, fewer TCP handshakes
- **Reliability**: All points succeed or fail together
- **ESP32 Friendly**: Minimal memory usage (30 points ≈ 3KB)

### Sending Methods

#### Option 1: MQTT Batch (Recommended for Real-time)
```python
# Send batch of GPS points via MQTT
topic = f"gps/{device_id}/data"
batch_message = {
    "data": collected_points,  # Array of GPS points
    "signature": calculate_hmac(collected_points),
    "api_key": api_key
}
client.publish(topic, json.dumps(batch_message), qos=1)
```

#### Option 2: HTTP Batch API (Good for periodic uploads)
```python
# Send batch via HTTP POST
response = requests.post(
    f"{API_BASE}/api/v1/gps/batch",
    json={"data": collected_points},
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
)
```

### MQTT Topics
- **GPS Data**: `gps/{device_id}/data` (supports both single and batch)
- **Device Status**: `device/{device_id}/status`
- **Commands**: `cmd/{device_id}/request` (subscribe)
- **Responses**: `device/{device_id}/response` (publish)

## 📞 Support

For technical support or additional integration assistance:
- API Documentation: https://dg-dev.hikeandfly.app/docs
- Health Status: https://dg-dev.hikeandfly.app/health

## 🧪 Testing Checklist

- [ ] Download and verify CA certificate
- [ ] Test device registration with your device ID format
- [ ] Verify MQTT connection with TLS
- [ ] Send test GPS data and verify signature
- [ ] Check data appears in platform dashboard
- [ ] Test error handling and reconnection logic
- [ ] Verify battery optimization doesn't affect GPS updates

## 🚀 Production Deployment

Before mass production:
1. Test with at least 100 devices simultaneously
2. Implement firmware update mechanism
3. Add device health monitoring
4. Set up production logging and analytics
5. Create device provisioning workflow