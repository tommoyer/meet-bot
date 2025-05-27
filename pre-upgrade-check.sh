#!/bin/bash

# Pre-upgrade system check script
# Validates system state before upgrade

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVICE_NAME="meet-bot"
APP_DIR="/opt/meet-bot"
CONFIG_DIR="/etc/meet-bot"

echo -e "${GREEN}Pre-Upgrade System Check${NC}"
echo "========================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}✗ Must run as root${NC}"
   exit 1
else
   echo -e "${GREEN}✓ Running as root${NC}"
fi

# Check service exists
if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
    echo -e "${GREEN}✓ Service exists${NC}"
else
    echo -e "${RED}✗ Service not found${NC}"
    exit 1
fi

# Check application directory
if [[ -d "$APP_DIR" ]]; then
    echo -e "${GREEN}✓ Application directory exists${NC}"
else
    echo -e "${RED}✗ Application directory missing${NC}"
    exit 1
fi

# Check virtual environment
if [[ -f "$APP_DIR/venv/bin/python" ]]; then
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment missing${NC}"
fi

# Check credentials
if [[ -f "$CONFIG_DIR/service-account.json" ]]; then
    echo -e "${GREEN}✓ Service account credentials found${NC}"
else
    echo -e "${YELLOW}⚠ Service account credentials missing${NC}"
fi

# Check disk space (need at least 100MB)
available_space=$(df /opt | awk 'NR==2 {print $4}')
if [[ $available_space -gt 102400 ]]; then
    echo -e "${GREEN}✓ Sufficient disk space${NC}"
else
    echo -e "${RED}✗ Insufficient disk space (need 100MB)${NC}"
    exit 1
fi

# Check if service is responding
if curl -f -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Service is responding${NC}"
else
    echo -e "${YELLOW}⚠ Service not responding${NC}"
fi

# Check current version
if [[ -f "$APP_DIR/VERSION" ]]; then
    current_version=$(cat "$APP_DIR/VERSION")
    echo -e "${GREEN}✓ Current version: $current_version${NC}"
else
    echo -e "${YELLOW}⚠ Version file missing${NC}"
fi

echo ""
echo -e "${GREEN}Pre-upgrade check completed successfully!${NC}"
echo "System is ready for upgrade."