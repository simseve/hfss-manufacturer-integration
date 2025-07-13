# GPS Integration Cheat Sheet

## Test Commands

```bash
# Run all tests
./scripts/run_all_gps_tests.sh

# Test specific device
python scripts/manufacturer_device_test.py --device-id MY-DEVICE-001 --num-messages 5
```

## Required GPS Fields

```json
{
  "device_id": "YOUR-DEVICE-001",        // Required
  "flight_id": "uuid-v4-format",         // Required (new flight = new UUID)
  "timestamp": "2025-07-11T21:30:00Z",   // Required (UTC)
  "latitude": 45.9237,                   // Required (-90 to 90)
  "longitude": 6.8694,                   // Required (-180 to 180)
  "altitude": 2400.0,                    // Optional (meters)
  "speed": 35.5,                         // Optional (km/h)
  "battery_level": 85.0                  // Optional (0-100%)
}
```

## Connection Info

**MQTT**: `localhost:8883` (TLS required)  
**HTTP**: `http://localhost/api/v1/gps/`  
**Auth**: Device-specific credentials from registration  
**CA Certificate**: `http://localhost/ca.crt` (auto-downloaded by scripts)

## Message Flow

1. **Register** → Get credentials
2. **Connect** → MQTT or HTTP
3. **Send GPS** → With HMAC signature
4. **Verify** → Check database

## Quick Debug

```bash
# Check if data arrived
docker compose exec timescaledb psql -U gps_prod_user -d gps_tracking_production -c \
  "SELECT * FROM gps_data WHERE device_id = 'YOUR-DEVICE' ORDER BY timestamp DESC LIMIT 5"

# Check logs
docker compose logs api1 api2 | grep YOUR-DEVICE
```