# ESP32 GPS Tracker Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing a GPS tracker on ESP32 that integrates with the HFSS-DIGI tracking platform. The system uses secure MQTT over TLS with HMAC message signing.

## Prerequisites

### Hardware Requirements
- ESP32 with GPS module (e.g., NEO-6M, NEO-8M)
- Minimum 4MB flash memory
- Stable power supply (3.3V)
- Optional: External antenna for better GPS reception

### Software Libraries
```cpp
// Required ESP32 libraries
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>        // MQTT client
#include <ArduinoJson.h>         // JSON handling
#include <mbedtls/md.h>          // HMAC-SHA256
#include <Preferences.h>         // Secure storage
#include <TinyGPS++.h>           // GPS parsing
#include <HTTPClient.h>          // HTTP for registration
```

## Security Architecture

### 1. Factory Provisioning (Manufacturer Responsibility)
Each device must be provisioned with:
- **Device ID**: Unique identifier (e.g., `PARA-20250711-12345-0001`)
- **Device Secret**: 256-bit random secret for HMAC signing
- **Registration Token**: HMAC-SHA256(manufacturer_secret, device_info)
- **Manufacturer ID**: Your assigned manufacturer identifier

### 2. Secure Storage
Store credentials in ESP32's encrypted NVS (Non-Volatile Storage):
```cpp
Preferences preferences;
preferences.begin("device-creds", false);
preferences.putString("device_id", DEVICE_ID);
preferences.putString("device_secret", DEVICE_SECRET);
preferences.putString("reg_token", REGISTRATION_TOKEN);
preferences.end();
```

## API Integration Flow

### Step 1: Device Registration (First Boot Only)

**Endpoint**: `POST /api/v1/devices/register`

```cpp
// Example registration code
void registerDevice() {
    HTTPClient http;
    WiFiClientSecure client;
    client.setInsecure(); // For testing only, use CA cert in production
    
    // Prepare registration payload
    StaticJsonDocument<512> doc;
    doc["device_id"] = DEVICE_ID;
    doc["manufacturer"] = "DIGIFLY";
    doc["registration_token"] = REGISTRATION_TOKEN;
    doc["device_secret"] = DEVICE_SECRET;
    doc["device_type"] = "PARAGLIDER_TRACKER";
    doc["firmware_version"] = "1.0.0";
    
    JsonObject device_info = doc.createNestedObject("device_info");
    device_info["model"] = "ESP32-GPS-v1";
    device_info["capabilities"] = "gps,accelerometer";
    
    String payload;
    serializeJson(doc, payload);
    
    // Send registration request
    http.begin(client, "https://your-domain.com/api/v1/devices/register");
    http.addHeader("Content-Type", "application/json");
    
    int httpCode = http.POST(payload);
    
    if (httpCode == 200) {
        String response = http.getString();
        StaticJsonDocument<512> responseDoc;
        deserializeJson(responseDoc, response);
        
        // Store credentials securely
        const char* api_key = responseDoc["api_key"];
        const char* mqtt_username = responseDoc["mqtt_username"];
        const char* mqtt_password = responseDoc["mqtt_password"];
        
        preferences.begin("device-creds", false);
        preferences.putString("api_key", api_key);
        preferences.putString("mqtt_user", mqtt_username);
        preferences.putString("mqtt_pass", mqtt_password);
        preferences.end();
        
        Serial.println("Registration successful!");
    }
    
    http.end();
}
```

**Expected Response**:
```json
{
    "device_id": "PARA-20250711-12345-0001",
    "api_key": "gps_xxxxxxxxxxxxx",
    "mqtt_username": "device_PARA-20250711-12345-0001",
    "mqtt_password": "generated_secure_password"
}
```

### Step 2: Download CA Certificate

**Endpoint**: `GET /ca.crt`

```cpp
// Download and store CA certificate for TLS
void downloadCACert() {
    HTTPClient http;
    http.begin("http://your-domain.com/ca.crt");
    
    int httpCode = http.GET();
    if (httpCode == 200) {
        String cert = http.getString();
        
        // Store in SPIFFS or LittleFS
        File file = SPIFFS.open("/ca.crt", FILE_WRITE);
        file.print(cert);
        file.close();
    }
    
    http.end();
}
```

### Step 3: MQTT Connection Setup

```cpp
WiFiClientSecure wifiClient;
PubSubClient mqttClient(wifiClient);

void setupMQTT() {
    // Load CA certificate
    File ca = SPIFFS.open("/ca.crt", "r");
    String caCert = ca.readString();
    ca.close();
    
    wifiClient.setCACert(caCert.c_str());
    
    // Configure MQTT
    mqttClient.setServer("your-domain.com", 8883); // TLS port
    mqttClient.setCallback(mqttCallback);
    
    // Connect with device credentials
    String clientId = "esp32-" + String(DEVICE_ID);
    String username = preferences.getString("mqtt_user");
    String password = preferences.getString("mqtt_pass");
    
    if (mqttClient.connect(clientId.c_str(), 
                          username.c_str(), 
                          password.c_str())) {
        Serial.println("MQTT connected!");
        
        // Subscribe to device commands
        String cmdTopic = "devices/" + String(DEVICE_ID) + "/command";
        mqttClient.subscribe(cmdTopic.c_str());
    }
}
```

### Step 4: GPS Data Transmission

**MQTT Topic**: `gps/{device_id}/data`

```cpp
void sendGPSData(float lat, float lon, float alt, float speed) {
    // Create GPS data object
    StaticJsonDocument<512> gpsDoc;
    gpsDoc["device_id"] = DEVICE_ID;
    gpsDoc["flight_id"] = getCurrentFlightId(); // UUID v4 for flight session
    gpsDoc["timestamp"] = getISO8601Time(); // UTC timestamp
    gpsDoc["latitude"] = lat;
    gpsDoc["longitude"] = lon;
    gpsDoc["altitude"] = alt;
    gpsDoc["speed"] = speed;
    gpsDoc["heading"] = gps.course.deg();
    gpsDoc["accuracy"] = gps.hdop.value() / 100.0;
    gpsDoc["satellites"] = gps.satellites.value();
    gpsDoc["battery_level"] = getBatteryLevel();
    
    // Optional metadata
    JsonObject metadata = gpsDoc.createNestedObject("device_metadata");
    metadata["fix_quality"] = gps.location.isValid() ? "3D" : "No Fix";
    metadata["temperature"] = readTemperature();
    
    // Create canonical JSON for signing
    String canonicalJson;
    serializeJson(gpsDoc, canonicalJson);
    
    // Generate HMAC signature
    String signature = generateHMAC(canonicalJson);
    
    // Create final message
    StaticJsonDocument<768> message;
    message["data"] = gpsDoc;
    message["signature"] = signature;
    message["api_key"] = preferences.getString("api_key");
    
    // Publish to MQTT
    String payload;
    serializeJson(message, payload);
    
    String topic = "gps/" + String(DEVICE_ID) + "/data";
    mqttClient.publish(topic.c_str(), payload.c_str(), false); // QoS 0
}

String generateHMAC(String data) {
    // Get device secret
    String secret = preferences.getString("device_secret");
    
    // HMAC-SHA256
    unsigned char hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
    
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
    mbedtls_md_hmac_starts(&ctx, (unsigned char*)secret.c_str(), secret.length());
    mbedtls_md_hmac_update(&ctx, (unsigned char*)data.c_str(), data.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    
    // Convert to hex string
    String hmacHex = "";
    for (int i = 0; i < 32; i++) {
        char str[3];
        sprintf(str, "%02x", (int)hmacResult[i]);
        hmacHex += str;
    }
    
    return hmacHex;
}
```

## Message Format

### GPS Data Message Structure
```json
{
    "data": {
        "device_id": "PARA-20250711-12345-0001",
        "timestamp": "2025-01-11T10:30:00.000Z",
        "latitude": 45.923700,
        "longitude": 6.869500,
        "altitude": 2450.5,
        "speed": 35.2,
        "heading": 180.0,
        "accuracy": 5.0,
        "satellites": 12,
        "battery_level": 85,
        "device_metadata": {
            "temperature": 22.5,
            "fix_quality": "3D"
        }
    },
    "signature": "a3f2b1c4d5e6...",  // HMAC-SHA256 of data object
    "api_key": "gps_xxxxxxxxxxxxx"
}
```

### Batch GPS Data Sending (Power Efficient)

For power-constrained devices, collect multiple GPS points and send them in batches:

```cpp
// Buffer for collecting GPS points
StaticJsonDocument<4096> batchBuffer;
JsonArray pointsArray = batchBuffer.createNestedArray("data");
int pointCount = 0;
unsigned long lastBatchTime = 0;
const int BATCH_SIZE = 30;  // Send every 30 points
const unsigned long BATCH_TIMEOUT = 30000;  // Or every 30 seconds

void collectGPSPoint(float lat, float lon, float alt, float speed) {
    // Create GPS point
    JsonObject point = pointsArray.createNestedObject();
    point["device_id"] = DEVICE_ID;
    point["flight_id"] = getCurrentFlightId();
    point["timestamp"] = getISO8601Time();
    point["latitude"] = lat;
    point["longitude"] = lon;
    point["altitude"] = alt;
    point["speed"] = speed;
    point["heading"] = gps.course.deg();
    point["accuracy"] = gps.hdop.value() / 100.0;
    point["satellites"] = gps.satellites.value();
    point["battery_level"] = getBatteryLevel();
    
    pointCount++;
    
    // Send batch if size reached or timeout
    if (pointCount >= BATCH_SIZE || 
        (millis() - lastBatchTime >= BATCH_TIMEOUT && pointCount > 0)) {
        sendBatch();
    }
}

void sendBatch() {
    // Calculate signature for entire batch
    String batchJson;
    serializeJson(batchBuffer["data"], batchJson);
    String signature = generateHMAC(batchJson);
    
    // Add auth fields
    batchBuffer["signature"] = signature;
    batchBuffer["api_key"] = preferences.getString("api_key");
    
    // Send via MQTT
    String payload;
    serializeJson(batchBuffer, payload);
    
    String topic = "gps/" + String(DEVICE_ID) + "/data";
    if (mqttClient.publish(topic.c_str(), payload.c_str(), false)) {
        Serial.println("Batch sent: " + String(pointCount) + " points");
    }
    
    // Reset buffer
    batchBuffer.clear();
    pointsArray = batchBuffer.createNestedArray("data");
    pointCount = 0;
    lastBatchTime = millis();
}
```

## Best Practices

### 1. Power Management
```cpp
// Send GPS updates efficiently
void loop() {
    static unsigned long lastUpdate = 0;
    unsigned long interval = 1000; // 1 second default
    
    // Adjust interval based on movement
    if (deviceMoving()) {
        interval = 1000;  // 1 second when moving
    } else {
        interval = 30000; // 30 seconds when stationary
    }
    
    if (millis() - lastUpdate > interval) {
        if (gps.location.isValid()) {
            sendGPSData(gps.location.lat(), 
                       gps.location.lng(),
                       gps.altitude.meters(),
                       gps.speed.kmph());
        }
        lastUpdate = millis();
    }
}
```

### 2. Connection Recovery
```cpp
void maintainConnections() {
    // WiFi reconnection
    if (WiFi.status() != WL_CONNECTED) {
        reconnectWiFi();
    }
    
    // MQTT reconnection with exponential backoff
    if (!mqttClient.connected()) {
        static unsigned long lastReconnect = 0;
        static int reconnectDelay = 1000;
        
        if (millis() - lastReconnect > reconnectDelay) {
            if (setupMQTT()) {
                reconnectDelay = 1000; // Reset on success
            } else {
                reconnectDelay = min(reconnectDelay * 2, 60000); // Max 1 minute
            }
            lastReconnect = millis();
        }
    }
}
```

### 3. Error Handling
- Validate GPS data before sending (check for valid fix)
- Buffer messages during connection loss
- Implement watchdog timer for system stability
- Log errors to SPIFFS for debugging

### 4. Security Considerations
- **Never** hardcode secrets in source code
- Store all credentials in encrypted NVS
- Use secure boot and flash encryption
- Implement firmware signature verification for OTA updates
- Rotate device secrets periodically (coordinate with backend)

## Testing Checklist

1. **Factory Reset Test**
   - Erase all NVS data
   - Verify device can register from scratch
   - Confirm credentials are properly stored

2. **Connection Tests**
   - Test WiFi disconnection/reconnection
   - Test MQTT disconnection/reconnection
   - Verify TLS certificate validation

3. **GPS Tests**
   - Test with no GPS fix
   - Test with poor GPS signal
   - Verify accuracy reporting

4. **Security Tests**
   - Verify HMAC signatures are correct
   - Test with wrong device secret (should fail)
   - Ensure no credentials in logs

5. **Power Tests**
   - Test battery level reporting
   - Verify deep sleep modes
   - Test wake-up and quick GPS fix

## API Reference Summary

| Endpoint | Method | Purpose |
|----------|---------|---------|
| `/api/v1/devices/register` | POST | One-time device registration |
| `/ca.crt` | GET | Download CA certificate |
| `mqtts://domain:8883` | MQTT | Secure MQTT connection |

### MQTT Topics

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `gps/{device_id}/data` | Publish | Send GPS updates |
| `devices/{device_id}/command` | Subscribe | Receive commands |
| `devices/{device_id}/config` | Subscribe | Receive configuration |

## Support

For technical support and manufacturer onboarding:
- Email: support@hfss-digi.com
- Documentation: https://docs.hfss-digi.com
- Test Environment: https://test.hfss-digi.com

## Appendix: Example Arduino Sketch

A complete example implementation is available at:
`examples/esp32_gps_tracker/esp32_gps_tracker.ino`

This includes:
- Full registration flow
- GPS reading and transmission
- Power management
- Error handling
- OTA update support