# TLS Certificate Information

## CA Certificate Endpoint

The platform provides a CA certificate for MQTT TLS connections at:

```
http://your-server/ca.crt
```

For local testing:
```
http://localhost/ca.crt
```

## Automatic Download

Our test scripts automatically download this certificate:

```python
# The script does this for you:
response = requests.get("http://localhost/ca.crt")
with open("/tmp/mqtt_ca.crt", "wb") as f:
    f.write(response.content)
```

## Manual Download

If you need to download it manually:

```bash
# Using curl
curl -o ca.crt http://localhost/ca.crt

# Using wget
wget http://localhost/ca.crt
```

## Using the Certificate

### MQTT Connection (Python)
```python
import paho.mqtt.client as mqtt
import ssl

client = mqtt.Client()
client.tls_set(ca_certs="/path/to/ca.crt")
client.connect("localhost", 8883)
```

### MQTT Connection (mosquitto_pub)
```bash
mosquitto_pub -h localhost -p 8883 \
  --cafile ca.crt \
  -u device_YOUR-DEVICE-ID \
  -P your_mqtt_password \
  -t gps/YOUR-DEVICE-ID/data \
  -m '{"your":"gps_data"}'
```

## Certificate Details

- **Format**: PEM encoded X.509 certificate
- **Purpose**: Verify MQTT broker identity
- **Required for**: All MQTT connections (port 8883)
- **Not required for**: HTTP API connections

## Troubleshooting

### Certificate Download Fails
- Check if the server is running
- Verify the URL is correct
- Try accessing in a browser first

### MQTT Connection Fails
- Ensure you're using port 8883 (not 1883)
- Verify certificate path is correct
- Check certificate hasn't expired

### Certificate Verification Error
- Download a fresh copy of the certificate
- Ensure system time is correct
- Check certificate hasn't been corrupted