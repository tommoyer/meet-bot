#!/bin/bash

set -e

SERVICE_NAME="meet-bot"
SERVICE_FILE="/etc/systemd/system/meet-bot.service"
SERVICE_FILE_SRC="./meet-bot.service"

echo "Stopping $SERVICE_NAME service..."
sudo systemctl stop $SERVICE_NAME

echo "Pulling latest code..."
git pull

echo "Upgrading Python dependencies (if requirements.txt exists)..."
if [ -f requirements.txt ]; then
    pip install --upgrade -r requirements.txt
fi

echo "Copying meet-bot.service to $SERVICE_FILE..."
if [ -f "$SERVICE_FILE_SRC" ]; then
    sudo cp "$SERVICE_FILE_SRC" "$SERVICE_FILE"
    sudo systemctl daemon-reload
    echo "meet-bot.service updated."
else
    echo "Warning: $SERVICE_FILE_SRC not found, skipping service file update."
fi

echo "Restarting $SERVICE_NAME service..."
sudo systemctl start $SERVICE_NAME

echo "Done. $SERVICE_NAME has been upgraded and restarted."