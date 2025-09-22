#!/bin/bash
# PM2-ähnlicher Daemon Manager für Python HTTP Server
# Verwendung: ./pm2-like.sh {start|stop|restart|status|logs}

SERVICE_NAME="pimic-display"
SCRIPT_PATH="/home/ochtii/pimic/display/http_server.py"
PID_FILE="/home/ochtii/pimic/display/pm2.pid"
LOG_FILE="/home/ochtii/pimic/display/pm2.log"

start() {
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        if kill -0 $PID 2>/dev/null; then
            echo "Service bereits aktiv (PID: $PID)"
            return 1
        fi
    fi
    
    echo "Starte $SERVICE_NAME..."
    cd "$(dirname "$SCRIPT_PATH")"
    nohup python3 "$SCRIPT_PATH" 3000 >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Service gestartet (PID: $(cat $PID_FILE))"
    echo "Logs: tail -f $LOG_FILE"
}

stop() {
    if [ ! -f $PID_FILE ]; then
        echo "Service nicht aktiv (PID-Datei nicht gefunden)"
        return 1
    fi
    
    PID=$(cat $PID_FILE)
    if ! kill -0 $PID 2>/dev/null; then
        echo "Service nicht aktiv (PID $PID nicht gefunden)"
        rm -f $PID_FILE
        return 1
    fi
    
    echo "Stoppe $SERVICE_NAME (PID: $PID)..."
    kill $PID
    sleep 2
    
    if kill -0 $PID 2>/dev/null; then
        echo "Force kill..."
        kill -9 $PID
    fi
    
    rm -f $PID_FILE
    echo "Service gestoppt"
}

status() {
    if [ ! -f $PID_FILE ]; then
        echo "Status: Stopped"
        return 1
    fi
    
    PID=$(cat $PID_FILE)
    if kill -0 $PID 2>/dev/null; then
        echo "Status: Running (PID: $PID)"
        echo "CPU/Memory: $(ps -p $PID -o pid,ppid,%cpu,%mem,cmd --no-headers)"
        echo "Started: $(ps -p $PID -o lstart --no-headers)"
    else
        echo "Status: Dead (PID file exists but process not running)"
        rm -f $PID_FILE
    fi
}

logs() {
    if [ ! -f $LOG_FILE ]; then
        echo "Keine Log-Datei gefunden: $LOG_FILE"
        return 1
    fi
    
    echo "=== Zeige Logs (Ctrl+C zum Beenden) ==="
    tail -f "$LOG_FILE"
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "PM2-ähnlicher Manager für Python HTTP Server"
        echo "  start   - Service starten"
        echo "  stop    - Service stoppen"
        echo "  restart - Service neustarten"
        echo "  status  - Status anzeigen"
        echo "  logs    - Live-Logs anzeigen"
        exit 1
        ;;
esac