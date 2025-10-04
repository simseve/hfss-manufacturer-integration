# Manufacturer Quick Reference Card

## 🚀 Integration Steps

### 1️⃣ Factory Provisioning
```
For each device, generate and store:
├── Device ID:     PARA-YYYYMMDD-NNNNN-XXXX
├── Device Secret: 256-bit random (hex)
├── Reg Token:     HMAC-SHA256(manufacturer_secret, device_info)
└── Store in:      ESP32 encrypted NVS
```

### 2️⃣ First Boot Registration
```http
POST /api/v1/devices/register
Content-Type: application/json

{
  "device_id": "PARA-20250711-12345-0001",
  "manufacturer": "DIGIFLY",
  "registration_token": "...",
  "device_secret": "...",
  "device_type": "PARAGLIDER_TRACKER"
}

Response:
{
  "api_key": "gps_xxxxx",
  "mqtt_username": "device_PARA-20250711-12345-0001",
  "mqtt_password": "generated_password"
}
```

### 3️⃣ MQTT Connection
```
Server: dg-mqtt.hikeandfly.app:8883 (TLS)
Username: {mqtt_username from registration}
Password: {mqtt_password from registration}
CA Cert: Download from https://dg-dev.hikeandfly.app/ca.crt
```

### 4️⃣ Send GPS Data
```json
TOPIC: gps/{device_id}/data

{
  "data": {
    "device_id": "PARA-20250711-12345-0001",
    "flight_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-01-11T10:30:00.000Z",
    "latitude": 45.923700,
    "longitude": 6.869500,
    "altitude": 2450.5,
    "speed": 35.2,
    "heading": 180.0,
    "accuracy": 5.0,
    "satellites": 12,
    "battery_level": 85
  },
  "signature": "HMAC-SHA256(data)",
  "api_key": "{from registration}"
}
```

**Note**: `flight_id` is a UUID v4 that identifies a flight session. Generate a new flight_id when takeoff is detected and keep it constant during the entire flight. Close the flight when landing.

## 🔐 Security Checklist

- [ ] Unique device secret per device (never shared)
- [ ] Secrets stored in encrypted NVS
- [ ] TLS certificate validation enabled
- [ ] HMAC signature on every message
- [ ] No hardcoded credentials in firmware
- [ ] Secure boot enabled (production)

## 📊 Message Rates

| State | Recommended Interval |
|-------|---------------------|
| Moving | 1 second |
| Stationary | 30 seconds |
| No GPS Fix | 60 seconds |
| Low Battery | 300 seconds |

## 🛠️ Troubleshooting

### Registration Fails (403)
- Check manufacturer secret
- Verify registration token calculation
- Ensure device ID format is correct

### MQTT Connection Fails
- Verify TLS certificate
- Check username format: `device_{device_id}`
- Ensure port 8883 (not 1883)

### Messages Rejected
- Verify HMAC signature calculation
- Check timestamp is UTC and recent (±5 min)
- Ensure all required fields present

### 5️⃣ Close Flight (Landing)
```json
TOPIC: flight/{device_id}/close

{
  "flight_id": "550e8400-e29b-41d4-a716-446655440000",
  "api_key": "{from registration}"
}

Response (on topic flight/{device_id}/closed):
{
  "flight_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "closed",
  "distance": 45.8,
  "duration": "01:23:45"
}
```

**HTTP Alternative:**
```bash
POST /api/v1/flights/{flight_id}/close
X-API-Key: {your_api_key}
```

## 📡 Test Commands

```bash
# Test registration
curl -X POST https://dg-dev.hikeandfly.app/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{"device_id":"TEST-001", ...}'

# Test MQTT (will fail auth, but tests connection)
mosquitto_pub -h dg-mqtt.hikeandfly.app -p 8883 \
  --cafile ca.crt -t test -m test \
  -u device_TEST -P test

# Test flight close (MQTT)
mosquitto_pub -h dg-mqtt.hikeandfly.app -p 8883 \
  --cafile ca.crt \
  -u device_YOUR-DEVICE -P your_password \
  -t "flight/YOUR-DEVICE/close" \
  -m '{"flight_id":"uuid","api_key":"key"}'
```

## 📞 Support

**API Endpoint**: https://dg-dev.hikeandfly.app/api/v1  
**MQTT Broker**: dg-mqtt.hikeandfly.app:8883  
**CA Certificate**: https://dg-dev.hikeandfly.app/ca.crt  
**Documentation**: Check MANUFACTURER_INTEGRATION_GUIDE.md

---
*Version 1.0 - January 2025*