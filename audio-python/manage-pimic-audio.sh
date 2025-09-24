#!/bin/bash
# PIMIC Audio Service Management Script - PM2 Version
# Verwaltet den Python Audio Streaming Service mit PM2

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVICE_NAME="pimic-audio"
SERVICE_DIR="/opt/pimic-audio"
LOG_DIR="/var/log/pimic"

# Funktion: Status anzeigen
show_status() {
    echo -e "${BLUE}📊 PIMIC Audio Service Status (PM2)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # PM2 Status prüfen
    PM2_STATUS=$(pm2 jlist 2>/dev/null | jq -r ".[] | select(.name==\"$SERVICE_NAME\") | .pm2_env.status" 2>/dev/null || echo "not_found")
    
    if [[ "$PM2_STATUS" == "online" ]]; then
        echo -e "${GREEN}✅ Service: Online (PM2)${NC}"
        
        # IP-Adresse ermitteln
        IP=$(hostname -I | awk '{print $1}' || echo "localhost")
        echo -e "${GREEN}📡 Web Interface: http://$IP:6969${NC}"
        
        # PM2 Details
        echo ""
        pm2 info $SERVICE_NAME
        
        # Aktive Verbindungen prüfen
        echo ""
        echo -e "${BLUE}🌐 Aktive Verbindungen auf Port 6969:${NC}"
        netstat -an | grep :6969 || echo "Keine aktiven Verbindungen"
        
        # Health Check
        echo ""
        echo -e "${BLUE}❤️ Health Check:${NC}"
        curl -s "http://localhost:6969/health" | python3 -m json.tool 2>/dev/null || echo "Health Check fehlgeschlagen"
        
    elif [[ "$PM2_STATUS" == "stopped" ]]; then
        echo -e "${YELLOW}⚠️  Service: Gestoppt${NC}"
    else
        echo -e "${RED}❌ Service: Nicht gefunden oder Fehler${NC}"
        echo -e "${YELLOW}PM2 Prozesse:${NC}"
        pm2 list
    fi
}

# Funktion: Service starten
start_service() {
    echo -e "${BLUE}🚀 PIMIC Audio Service starten (PM2)...${NC}"
    pm2 start $SERVICE_NAME
    sleep 2
    
    PM2_STATUS=$(pm2 jlist 2>/dev/null | jq -r ".[] | select(.name==\"$SERVICE_NAME\") | .pm2_env.status" 2>/dev/null || echo "error")
    
    if [[ "$PM2_STATUS" == "online" ]]; then
        echo -e "${GREEN}✅ Service erfolgreich gestartet!${NC}"
        IP=$(hostname -I | awk '{print $1}' || echo "localhost")
        echo -e "${GREEN}📡 Verfügbar unter: http://$IP:6969${NC}"
    else
        echo -e "${RED}❌ Service-Start fehlgeschlagen!${NC}"
        pm2 logs $SERVICE_NAME --lines 10
    fi
}

# Funktion: Service stoppen
stop_service() {
    echo -e "${YELLOW}⏹️ PIMIC Audio Service stoppen...${NC}"
    pm2 stop $SERVICE_NAME
    
    PM2_STATUS=$(pm2 jlist 2>/dev/null | jq -r ".[] | select(.name==\"$SERVICE_NAME\") | .pm2_env.status" 2>/dev/null || echo "error")
    
    if [[ "$PM2_STATUS" == "stopped" ]]; then
        echo -e "${GREEN}✅ Service erfolgreich gestoppt!${NC}"
    else
        echo -e "${RED}❌ Service-Stopp fehlgeschlagen!${NC}"
        pm2 status $SERVICE_NAME
    fi
}

# Funktion: Service neu starten
restart_service() {
    echo -e "${BLUE}🔄 PIMIC Audio Service neu starten...${NC}"
    pm2 restart $SERVICE_NAME
    sleep 2
    
    PM2_STATUS=$(pm2 jlist 2>/dev/null | jq -r ".[] | select(.name==\"$SERVICE_NAME\") | .pm2_env.status" 2>/dev/null || echo "error")
    
    if [[ "$PM2_STATUS" == "online" ]]; then
        echo -e "${GREEN}✅ Service erfolgreich neu gestartet!${NC}"
        IP=$(hostname -I | awk '{print $1}' || echo "localhost")
        echo -e "${GREEN}📡 Verfügbar unter: http://$IP:6969${NC}"
    else
        echo -e "${RED}❌ Service-Neustart fehlgeschlagen!${NC}"
        pm2 logs $SERVICE_NAME --lines 10
    fi
}

# Funktion: Logs anzeigen
show_logs() {
    echo -e "${BLUE}📋 PIMIC Audio Service Logs (PM2)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    echo -e "${YELLOW}PM2 Logs für $SERVICE_NAME:${NC}"
    pm2 logs $SERVICE_NAME --lines 30
    
    echo ""
    echo -e "${BLUE}Verfügbare PM2 Log-Befehle:${NC}"
    echo -e "  Live-Logs:     ${YELLOW}pm2 logs $SERVICE_NAME${NC}"
    echo -e "  Alle Logs:     ${YELLOW}pm2 logs $SERVICE_NAME --lines 100${NC}"
    echo -e "  Error-Logs:    ${YELLOW}pm2 logs $SERVICE_NAME --err${NC}"
    echo -e "  Output-Logs:   ${YELLOW}pm2 logs $SERVICE_NAME --out${NC}"
    echo -e "  Log-Dateien:   ${YELLOW}$LOG_DIR/pimic-audio*.log${NC}"
}

# Funktion: Service deinstallieren
uninstall_service() {
    echo -e "${YELLOW}🗑️ PIMIC Audio Service deinstallieren (PM2)...${NC}"
    
    # PM2 Service stoppen und löschen
    pm2 stop $SERVICE_NAME 2>/dev/null || true
    pm2 delete $SERVICE_NAME 2>/dev/null || true
    pm2 save
    
    # Service-Verzeichnis löschen
    sudo rm -rf "$SERVICE_DIR"
    
    # Log-Verzeichnis löschen
    sudo rm -rf "$LOG_DIR"
    
    echo -e "${GREEN}✅ Service erfolgreich deinstalliert!${NC}"
    echo -e "${YELLOW}PM2 Startup-Script bleibt installiert für andere Services${NC}"
}

# Funktion: Netzwerk-Info anzeigen
show_network() {
    echo -e "${BLUE}🌐 Netzwerk-Informationen${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # IP-Adressen
    echo -e "${YELLOW}IP-Adressen:${NC}"
    hostname -I | tr ' ' '\n' | grep -v '^$' | while read ip; do
        echo -e "  http://$ip:6969"
    done
    
    echo ""
    echo -e "${YELLOW}Hostname:${NC} $(hostname)"
    
    # Port-Status
    echo ""
    echo -e "${YELLOW}Port-Status:${NC}"
    netstat -tlnp | grep -E ':(6969|420)' || echo "Keine Ports aktiv"
    
    # Firewall-Status
    echo ""
    if command -v ufw &> /dev/null; then
        echo -e "${YELLOW}UFW Status:${NC}"
        sudo ufw status | grep -E '(6969|420)' || echo "Keine UFW-Regeln für PIMIC"
    fi
}

# Funktion: Hilfe anzeigen
show_help() {
    echo -e "${BLUE}🎵 PIMIC Audio Service Management${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}Verwendung:${NC}"
    echo -e "  $0 {start|stop|restart|status|logs|network|uninstall|help}"
    echo ""
    echo -e "${YELLOW}Kommandos:${NC}"
    echo -e "  ${GREEN}start${NC}     - Service starten"
    echo -e "  ${RED}stop${NC}      - Service stoppen"
    echo -e "  ${BLUE}restart${NC}   - Service neu starten"
    echo -e "  ${YELLOW}status${NC}    - Service-Status anzeigen"
    echo -e "  ${YELLOW}logs${NC}      - Service-Logs anzeigen"
    echo -e "  ${YELLOW}network${NC}   - Netzwerk-Informationen"
    echo -e "  ${RED}uninstall${NC} - Service komplett deinstallieren"
    echo -e "  ${BLUE}help${NC}      - Diese Hilfe anzeigen"
    echo ""
    echo -e "${YELLOW}Beispiele:${NC}"
    echo -e "  ./manage-pimic-audio.sh start"
    echo -e "  ./manage-pimic-audio.sh status"
    echo -e "  ./manage-pimic-audio.sh logs"
    echo ""
    echo -e "${GREEN}🐍 Pure Python - No npm dependencies required! 🐍${NC}"
}

# Hauptlogik
case "${1:-status}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    network)
        show_network
        ;;
    uninstall)
        echo -e "${RED}⚠️ Service wird komplett deinstalliert! Fortfahren? (y/N)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            uninstall_service
        else
            echo "Abgebrochen."
        fi
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unbekanntes Kommando: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac