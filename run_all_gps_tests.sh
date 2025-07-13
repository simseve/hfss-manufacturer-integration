#!/bin/bash
# Run all 4 GPS endpoint tests against PRODUCTION
# Usage: ./run_all_gps_tests.sh

set -e

echo "=== Testing All 4 GPS Endpoints (PRODUCTION) ==="
echo "==============================================="
echo

# Change to script directory
cd "$(dirname "$0")"

# Production settings for Digifly
API_URL="https://dg-dev.hikeandfly.app/api/v1"
MQTT_HOST="dg-mqtt.hikeandfly.app"
MANUFACTURER_SECRET="GziZ46Tr4ANkhKh75lFnPtOrTkLgfHWe"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔗 Production Endpoints:"
echo "   API: $API_URL"
echo "   MQTT: $MQTT_HOST:8883"
echo

echo -e "${BLUE}1. Testing MQTT Single GPS Point${NC}"
echo "---------------------------------"
python3 scripts/manufacturer_device_test.py \
    --api-url "$API_URL" \
    --mqtt-host "$MQTT_HOST" \
    --device-id MQTT-TEST-$(date +%s) \
    --manufacturer-secret "$MANUFACTURER_SECRET" \
    --num-messages 1
echo

echo -e "${BLUE}2. Testing MQTT Batch GPS Points${NC}"
echo "--------------------------------"
python3 scripts/manufacturer_device_test.py \
    --api-url "$API_URL" \
    --mqtt-host "$MQTT_HOST" \
    --device-id MQTT-BATCH-$(date +%s) \
    --manufacturer-secret "$MANUFACTURER_SECRET" \
    --batch-mode \
    --batch-size 5 \
    --num-batches 1
echo

echo -e "${BLUE}3. Testing HTTP Single GPS Point${NC}"
echo "--------------------------------"
python3 scripts/manufacturer_device_test.py \
    --api-url "$API_URL" \
    --mqtt-host "$MQTT_HOST" \
    --device-id HTTP-TEST-$(date +%s) \
    --manufacturer-secret "$MANUFACTURER_SECRET" \
    --num-messages 1
echo

echo -e "${BLUE}4. Testing HTTP Batch GPS Points${NC}"
echo "--------------------------------"
python3 scripts/manufacturer_device_test.py \
    --api-url "$API_URL" \
    --mqtt-host "$MQTT_HOST" \
    --device-id HTTP-BATCH-$(date +%s) \
    --manufacturer-secret "$MANUFACTURER_SECRET" \
    --test-http-batch
echo

echo -e "${GREEN}=== All Tests Complete ===${NC}"
echo "=========================="
echo
echo "✅ If all tests passed, your integration is working correctly!"
echo "📁 Device configs saved in /tmp/device_*_complete.json"