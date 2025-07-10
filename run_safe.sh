#!/bin/bash
# Safe wrapper script for running the Paraglider Emulator
# Performs system checks before starting the emulator

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DEVICES=10
DURATION=60
DOMAIN="localhost"
MANUFACTURER="DIGIFLY"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--devices)
            DEVICES="$2"
            shift 2
            ;;
        -t|--duration)
            DURATION="$2"
            shift 2
            ;;
        -h|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -m|--manufacturer)
            MANUFACTURER="$2"
            shift 2
            ;;
        --help)
            echo "Safe Paraglider Emulator Runner"
            echo ""
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -d, --devices NUM      Number of devices to simulate (default: 10)"
            echo "  -t, --duration MIN     Duration in minutes (default: 60)"
            echo "  -h, --domain HOST      Server domain (default: localhost)"
            echo "  -m, --manufacturer NAME Manufacturer name (default: DIGIFLY)"
            echo "  --help                 Show this help message"
            echo ""
            echo "This script performs safety checks before running the emulator:"
            echo "  - Checks if emulator is already running"
            echo "  - Verifies system resources"
            echo "  - Ensures Python dependencies are installed"
            echo "  - Validates certificates exist"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "🛡️  Safe Paraglider Emulator Runner"
echo "===================================="

# Check if emulator is already running
echo -n "Checking for running instances... "
if pgrep -f "paraglider_emulator.py" > /dev/null; then
    echo -e "${RED}FAILED${NC}"
    echo ""
    echo -e "${RED}ERROR: Paraglider emulator is already running!${NC}"
    echo "Running processes:"
    ps aux | grep -E "paraglider_emulator.py" | grep -v grep
    echo ""
    echo "To stop the running instance:"
    echo "  pkill -f paraglider_emulator.py"
    exit 1
else
    echo -e "${GREEN}OK${NC}"
fi

# Check lock file
LOCK_FILE="/tmp/paraglider_emulator.lock"
if [ -f "$LOCK_FILE" ]; then
    echo -e "${YELLOW}WARNING: Lock file exists at $LOCK_FILE${NC}"
    echo "This might be from a previous crashed instance."
    read -p "Remove lock file and continue? (y/N): " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -f "$LOCK_FILE"
        echo "Lock file removed."
    else
        echo "Aborted."
        exit 1
    fi
fi

# Check system load
echo -n "Checking system load... "
if command -v uptime >/dev/null 2>&1; then
    LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk -F, '{print $1}' | xargs)
    LOAD_INT=$(echo "$LOAD" | cut -d. -f1)
    
    if [ "$LOAD_INT" -gt 4 ]; then
        echo -e "${RED}HIGH${NC}"
        echo -e "${YELLOW}WARNING: System load is high: $LOAD${NC}"
        read -p "Continue anyway? (y/N): " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "Aborted."
            exit 1
        fi
    else
        echo -e "${GREEN}OK${NC} (load: $LOAD)"
    fi
else
    echo -e "${YELLOW}SKIP${NC} (uptime command not found)"
fi

# Check Python
echo -n "Checking Python installation... "
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}FAILED${NC}"
    echo "Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
else
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}OK${NC} (version: $PYTHON_VERSION)"
fi

# Check dependencies
echo -n "Checking Python dependencies... "
MISSING_DEPS=()
for dep in "paho.mqtt.client" "requests" "dotenv"; do
    if ! python3 -c "import $dep" 2>/dev/null; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}MISSING${NC}"
    echo "Missing dependencies: ${MISSING_DEPS[*]}"
    echo ""
    echo "Please run: python3 setup.py"
    exit 1
else
    echo -e "${GREEN}OK${NC}"
fi

# Check certificates
echo -n "Checking certificates... "
CERT_DIR="certs"
if [ ! -f "$CERT_DIR/ca.crt" ] || [ ! -f "$CERT_DIR/client.crt" ] || [ ! -f "$CERT_DIR/client.key" ]; then
    echo -e "${YELLOW}MISSING${NC}"
    echo ""
    echo "Certificates not found. Generating test certificates..."
    if python3 generate_certs.py; then
        echo -e "${GREEN}Certificates generated successfully${NC}"
    else
        echo -e "${RED}Failed to generate certificates${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}OK${NC}"
fi

# Check manufacturer configuration
echo -n "Checking manufacturer configuration... "
ENV_VAR="MANUFACTURER_SECRET_${MANUFACTURER}"
if [ -z "${!ENV_VAR}" ]; then
    # Try to load from config
    if python3 -c "from config_manager import ConfigManager; m = ConfigManager(); m.get_manufacturer_config('$MANUFACTURER')" 2>/dev/null; then
        echo -e "${GREEN}OK${NC} (from saved config)"
    else
        echo -e "${YELLOW}NOT CONFIGURED${NC}"
        echo ""
        echo "Manufacturer $MANUFACTURER is not configured."
        echo "Running configuration setup..."
        python3 paraglider_emulator.py --config --manufacturer "$MANUFACTURER"
        if [ $? -ne 0 ]; then
            echo -e "${RED}Configuration failed${NC}"
            exit 1
        fi
    fi
else
    echo -e "${GREEN}OK${NC} (from environment)"
fi

# Display configuration
echo ""
echo "📋 Configuration Summary"
echo "========================"
echo "Manufacturer: $MANUFACTURER"
echo "Devices:      $DEVICES"
echo "Duration:     $DURATION minutes"
echo "Domain:       $DOMAIN"
echo "Safe Mode:    ON (5-second updates, rate limiting enabled)"
echo ""

# Confirm before starting
read -p "Start emulator with these settings? (Y/n): " response
if [[ "$response" =~ ^[Nn]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Create log directory
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/emulator_$(date +%Y%m%d_%H%M%S).log"

echo ""
echo "🚀 Starting Paraglider Emulator..."
echo "Log file: $LOG_FILE"
echo ""

# Run the emulator with safe settings
python3 paraglider_emulator.py \
    --devices "$DEVICES" \
    --duration "$DURATION" \
    --domain "$DOMAIN" \
    --manufacturer "$MANUFACTURER" \
    2>&1 | tee "$LOG_FILE"

# Check exit code
EXIT_CODE=${PIPESTATUS[0]}
if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Emulator completed successfully${NC}"
else
    echo ""
    echo -e "${RED}❌ Emulator exited with code $EXIT_CODE${NC}"
fi

exit $EXIT_CODE