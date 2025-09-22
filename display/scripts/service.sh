#!/bin/bash
# Systemd Service Management Scripts

SERVICE_NAME="pimic-display"

case "$1" in
    start)
        echo "Starte $SERVICE_NAME Service..."
        sudo systemctl start $SERVICE_NAME
        ;;
    stop)
        echo "Stoppe $SERVICE_NAME Service..."
        sudo systemctl stop $SERVICE_NAME
        ;;
    restart)
        echo "Starte $SERVICE_NAME Service neu..."
        sudo systemctl restart $SERVICE_NAME
        ;;
    status)
        sudo systemctl status $SERVICE_NAME --no-pager
        ;;
    logs)
        echo "Zeige Logs (Ctrl+C zum Beenden)..."
        sudo journalctl -u $SERVICE_NAME -f
        ;;
    enable)
        echo "Aktiviere Service für automatischen Start..."
        sudo systemctl enable $SERVICE_NAME
        ;;
    disable)
        echo "Deaktiviere automatischen Start..."
        sudo systemctl disable $SERVICE_NAME
        ;;
    uninstall)
        echo "Deinstalliere Service..."
        sudo systemctl stop $SERVICE_NAME
        sudo systemctl disable $SERVICE_NAME
        sudo rm /etc/systemd/system/${SERVICE_NAME}.service
        sudo systemctl daemon-reload
        echo "Service deinstalliert"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|enable|disable|uninstall}"
        echo ""
        echo "Befehle:"
        echo "  start     - Service starten"
        echo "  stop      - Service stoppen"  
        echo "  restart   - Service neustarten"
        echo "  status    - Service Status anzeigen"
        echo "  logs      - Live-Logs anzeigen"
        echo "  enable    - Automatischen Start aktivieren"
        echo "  disable   - Automatischen Start deaktivieren"
        echo "  uninstall - Service komplett entfernen"
        exit 1
        ;;
esac