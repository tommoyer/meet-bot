# Google Meet Bot for Mattermost

A standalone Python application that integrates Google Meet API with Mattermost slash commands, designed to run on your Mattermost server.

## Features

- 🎥 Create Google Meet links instantly via Mattermost slash commands
- ⚡ Quick meeting shortcut for 30-minute meetings
- 🔧 Configurable meeting titles and durations
- 🔐 Secure Google API authentication (Service Account or OAuth2)
- 📊 Health check endpoint for monitoring
- 🚀 Systemd service for automatic startup and management
- 📝 Comprehensive logging and error handling

## Quick Start

### 1. Installation

```bash
# Download all files to a directory
# Make install script executable
chmod +x install.sh

# Run installation (requires sudo)
sudo ./install.sh
```

### 2. Google API Setup

```bash
# Run the authentication setup script
sudo python3 setup-google-auth.py
```

Follow the prompts to set up either:
- **Service Account** (recommended for production)
- **OAuth2** (for development/testing)

### 3. Configure Mattermost Token

Edit the systemd service to add your Mattermost slash command token:

```bash
sudo systemctl edit meet-bot
```

Add the following content:

```ini
[Service]
Environment=MATTERMOST_TOKEN=your_actual_mattermost_token_here
```

### 4. Start the Service

```bash
# Enable auto-start on boot
sudo systemctl enable meet-bot

# Start the service
sudo systemctl start meet-bot

# Check status
sudo systemctl status meet-bot
```

## Mattermost Integration

### Setting up Slash Commands

1. Go to **System Console** > **Integrations** > **Slash Commands**
2. Create a new slash command:
   - **Command Trigger Word**: `meet`
   - **Request URL**: `http://your-server:8080/meet`
   - **Request Method**: POST
   - **Response Username**: Meet Bot
   - **Auto Complete**: Yes
   - **Auto Complete Hint**: `[title="Meeting Name"] [duration=60] [quick]`

3. Optional: Create a help command:
   - **Command Trigger Word**: `meet-help`
   - **Request URL**: `http://your-server:8080/meet-help`
   - **Request Method**: POST

### Usage Examples

```bash
# Quick meeting (30 minutes)
/meet quick

# Default meeting (60 minutes, auto-generated title)
/meet

# Custom title
/meet title="Daily Standup"

# Custom title and duration
/meet title="Client Call" duration=30

# Using text as title (legacy format)
/meet Weekly Team Review

# Show help
/meet-help
```

## Configuration

### Environment Variables

The service supports these environment variables (set in systemd service):

```bash
PORT=8080                                           # Server port
HOST=0.0.0.0                                       # Server host
MATTERMOST_TOKEN=your_token                        # Mattermost verification token
GOOGLE_SERVICE_ACCOUNT_FILE=/etc/meet-bot/service-account.json
DEBUG=false                                        # Enable debug logging
```

### File Locations

- **Application**: `/opt/meet-bot/`
- **Configuration**: `/etc/meet-bot/`
- **Logs**: `/var/log/meet-bot/`
- **Service**: `/etc/systemd/system/meet-bot.service`

## Management

### Service Management

```bash
# Start/stop/restart
sudo systemctl start meet-bot
sudo systemctl stop meet-bot
sudo systemctl restart meet-bot

# Enable/disable auto-start
sudo systemctl enable meet-bot
sudo systemctl disable meet-bot

# Check status
sudo systemctl status meet-bot
```

### Monitoring

```bash
# View live logs
sudo journalctl -u meet-bot -f

# View recent logs
sudo journalctl -u meet-bot -n 100

# Health check
curl http://localhost:8080/health
```

### Log Management

Logs are automatically rotated daily and kept for 52 weeks. Manual log viewing:

```bash
# Application logs
sudo tail -f /var/log/meet-bot/meet-bot.log

# System logs
sudo journalctl -u meet-bot -f
```

## Google API Setup Details

### Service Account (Recommended)

1. **Create Project**: Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **Enable APIs**: Enable Google Meet API and Google Calendar API
3. **Create Service Account**:
   - Go to IAM & Admin > Service Accounts
   - Create new service account
   - Download JSON key file
4. **Share Calendar**: Share your Google Calendar with the service account email
5. **Install Credentials**: Use `setup-google-auth.py` script

### Required Google API Scopes

- `https://www.googleapis.com/auth/meetings.space.created`
- `https://www.googleapis.com/auth/calendar`

## Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   sudo journalctl -u meet-bot -n 50
   ```

2. **Google API errors**:
   - Check credentials file permissions: `ls -la /etc/meet-bot/`
   - Verify APIs are enabled in Google Cloud Console
   - Check service account calendar sharing

3. **Mattermost integration issues**:
   - Verify token configuration
   - Check Mattermost slash command URL
   - Test with `curl`:
     ```bash
     curl -X POST http://localhost:8080/health
     ```

### Debug Mode

Enable debug logging:

```bash
sudo systemctl edit meet-bot
```

Add:
```ini
[Service]
Environment=DEBUG=true
```

Then restart:
```bash
sudo systemctl restart meet-bot
```

## Security Considerations

- Service runs as dedicated `meet-bot` user with minimal privileges
- Credentials stored in `/etc/meet-bot/` with restricted permissions (640)
- Systemd security hardening enabled
- Log files protected with appropriate permissions
- Mattermost token verification for slash commands

## Updating

To update the application:

1. Replace the Python files in `/opt/meet-bot/`
2. Install any new dependencies
3. Restart the service:

```bash
sudo systemctl restart meet-bot
```

## Uninstallation

```bash
# Stop and disable service
sudo systemctl stop meet-bot
sudo systemctl disable meet-bot

# Remove files
sudo rm /etc/systemd/system/meet-bot.service
sudo rm -rf /opt/meet-bot
sudo rm -rf /etc/meet-bot
sudo rm -rf /var/log/meet-bot
sudo rm /etc/logrotate.d/meet-bot

# Remove user
sudo userdel meet-bot

# Reload systemd
sudo systemctl daemon-reload
```