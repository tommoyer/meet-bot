#!/bin/bash

# Google Meet Bot Installation Script
# Run with sudo: sudo bash install.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Installing Google Meet Bot for Mattermost...${NC}"

# Create user and group
echo -e "${YELLOW}Creating meet-bot user...${NC}"
if ! id "meet-bot" &>/dev/null; then
    useradd --system --shell /bin/false --home-dir /opt/meet-bot --create-home meet-bot
    echo -e "${GREEN}Created meet-bot user${NC}"
else
    echo -e "${YELLOW}User meet-bot already exists${NC}"
fi

# Create directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p /opt/meet-bot
mkdir -p /etc/meet-bot
mkdir -p /var/log/meet-bot

# Set ownership
chown -R meet-bot:meet-bot /opt/meet-bot
chown -R meet-bot:meet-bot /var/log/meet-bot
chown -R root:meet-bot /etc/meet-bot
chmod 750 /etc/meet-bot

# Copy application files
echo -e "${YELLOW}Copying application files...${NC}"
cp main.py /opt/meet-bot/
cp requirements.txt /opt/meet-bot/
chown meet-bot:meet-bot /opt/meet-bot/main.py /opt/meet-bot/requirements.txt

# Install Python and pip if not present
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 is not installed. Please install Python 3.8+ first.${NC}"
    exit 1
fi

if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}Installing pip...${NC}"
    apt-get update
    apt-get install -y python3-pip python3-venv
fi

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
cd /opt/meet-bot
sudo -u meet-bot python3 -m venv venv
sudo -u meet-bot /opt/meet-bot/venv/bin/pip install --upgrade pip
sudo -u meet-bot /opt/meet-bot/venv/bin/pip install -r requirements.txt

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
cp meet-bot.service /etc/systemd/system/
systemctl daemon-reload

# Create log rotation config
echo -e "${YELLOW}Setting up log rotation...${NC}"
cat > /etc/logrotate.d/meet-bot << EOF
/var/log/meet-bot/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 meet-bot meet-bot
    postrotate
        systemctl reload meet-bot || true
    endscript
}
EOF

# Create configuration template
echo -e "${YELLOW}Creating configuration template...${NC}"
cat > /etc/meet-bot/config.env.template << EOF
# Mattermost Configuration
MATTERMOST_TOKEN=your_mattermost_slash_command_token_here

# Google API Configuration
GOOGLE_SERVICE_ACCOUNT_FILE=/etc/meet-bot/service-account.json

# Server Configuration
PORT=8080
HOST=0.0.0.0
DEBUG=false
EOF

chown root:meet-bot /etc/meet-bot/config.env.template
chmod 640 /etc/meet-bot/config.env.template

echo -e "${GREEN}Installation completed!${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Place your Google service account JSON file at: /etc/meet-bot/service-account.json"
echo "2. Edit the systemd service file to add your Mattermost token:"
echo "   sudo systemctl edit meet-bot"
echo "3. Enable and start the service:"
echo "   sudo systemctl enable meet-bot"
echo "   sudo systemctl start meet-bot"
echo "4. Check service status:"
echo "   sudo systemctl status meet-bot"
echo "5. View logs:"
echo "   sudo journalctl -u meet-bot -f"
echo
echo -e "${GREEN}The service will be available at: http://localhost:8080${NC}"