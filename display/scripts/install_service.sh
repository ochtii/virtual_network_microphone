#!/bin/bash
# Installiert und startet den Systemd Service für den HTTP Server

SERVICE_NAME="pimic-display"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
LOCAL_SERVICE_FILE="$(dirname "$0")/../${SERVICE_NAME}.service"

echo "=== Pi Mic Display Service Installation ==="

# Service-Datei kopieren
echo "Kopiere Service-Datei nach ${SERVICE_FILE}..."
sudo cp "$LOCAL_SERVICE_FILE" "$SERVICE_FILE"

# Systemd neu laden
echo "Lade Systemd-Konfiguration neu..."
sudo systemctl daemon-reload

# Service aktivieren (automatischer Start beim Boot)
echo "Aktiviere Service für automatischen Start..."
sudo systemctl enable $SERVICE_NAME

# Service starten
echo "Starte Service..."
sudo systemctl start $SERVICE_NAME

# Status anzeigen
echo ""
echo "=== Service Status ==="
sudo systemctl status $SERVICE_NAME --no-pager

echo ""
echo "=== Nützliche Befehle ==="
echo "Service stoppen:     sudo systemctl stop $SERVICE_NAME"
echo "Service starten:     sudo systemctl start $SERVICE_NAME"
echo "Service neustarten:  sudo systemctl restart $SERVICE_NAME" 
echo "Service Status:      sudo systemctl status $SERVICE_NAME"
echo "Logs anzeigen:       sudo journalctl -u $SERVICE_NAME -f"
echo "Service deaktivieren: sudo systemctl disable $SERVICE_NAME"
echo ""
echo "Web-Interface: http://192.168.188.90:3000"