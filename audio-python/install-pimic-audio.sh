#!/bin/bash
# PIMIC Audio Service Installation - Pure Python Version with PM2
# Installiert und konfiguriert den Python Audio Streaming Service mit PM2

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎵 PIMIC Audio Service Installation (Pure Python + PM2) 🎵${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Konfiguration
SERVICE_DIR="/opt/pimic-audio"
LOG_DIR="/var/log/pimic"
USER="pi"

# Aktueller Benutzer prüfen
CURRENT_USER=$(whoami)
if [[ "$CURRENT_USER" != "root" && "$CURRENT_USER" != "pi" ]]; then
    echo -e "${YELLOW}⚠️  Erkannter Benutzer: $CURRENT_USER${NC}"
    USER="$CURRENT_USER"
fi

echo -e "${GREEN}✅ Benutzer: $USER${NC}"

# Python Version prüfen
echo -e "${BLUE}🐍 Python Version prüfen...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' || echo "unknown")
echo -e "${GREEN}✅ Python: $PYTHON_VERSION${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 nicht gefunden!${NC}"
    echo -e "${YELLOW}Installiere Python 3...${NC}"
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
fi

# PM2 Installation prüfen
echo -e "${BLUE}📦 PM2 Installation prüfen...${NC}"
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}⚠️  PM2 nicht gefunden, installiere...${NC}"
    
    # Node.js installieren falls nicht vorhanden
    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}📦 Node.js installieren...${NC}"
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    
    # PM2 global installieren
    sudo npm install -g pm2
    
    # PM2 startup für aktuellen User
    pm2 startup | tail -1 | sudo bash
    echo -e "${GREEN}✅ PM2 installiert und konfiguriert${NC}"
else
    echo -e "${GREEN}✅ PM2 bereits installiert${NC}"
fi

# Service-Verzeichnis erstellen
echo -e "${BLUE}📁 Service-Verzeichnis erstellen...${NC}"
sudo mkdir -p "$SERVICE_DIR"
sudo mkdir -p "$SERVICE_DIR/templates"
sudo mkdir -p "$SERVICE_DIR/static"
sudo mkdir -p "$LOG_DIR"
sudo chown -R "$USER:$USER" "$SERVICE_DIR"
sudo chown -R "$USER:$USER" "$LOG_DIR"

# Alle Dateien kopieren
echo -e "${BLUE}📋 Server-Dateien kopieren...${NC}"
sudo cp pimic_minimal_server.py "$SERVICE_DIR/"
sudo cp -r templates/ "$SERVICE_DIR/"
sudo cp -r static/ "$SERVICE_DIR/"
sudo chmod +x "$SERVICE_DIR/pimic_minimal_server.py"
sudo chown -R "$USER:$USER" "$SERVICE_DIR"

# PM2 Ecosystem Konfiguration erstellen
echo -e "${BLUE}⚙️  PM2 Ecosystem konfigurieren...${NC}"
sudo tee "$SERVICE_DIR/ecosystem.config.js" > /dev/null <<EOF
module.exports = {
  apps: [{
    name: 'pimic-audio',
    script: '/usr/bin/python3',
    args: 'pimic_minimal_server.py',
    cwd: '$SERVICE_DIR',
    interpreter: 'none',
    instances: 1,
    exec_mode: 'fork',
    
    // Auto-restart configuration
    autorestart: true,
    watch: false,
    max_memory_restart: '256M',
    
    // Logging
    log_file: '$LOG_DIR/pimic-audio.log',
    out_file: '$LOG_DIR/pimic-audio-out.log',
    error_file: '$LOG_DIR/pimic-audio-error.log',
    log_type: 'json',
    
    // Environment
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '$SERVICE_DIR',
      PIMIC_LOG_LEVEL: 'INFO'
    },
    
    // Process management
    kill_timeout: 5000,
    restart_delay: 2000,
    
    // Monitoring
    min_uptime: '10s',
    max_restarts: 10
  }]
};
EOF

sudo chown "$USER:$USER" "$SERVICE_DIR/ecosystem.config.js"

# Firewall-Regeln (optional)
echo -e "${BLUE}🔥 Firewall-Regeln prüfen...${NC}"
if command -v ufw &> /dev/null; then
    sudo ufw allow 6969/tcp comment "PIMIC Audio Web Interface"
    sudo ufw allow 420:520/tcp comment "PIMIC Audio Streams"
    echo -e "${GREEN}✅ UFW Regeln hinzugefügt${NC}"
fi

# PM2 Service starten
echo -e "${BLUE}🚀 PM2 Service starten...${NC}"
cd "$SERVICE_DIR"

# Als User ausführen (nicht root)
sudo -u "$USER" pm2 start ecosystem.config.js

# PM2 Konfiguration speichern
sudo -u "$USER" pm2 save

# Service Status prüfen
sleep 3
PM2_STATUS=$(sudo -u "$USER" pm2 list | grep pimic-audio | awk '{print $10}' || echo "stopped")

if [[ "$PM2_STATUS" == "online" ]]; then
    echo -e "${GREEN}✅ Service erfolgreich gestartet!${NC}"
    
    # IP-Adresse ermitteln
    IP=$(hostname -I | awk '{print $1}' || echo "localhost")
    
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🎉 PIMIC Audio Service Installation erfolgreich! 🎉${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}📡 Web Interface: http://$IP:6969${NC}"
    echo -e "${YELLOW}🎧 Stream Ports:  420+${NC}"
    echo -e "${YELLOW}🐍 Python Service: PM2 Managed${NC}"
    echo -e "${YELLOW}🚀 No Dependencies: Standard Library Only${NC}"
    echo -e "${YELLOW}📁 Templates:     $SERVICE_DIR/templates/${NC}"
    echo -e "${YELLOW}🎨 Static Files:  $SERVICE_DIR/static/${NC}"
    echo ""
    echo -e "${BLUE}Service Management (PM2):${NC}"
    echo -e "  Start:   ${YELLOW}pm2 start pimic-audio${NC}"
    echo -e "  Stop:    ${YELLOW}pm2 stop pimic-audio${NC}"
    echo -e "  Restart: ${YELLOW}pm2 restart pimic-audio${NC}"
    echo -e "  Status:  ${YELLOW}pm2 status pimic-audio${NC}"
    echo -e "  Logs:    ${YELLOW}pm2 logs pimic-audio${NC}"
    echo -e "  Monitor: ${YELLOW}pm2 monit${NC}"
    echo ""
    echo -e "${GREEN}✨ Bereit für Audio Streaming! ✨${NC}"
    
else
    echo -e "${RED}❌ Service-Start fehlgeschlagen!${NC}"
    echo -e "${YELLOW}PM2 Status prüfen:${NC}"
    sudo -u "$USER" pm2 status
    echo ""
    echo -e "${YELLOW}Logs anzeigen:${NC}"
    sudo -u "$USER" pm2 logs pimic-audio --lines 20
    exit 1
fi