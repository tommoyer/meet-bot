# Google Meet Bot Upgrade Guide

This guide covers how to upgrade the Google Meet Bot to new versions safely.

## Quick Upgrade

For most upgrades, use the automated upgrade script:

```bash
# Copy new files to a directory and run upgrade
sudo bash upgrade.sh upgrade /path/to/new/files

# Or upgrade from current directory
sudo bash upgrade.sh upgrade
```

## Upgrade Process

The upgrade script performs these steps automatically:

1. **Pre-flight Check** - Validates system state
2. **Backup Creation** - Creates timestamped backup
3. **Service Stop** - Safely stops the running service
4. **File Installation** - Copies new application files
5. **Dependency Update** - Updates Python packages
6. **Service Start** - Starts the updated service
7. **Health Check** - Verifies the service is working
8. **Cleanup** - Removes old backups (keeps 5 most recent)

## Manual Upgrade Steps

If you prefer to upgrade manually:

### 1. Create Backup

```bash
sudo bash upgrade.sh backup
```

### 2. Stop Service

```bash
sudo systemctl stop meet-bot
```

### 3. Update Files

```bash
# Copy new application files
sudo cp main.py /opt/meet-bot/
sudo cp requirements.txt /opt/meet-bot/

# Update systemd service if changed
sudo cp meet-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

# Set correct ownership
sudo chown -R meet-bot:meet-bot /opt/meet-bot/
```

### 4. Update Dependencies

```bash
sudo -u meet-bot /opt/meet-bot/venv/bin/pip install -r /opt/meet-bot/requirements.txt
```

### 5. Start Service

```bash
sudo systemctl start meet-bot
sudo systemctl status meet-bot
```

## Rollback

If something goes wrong, rollback to the previous version:

```bash
sudo bash upgrade.sh rollback
```

## Pre-Upgrade Checklist

Before upgrading, ensure:

- [ ] Service is currently running properly
- [ ] You have sufficient disk space (100MB+)
- [ ] No active meetings are being created
- [ ] You have tested the new version in a development environment

Run the pre-upgrade check:

```bash
sudo bash pre-upgrade-check.sh
```

## Upgrade Scripts

### Main Upgrade Script (`upgrade.sh`)

Full-featured upgrade script with backup, rollback, and safety checks.

**Commands:**
- `upgrade [path]` - Upgrade from specified directory
- `rollback` - Rollback to previous version
- `status` - Show current status and version
- `backup` - Create backup only
- `clean` - Clean old backups

### Quick Upgrade Script (`quick-upgrade.sh`)

Downloads and upgrades from remote sources.

```bash
# Upgrade from Git repository
sudo bash quick-upgrade.sh https://github.com/user/meet-bot.git

# Upgrade from ZIP file
sudo bash quick-upgrade.sh https://example.com/meet-bot.zip
```

### Pre-Upgrade Check (`pre-upgrade-check.sh`)

Validates system state before upgrade.

## Version Management

### Version File

Each installation includes a `VERSION` file:

```bash
# Check current version
cat /opt/meet-bot/VERSION

# Version format: YYYY.MM.DD
# Example: 2025.05.27
```

### Version History

Backups include version information and can be used to track changes:

```bash
# List all backups
ls -la /opt/meet-bot-backups/

# View backup info
cat /opt/meet-bot-backups/meet-bot_backup_YYYY-MM-DD_HH-MM-SS/backup_info.txt
```

## Backup Management

### Automatic Backups

- Created before each upgrade
- Stored in `/opt/meet-bot-backups/`
- Include application files, systemd service, and configuration templates
- Exclude sensitive credentials for security
- Automatically cleaned (keeps 5 most recent)

### Manual Backup

```bash
# Create backup
sudo bash upgrade.sh backup

# Restore from specific backup
sudo cp -r /opt/meet-bot-backups/backup_name/app /opt/meet-bot
sudo systemctl restart meet-bot
```

### Backup Contents

Each backup includes:
- Application files (`main.py`, `requirements.txt`, etc.)
- Systemd service file
- Configuration templates (not credentials)
- Version information
- Backup metadata

## Troubleshooting Upgrades

### Service Won't Start

```bash
# Check service status
sudo systemctl status meet-bot

# Check logs
sudo journalctl -u meet-bot -n 50

# Check configuration
sudo bash pre-upgrade-check.sh
```

### Python Dependency Issues

```bash
# Reinstall virtual environment
sudo rm -rf /opt/meet-bot/venv
sudo -u meet-bot python3 -m venv /opt/meet-bot/venv
sudo -u meet-bot /opt/meet-bot/venv/bin/pip install -r /opt/meet-bot/requirements.txt
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R meet-bot:meet-bot /opt/meet-bot/
sudo chown -R root:meet-bot /etc/meet-bot/
sudo chown -R meet-bot:meet-bot /var/log/meet-bot/

# Fix permissions
sudo chmod 755 /opt/meet-bot/
sudo chmod 750 /etc/meet-bot/
sudo chmod 755 /var/log/meet-bot/
```

### Configuration Issues

```bash
# Verify Google credentials
sudo ls -la /etc/meet-bot/

# Test Google API access
sudo -u meet-bot /opt/meet-bot/venv/bin/python -c "
from google.oauth2.service_account import Credentials
creds = Credentials.from_service_account_file('/etc/meet-bot/service-account.json')
print('Credentials loaded successfully')
"
```

## Best Practices

1. **Test First** - Test upgrades in a development environment
2. **Schedule Downtime** - Inform users about maintenance windows
3. **Monitor After Upgrade** - Watch logs and health checks post-upgrade
4. **Keep Backups** - Don't delete backups immediately after upgrade
5. **Document Changes** - Keep notes about configuration changes
6. **Health Checks** - Always verify the service is working after upgrade

## Emergency Procedures

### Immediate Rollback

If the service fails immediately after upgrade:

```bash
sudo bash upgrade.sh rollback
```

### Manual Emergency Recovery

If upgrade script fails:

1. Stop the service: `sudo systemctl stop meet-bot`
2. Restore from backup: `sudo cp -r /opt/meet-bot-backups/latest_backup/app /opt/meet-bot`
3. Restore service file: `sudo cp /opt/meet-bot-backups/latest_backup/systemd/meet-bot.service /etc/systemd/system/`
4. Reload and start: `sudo systemctl daemon-reload && sudo systemctl start meet-bot`

### Contact and Support

For upgrade issues:
1. Check logs: `sudo journalctl -u meet-bot -f`
2. Run health check: `curl http://localhost:8080/health`
3. Verify Google API access
4. Check Mattermost integration