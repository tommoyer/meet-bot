#!/bin/bash

# Google Meet Bot Upgrade Script
# Usage: sudo bash upgrade.sh [version|path_to_files]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="meet-bot"
APP_DIR="/opt/meet-bot"
CONFIG_DIR="/etc/meet-bot"
LOG_DIR="/var/log/meet-bot"
BACKUP_DIR="/opt/meet-bot-backups"
USER="meet-bot"
GROUP="meet-bot"

# Version info
SCRIPT_VERSION="1.0.0"
CURRENT_DATE=$(date '+%Y-%m-%d_%H-%M-%S')

echo -e "${GREEN}Google Meet Bot Upgrade Script v${SCRIPT_VERSION}${NC}"
echo -e "${GREEN}==========================================${NC}"
echo -e "Date: ${CURRENT_DATE}"
echo -e "User: $(whoami)"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Function to print step headers
print_step() {
    echo -e "\n${BLUE}▶ $1${NC}"
    echo "----------------------------------------"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warnings
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print errors
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to check service status
check_service_status() {
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "running"
    else
        echo "stopped"
    fi
}

# Function to get current version
get_current_version() {
    if [[ -f "$APP_DIR/VERSION" ]]; then
        cat "$APP_DIR/VERSION"
    else
        echo "unknown"
    fi
}

# Function to create backup
create_backup() {
    print_step "Creating backup of current installation"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_NAME="${SERVICE_NAME}_backup_${CURRENT_DATE}"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"
    
    mkdir -p "$BACKUP_PATH"
    
    # Backup application files
    if [[ -d "$APP_DIR" ]]; then
        print_success "Backing up application directory..."
        cp -r "$APP_DIR" "$BACKUP_PATH/app"
    fi
    
    # Backup systemd service file
    if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
        print_success "Backing up systemd service file..."
        mkdir -p "$BACKUP_PATH/systemd"
        cp "/etc/systemd/system/${SERVICE_NAME}.service" "$BACKUP_PATH/systemd/"
    fi
    
    # Backup configuration (but not credentials for security)
    if [[ -d "$CONFIG_DIR" ]]; then
        print_success "Backing up configuration..."
        mkdir -p "$BACKUP_PATH/config"
        # Only backup non-sensitive files
        find "$CONFIG_DIR" -name "*.template" -o -name "*.env" -o -name "*.conf" | while read file; do
            if [[ -f "$file" ]]; then
                cp "$file" "$BACKUP_PATH/config/"
            fi
        done
    fi
    
    # Create backup info file
    cat > "$BACKUP_PATH/backup_info.txt" << EOF
Backup Created: $CURRENT_DATE
Service Name: $SERVICE_NAME
Previous Version: $(get_current_version)
Service Status: $(check_service_status)
Backup Path: $BACKUP_PATH
Created By: $(whoami)
EOF
    
    print_success "Backup created at: $BACKUP_PATH"
    echo "$BACKUP_PATH" > "/tmp/${SERVICE_NAME}_last_backup"
}

# Function to stop service safely
stop_service() {
    print_step "Stopping $SERVICE_NAME service"
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        systemctl stop $SERVICE_NAME
        
        # Wait for service to stop completely
        local timeout=30
        while systemctl is-active --quiet $SERVICE_NAME && [[ $timeout -gt 0 ]]; do
            sleep 1
            ((timeout--))
        done
        
        if systemctl is-active --quiet $SERVICE_NAME; then
            print_error "Service did not stop within 30 seconds"
            return 1
        else
            print_success "Service stopped successfully"
        fi
    else
        print_warning "Service was not running"
    fi
}

# Function to install new files
install_files() {
    local source_dir="$1"
    print_step "Installing new application files"
    
    # Validate source directory
    if [[ ! -d "$source_dir" ]]; then
        print_error "Source directory not found: $source_dir"
        return 1
    fi
    
    # Check for required files
    local required_files=("main.py" "requirements.txt")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$source_dir/$file" ]]; then
            print_error "Required file missing: $file"
            return 1
        fi
    done
    
    # Install Python files
    print_success "Installing Python application files..."
    cp "$source_dir/main.py" "$APP_DIR/"
    cp "$source_dir/requirements.txt" "$APP_DIR/"
    
    # Install VERSION file if it exists
    if [[ -f "$source_dir/VERSION" ]]; then
        cp "$source_dir/VERSION" "$APP_DIR/"
    else
        echo "$(date '+%Y.%m.%d')" > "$APP_DIR/VERSION"
    fi
    
    # Install systemd service file if it exists
    if [[ -f "$source_dir/${SERVICE_NAME}.service" ]]; then
        print_success "Installing systemd service file..."
        cp "$source_dir/${SERVICE_NAME}.service" "/etc/systemd/system/"
        systemctl daemon-reload
    fi
    
    # Set correct ownership
    chown -R $USER:$GROUP "$APP_DIR"
    chmod +x "$APP_DIR/main.py" 2>/dev/null || true
    
    print_success "Files installed successfully"
}

# Function to update dependencies
update_dependencies() {
    print_step "Updating Python dependencies"
    
    if [[ -f "$APP_DIR/requirements.txt" ]]; then
        print_success "Installing/updating Python packages..."
        sudo -u $USER "$APP_DIR/venv/bin/pip" install --upgrade pip
        sudo -u $USER "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"
        print_success "Dependencies updated successfully"
    else
        print_warning "No requirements.txt found, skipping dependency update"
    fi
}

# Function to start service
start_service() {
    print_step "Starting $SERVICE_NAME service"
    
    systemctl start $SERVICE_NAME
    
    # Wait for service to start
    local timeout=30
    while ! systemctl is-active --quiet $SERVICE_NAME && [[ $timeout -gt 0 ]]; do
        sleep 1
        ((timeout--))
    done
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        print_success "Service started successfully"
        
        # Test health endpoint
        sleep 5
        if curl -f -s http://localhost:8080/health > /dev/null 2>&1; then
            print_success "Health check passed"
        else
            print_warning "Health check failed - service may still be starting"
        fi
    else
        print_error "Service failed to start"
        return 1
    fi
}

# Function to show service status
show_status() {
    print_step "Service Status"
    
    echo "Service Status: $(check_service_status)"
    echo "Current Version: $(get_current_version)"
    echo ""
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "Recent logs:"
        journalctl -u $SERVICE_NAME --no-pager -n 10
    fi
}

# Function to rollback
rollback() {
    print_step "Rolling back to previous version"
    
    # Get last backup path
    if [[ -f "/tmp/${SERVICE_NAME}_last_backup" ]]; then
        local backup_path=$(cat "/tmp/${SERVICE_NAME}_last_backup")
        
        if [[ -d "$backup_path" ]]; then
            print_success "Found backup at: $backup_path"
            
            # Stop service
            stop_service
            
            # Restore files
            if [[ -d "$backup_path/app" ]]; then
                print_success "Restoring application files..."
                rm -rf "$APP_DIR"
                cp -r "$backup_path/app" "$APP_DIR"
                chown -R $USER:$GROUP "$APP_DIR"
            fi
            
            if [[ -f "$backup_path/systemd/${SERVICE_NAME}.service" ]]; then
                print_success "Restoring systemd service file..."
                cp "$backup_path/systemd/${SERVICE_NAME}.service" "/etc/systemd/system/"
                systemctl daemon-reload
            fi
            
            # Start service
            start_service
            
            print_success "Rollback completed successfully"
        else
            print_error "Backup directory not found: $backup_path"
            return 1
        fi
    else
        print_error "No backup information found"
        return 1
    fi
}

# Function to clean old backups
clean_backups() {
    print_step "Cleaning old backups"
    
    if [[ -d "$BACKUP_DIR" ]]; then
        # Keep only the 5 most recent backups
        local backup_count=$(ls -1 "$BACKUP_DIR" | wc -l)
        
        if [[ $backup_count -gt 5 ]]; then
            print_success "Removing old backups (keeping 5 most recent)..."
            ls -1t "$BACKUP_DIR" | tail -n +6 | while read backup; do
                rm -rf "$BACKUP_DIR/$backup"
                echo "Removed: $backup"
            done
        else
            print_success "No old backups to clean (found $backup_count backups)"
        fi
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: sudo bash upgrade.sh [COMMAND] [OPTIONS]

Commands:
    upgrade [path]     Upgrade to new version from specified path (default: current directory)
    rollback          Rollback to previous version
    status            Show current service status and version
    backup            Create backup only (no upgrade)
    clean             Clean old backups
    help              Show this help message

Examples:
    sudo bash upgrade.sh upgrade                    # Upgrade from current directory
    sudo bash upgrade.sh upgrade /path/to/files     # Upgrade from specific path
    sudo bash upgrade.sh rollback                   # Rollback to previous version
    sudo bash upgrade.sh status                     # Show status
    sudo bash upgrade.sh backup                     # Create backup only

EOF
}

# Main upgrade function
main_upgrade() {
    local source_dir="${1:-$(pwd)}"
    
    echo -e "Source directory: ${source_dir}"
    echo -e "Current version: $(get_current_version)"
    echo -e "Service status: $(check_service_status)"
    echo ""
    
    # Validate source directory
    if [[ ! -d "$source_dir" ]]; then
        print_error "Source directory does not exist: $source_dir"
        exit 1
    fi
    
    # Check for required files
    if [[ ! -f "$source_dir/main.py" ]]; then
        print_error "main.py not found in source directory"
        exit 1
    fi
    
    # Confirm upgrade
    read -p "Do you want to proceed with the upgrade? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Upgrade cancelled by user"
        exit 0
    fi
    
    # Execute upgrade steps
    create_backup || { print_error "Backup failed"; exit 1; }
    stop_service || { print_error "Failed to stop service"; exit 1; }
    install_files "$source_dir" || { print_error "Failed to install files"; rollback; exit 1; }
    update_dependencies || { print_error "Failed to update dependencies"; rollback; exit 1; }
    start_service || { print_error "Failed to start service"; rollback; exit 1; }
    clean_backups
    
    print_step "Upgrade completed successfully!"
    show_status
}

# Main script logic
case "${1:-upgrade}" in
    "upgrade")
        main_upgrade "$2"
        ;;
    "rollback")
        rollback
        ;;
    "status")
        show_status
        ;;
    "backup")
        create_backup
        ;;
    "clean")
        clean_backups
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac