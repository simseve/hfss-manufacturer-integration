# Manufacturer Device Test Script Manual

## Overview

The `manufacturer_device_test.py` script simulates the complete lifecycle of a GPS tracking device, from factory provisioning to sending GPS data. It supports both individual message sending and batch mode for power-efficient operations.

## Features

- **Complete Device Lifecycle**: Factory provisioning → Registration → MQTT connection → GPS transmission
- **Batch Mode**: Send multiple GPS points in a single message (power-efficient)
- **Flight Sessions**: Automatic flight_id generation and tracking
- **Reusable Configurations**: Save and reuse device credentials for multiple flights
- **HTTP & MQTT Support**: Test both batch APIs

## Quick Start

### 1. Basic Test (Individual Messages)

```bash
python manufacturer_device_test.py \
    --manufacturer-secret YOUR_SECRET \
    --device-num 1
```

### 2. Batch Mode Test

```bash
python manufacturer_device_test.py \
    --manufacturer-secret YOUR_SECRET \
    --device-id BATCH-001 \
    --batch-mode \
    --batch-size 30 \
    --num-batches 3
```

### 3. Reuse Existing Device

```bash
# First flight creates the device
python manufacturer_device_test.py \
    --manufacturer-secret YOUR_SECRET \
    --device-id PARA-001

# Subsequent flights reuse the config
python manufacturer_device_test.py \
    --config-file /tmp/device_PARA-001_complete.json \
    --batch-mode
```

## Command Line Options

### Connection Settings
- `--api-url URL` - API base URL (default: http://localhost/api/v1)
- `--mqtt-host HOST` - MQTT broker hostname (default: localhost)
- `--mqtt-port PORT` - MQTT broker port (default: 8883)
- `--ca-cert PATH` - Path to CA certificate for MQTT TLS

### Device Configuration
- `--manufacturer-secret SECRET` - Manufacturer secret for provisioning (required for new devices)
- `--device-id ID` - Specific device ID to use (optional, auto-generated if not provided)
- `--device-num NUM` - Device number for ID generation (default: 1)
- `--config-file PATH` - Use existing device configuration file

### GPS Data Options
- `--batch-mode` - Send GPS data in batches instead of individual messages
- `--batch-size N` - Number of GPS points per batch (default: 10)
- `--num-batches N` - Number of batches to send (default: 3)
- `--num-messages N` - Number of individual messages to send (default: 10)
- `--test-http-batch` - Also test HTTP batch API endpoint

## Usage Examples

### Example 1: Power-Efficient Device (30-second batches)

```bash
# Simulate device that collects GPS every second but sends every 30 seconds
python manufacturer_device_test.py \
    --manufacturer-secret GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe \
    --device-id POWER-SAVER-001 \
    --batch-mode \
    --batch-size 30 \
    --num-batches 5
```

### Example 2: Multiple Flights Same Device

```bash
# Flight 1
python manufacturer_device_test.py \
    --manufacturer-secret GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe \
    --device-id PARA-MULTI-001

# Flight 2 (reuse device)
python manufacturer_device_test.py \
    --config-file /tmp/device_PARA-MULTI-001_complete.json \
    --num-messages 20

# Flight 3 (batch mode)
python manufacturer_device_test.py \
    --config-file /tmp/device_PARA-MULTI-001_complete.json \
    --batch-mode \
    --batch-size 15
```

### Example 3: Test Both MQTT and HTTP Batch

```bash
python manufacturer_device_test.py \
    --manufacturer-secret GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe \
    --device-id TEST-BOTH-001 \
    --batch-mode \
    --test-http-batch
```

## Output Files

The script creates several files:

1. **Factory Config**: `/tmp/device_config_{num}.json`
   - Basic device credentials (before registration)

2. **Complete Config**: `/tmp/device_{device_id}_complete.json`
   - Full credentials including API key and MQTT credentials
   - Can be reused with `--config-file`

3. **CA Certificate**: `/tmp/mqtt_ca.crt`
   - Downloaded from server for MQTT TLS

## Batch Mode Details

### Message Format

Individual message:
```json
{
    "data": {
        "device_id": "PARA-001",
        "flight_id": "uuid",
        "latitude": 45.123,
        "longitude": 6.789,
        ...
    },
    "signature": "hmac_signature",
    "api_key": "gps_xxxxx"
}
```

Batch message:
```json
{
    "data": [
        {"device_id": "PARA-001", "flight_id": "uuid", ...},
        {"device_id": "PARA-001", "flight_id": "uuid", ...},
        // up to batch_size points
    ],
    "signature": "hmac_signature",
    "api_key": "gps_xxxxx"
}
```

### Power Savings

Batch mode significantly reduces power consumption:
- **Individual**: 30 MQTT publishes = 30 TCP operations
- **Batch**: 1 MQTT publish = 1 TCP operation
- **Savings**: ~90% reduction in network overhead

## Troubleshooting

### MQTT Connection Failed
- Check MQTT broker is running: `docker ps | grep mqtt`
- Verify CA certificate exists: `ls /tmp/mqtt_ca.crt`
- Check MQTT credentials in device config file

### Registration Failed
- Verify manufacturer secret is correct
- Check API is running: `curl http://localhost/health`
- Ensure device ID is unique

### Batch Too Large
- Keep batch size under 100 points
- Typical MQTT message limit is 256KB
- 30-50 points is optimal for most use cases

### HTTP Batch Returns 401
- Note: HTTP batch API currently expects different API key format
- Use MQTT batch for now (recommended anyway)

## Performance Tips

1. **Optimal Batch Size**: 30-50 points balances efficiency and latency
2. **Collection Interval**: 1-second GPS updates, 30-second sends
3. **Memory Usage**: Each point ≈ 100 bytes, 30 points ≈ 3KB
4. **Network Efficiency**: Batch mode uses 90% less bandwidth

## Integration with Your Device

To integrate batch sending in your ESP32/embedded device:

1. Collect GPS points in a circular buffer
2. When buffer reaches threshold OR timeout occurs:
   - Create JSON array of all points
   - Calculate HMAC signature
   - Send via MQTT publish
   - Clear buffer

See `ESP32_MANUFACTURER_GUIDE.md` for complete implementation example.