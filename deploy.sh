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

# Funktion für Port-Prüfung und Bereinigung
check_and_clean_ports() {
    log "Checking required ports..."
    
    # Array der benötigten Ports für pimic
    REQUIRED_PORTS=(3000 3001 3002)
    
    for port in "${REQUIRED_PORTS[@]}"; do
        log "Checking port $port..."
        
        # Prüfe ob Port belegt ist
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            log "Port $port is occupied, checking processes..."
            
            # Finde Prozesse die den Port verwenden
            PIDS=$(lsof -ti:$port)
            
            for pid in $PIDS; do
                # Hole Prozess-Info
                PROCESS_INFO=$(ps -p $pid -o comm=,args= 2>/dev/null || echo "unknown unknown")
                log "Process on port $port: PID=$pid, Info=$PROCESS_INFO"
                
                # Prüfe ob es ein pimic-bezogener Prozess ist
                if echo "$PROCESS_INFO" | grep -qE "(python.*http_server|node.*server|chromium)"; then
                    log "Killing pimic-related process $pid on port $port"
                    kill -TERM $pid 2>/dev/null || true
                    sleep 2
                    
                    # Force kill falls noch da
                    if kill -0 $pid 2>/dev/null; then
                        log "Force killing stubborn process $pid"
                        kill -KILL $pid 2>/dev/null || true
                    fi
                else
                    log "WARNING: Unknown process $pid occupying port $port - manual intervention may be needed"
                fi
            done
            
            # Warte kurz und prüfe nochmal
            sleep 3
            if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
                log "WARNING: Port $port still occupied after cleanup"
            else
                log "Port $port successfully cleaned"
            fi
        else
            log "Port $port is available"
        fi
    done
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

# Port-Prüfung und Bereinigung vor PM2 Restart
check_and_clean_ports

if pm2 list | grep -q "pimic-display"; then
    log "Restarting PM2 services..."
    pm2 restart pimic-display
    
    # Warte kurz und prüfe ob Services ordnungsgemäß gestartet sind
    sleep 5
    if ! pm2 list | grep -q "online.*pimic-display"; then
        log "ERROR: pimic-display service failed to start properly"
        exit 1
    fi
    log "PM2 services restarted successfully"
else
    log "Starting PM2 services..."
    cd "$DISPLAY_DIR"
    pm2 start ecosystem.config.js
    
    # Warte kurz und prüfe ob Services ordnungsgemäß gestartet sind
    sleep 5
    if ! pm2 list | grep -q "online.*pimic-display"; then
        log "ERROR: pimic-display service failed to start"
        exit 1
    fi
    log "PM2 services started successfully"
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