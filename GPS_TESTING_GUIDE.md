# GPS Device Testing Guide for Manufacturers

This guide helps device manufacturers test GPS data submission to the HFSS DIGI platform.

## Quick Start

### 1. Device Registration

Every device must be registered before sending GPS data:

```bash
python manufacturer_device_test.py \
  --device-id YOUR-DEVICE-001 \
  --manufacturer-secret YOUR_MANUFACTURER_SECRET \
  --num-messages 0
```

This creates a device configuration file at `/tmp/device_YOUR-DEVICE-001_complete.json` containing:
- API key (for HTTP)
- MQTT credentials
- Device secret (for HMAC signing)

### 2. Test GPS Data Submission

#### Option A: MQTT Single Point
```bash
# Using saved configuration
python manufacturer_device_test.py \
  --config-file /tmp/device_YOUR-DEVICE-001_complete.json \
  --skip-registration \
  --num-messages 3
```

#### Option B: MQTT Batch Mode (Power Efficient)
```bash
# Send 15 points in one message
python manufacturer_device_test.py \
  --config-file /tmp/device_YOUR-DEVICE-001_complete.json \
  --skip-registration \
  --batch-mode \
  --batch-size 15 \
  --num-batches 1
```

#### Option C: HTTP API Testing
```bash
# First update test_http_api.py with your device credentials
# Then run:
python test_http_api.py
```

## Test Scenarios

### 📍 Test 1: Single GPS Point via MQTT
- **Purpose**: Test basic GPS data submission
- **Protocol**: MQTT over TLS (port 8883)
- **Authentication**: Device-specific MQTT credentials
- **Message size**: ~550 bytes

```bash
python manufacturer_device_test.py --config-file /tmp/device_config.json --skip-registration --num-messages 1
```

### 📦 Test 2: Batch GPS Points via MQTT  
- **Purpose**: Test power-efficient batch transmission
- **Protocol**: MQTT over TLS (port 8883)
- **Benefits**: 90% reduction in network overhead
- **Message size**: ~6.5KB for 15 points

```bash
python manufacturer_device_test.py --config-file /tmp/device_config.json --skip-registration --batch-mode --batch-size 15 --num-batches 1
```

### 🌐 Test 3: Single GPS Point via HTTP
- **Purpose**: Test REST API endpoint
- **Protocol**: HTTPS (port 443/80)
- **Authentication**: Bearer token with API key
- **Required**: Valid flight_id (UUID format)

### 🌐 Test 4: Batch GPS Points via HTTP
- **Purpose**: Test batch REST API endpoint
- **Processing**: Asynchronous via Redis Streams
- **Response**: Returns immediately with "accepted" status

## Verify Data Reception

Check if your GPS data reached the database:

```bash
# Check latest points from your device
docker compose exec timescaledb psql -U gps_prod_user -d gps_tracking_production -c \
  "SELECT timestamp, latitude, longitude, altitude FROM gps_data WHERE device_id = 'YOUR-DEVICE-001' ORDER BY timestamp DESC LIMIT 5"

# Count total points sent
docker compose exec timescaledb psql -U gps_prod_user -d gps_tracking_production -c \
  "SELECT COUNT(*) FROM gps_data WHERE device_id = 'YOUR-DEVICE-001'"
```

## Required Data Fields

### Mandatory Fields
- `device_id`: Your registered device ID
- `flight_id`: UUID for the flight session (generate once per flight)
- `timestamp`: ISO 8601 format with timezone
- `latitude`: -90 to 90 degrees
- `longitude`: -180 to 180 degrees

### Optional Fields
- `altitude`: Meters above sea level
- `barometric_altitude`: Barometric altitude in meters
- `speed`: Speed in km/h
- `heading`: Direction in degrees (0-360)
- `accuracy`: GPS accuracy in meters
- `satellites`: Number of satellites
- `battery_level`: Battery percentage (0-100)
- `device_metadata`: JSON object with custom data

## Message Formats

### MQTT Single Point
```json
{
  "data": {
    "device_id": "YOUR-DEVICE-001",
    "flight_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-07-11T21:30:00.000Z",
    "latitude": 45.9237,
    "longitude": 6.8694,
    "altitude": 2400.0,
    "speed": 35.5,
    "battery_level": 85.0
  },
  "signature": "HMAC-SHA256-SIGNATURE",
  "api_key": "YOUR-API-KEY"
}
```

### MQTT Batch
```json
{
  "data": [
    {
      "device_id": "YOUR-DEVICE-001",
      "flight_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2025-07-11T21:30:00.000Z",
      "latitude": 45.9237,
      "longitude": 6.8694,
      "altitude": 2400.0
    },
    {
      "device_id": "YOUR-DEVICE-001",
      "flight_id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2025-07-11T21:30:01.000Z",
      "latitude": 45.9238,
      "longitude": 6.8695,
      "altitude": 2401.0
    }
  ],
  "signature": "HMAC-SHA256-SIGNATURE",
  "api_key": "YOUR-API-KEY"
}
```

## Best Practices

1. **Batch Transmission**: Use batch mode to save power and bandwidth
   - Recommended batch size: 10-30 points
   - Send every 30-60 seconds

2. **Flight Sessions**: Generate new flight_id for each flight
   - Use UUID v4 format
   - Keep same flight_id for all points in a flight

3. **Timestamps**: Always use UTC with timezone
   - ISO 8601 format: `2025-07-11T21:30:00.000Z`
   - Ensure accurate device time synchronization

4. **Connection Management**:
   - MQTT: Maintain persistent connection during flight
   - HTTP: Use connection pooling for multiple requests

5. **Error Handling**:
   - Implement retry logic with exponential backoff
   - Store failed transmissions for later retry
   - Monitor battery level before transmission

## Troubleshooting

### Common Error Messages

#### "Invalid manufacturer secret"
**Cause**: Manufacturer secret is incorrect or malformed
**Solution**:
- Verify secret is exactly 32 characters
- Remove any spaces or newlines
- Check you're using production secret, not test
- Contact HFSS if secret was never provided

#### "Device already exists"
**Cause**: Device ID already registered
**Solution**:
- Use unique device ID for each device
- Check if device was previously registered
- Use `--skip-registration` with existing config file

#### "MQTT connection timed out"
**Cause**: Cannot reach MQTT broker
**Solution**:
```bash
# Test connectivity
ping dg-mqtt.hikeandfly.app
nslookup dg-mqtt.hikeandfly.app
telnet dg-mqtt.hikeandfly.app 8883

# Check firewall allows port 8883
# Verify CA certificate exists
ls -la /tmp/mqtt_ca.crt
```

#### "Invalid HMAC signature"
**Cause**: Signature calculation incorrect
**Solution**:
- Ensure using device_secret for HMAC (not manufacturer secret)
- JSON must be compact: `json.dumps(data, separators=(',', ':'))`
- Use SHA256 algorithm
- Signature must be hexadecimal string

#### "Not authorized"
**Cause**: Invalid credentials
**Solution**:
- Device must be registered first
- MQTT username format: `device_YOUR-DEVICE-001`
- API key must start with `hfss_`
- Password must match registration response

### Data Validation Issues

#### "Invalid GPS coordinates"
**Requirements**:
- Latitude: -90 to 90
- Longitude: -180 to 180
- Not (0, 0) - this is filtered as invalid

#### "Invalid timestamp"
**Requirements**:
- ISO 8601 format with timezone
- Must be UTC: `2025-07-11T21:30:00.000Z`
- Cannot be in future
- Cannot be older than 24 hours

#### "Invalid flight_id"
**Requirements**:
- Must be valid UUID v4
- Format: `550e8400-e29b-41d4-a716-446655440000`
- Same for all points in a flight
- New flight = new UUID

### Connection Issues

#### MQTT Specific
```bash
# Test MQTT broker is reachable
mosquitto_pub -h dg-mqtt.hikeandfly.app -p 8883 \
  --cafile ca.crt \
  -u test -P test \
  -t test -m "test" -d

# Common issues:
# - Port 8883 blocked by firewall
# - CA certificate missing or invalid
# - TLS version mismatch (use TLS 1.2+)
```

#### HTTP API Specific
```bash
# Test API endpoint
curl -X GET https://dg-dev.hikeandfly.app/api/v1/health

# Test with your API key
curl -X GET https://dg-dev.hikeandfly.app/api/v1/devices \
  -H "X-API-Key: hfss_YOUR_API_KEY"
```

### Points Not Appearing

#### Check Processing Delay
- Batch processing occurs every 10-15 seconds
- High load may cause delays up to 1 minute
- Check API logs for errors

#### Verify Data Format
```python
# Correct format for single point
{
    "device_id": "TEST-001",
    "flight_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-07-11T21:30:00.000Z",
    "latitude": 45.9237,
    "longitude": 6.8694,
    "altitude": 2400.0
}
```

#### Debug Steps
1. Check device registration succeeded
2. Verify MQTT message published (check return code)
3. Monitor MQTT broker logs
4. Check API processing logs
5. Query database directly

## Support

For manufacturer support:
- Integration issues: Check `/tmp/device_*.json` for credentials
- API documentation: See `docs/API_REFERENCE.md`
- System architecture: See `docs/SYSTEM_ARCHITECTURE.md`