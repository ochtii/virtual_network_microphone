#!/bin/bash

# Automatisches GitHub Deployment Script für pimic
# Verwendet von PM2 für automatische Updates

set -e  # Exit bei Fehlern

PROJECT_DIR="/home/ochtii/pimic"
DISPLAY_DIR="$PROJECT_DIR/display"
BACKUP_DIR="/home/ochtii/pimic_backup"
LOG_FILE="$DISPLAY_DIR/deploy.log"

echo "$(date): Starting deployment..." >> "$LOG_FILE"

# Funktion für Logging
log() {
    echo "$(date): $1" | tee -a "$LOG_FILE"
}

# Funktion für Rollback
rollback() {
    log "ERROR: Deployment failed, rolling back..."
    if [ -d "$BACKUP_DIR" ]; then
        cd /home/ochtii
        rm -rf pimic
        mv pimic_backup pimic
        log "Rollback completed"
    fi
    exit 1
}

# Error handler
trap rollback ERR

log "Checking current directory..."
cd "$PROJECT_DIR"

log "Creating backup..."
if [ -d "$BACKUP_DIR" ]; then
    rm -rf "$BACKUP_DIR"
fi
cp -r "$PROJECT_DIR" "$BACKUP_DIR"

log "Fetching latest changes from GitHub..."
git fetch origin

log "Checking for updates..."
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "No updates available, deployment skipped"
    exit 0
fi

log "Updates found, pulling changes..."
git reset --hard origin/master

log "Setting correct permissions..."
chmod +x "$PROJECT_DIR/deploy.sh"
chmod +x "$DISPLAY_DIR/scripts/*.sh" 2>/dev/null || true

log "Checking if PM2 is running..."
export PATH=/usr/bin:~/.npm-global/bin:$PATH

if pm2 list | grep -q "pimic-display"; then
    log "Restarting PM2 services..."
    pm2 restart pimic-display
else
    log "Starting PM2 services..."
    cd "$DISPLAY_DIR"
    pm2 start ecosystem.config.js
fi

log "Restarting Chromium on Pi..."
# Chromium neustarten nach erfolgreichem Deployment
sudo pkill -f chromium 2>/dev/null || true
sleep 3
DISPLAY=:0 chromium-browser --kiosk --disable-infobars --disable-session-crashed-bubble --disable-restore-session-state --no-sandbox http://localhost:3000 > /dev/null 2>&1 &
log "Chromium restarted successfully"

log "Deployment completed successfully!"

# Cleanup old backups (keep only latest)
log "Cleaning up old backups..."
find /home/ochtii -name "pimic_backup_*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

log "=== Deployment finished ==="