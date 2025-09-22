#!/bin/bash
# Stoppt sowohl das Python GUI als auch den HTTP Server
cd "$(dirname "$0")/.."

echo "Stoppe HTTP Server..."
$(dirname "$0")/stop_http_server.sh

echo "Stoppe Display GUI..."
if [ -f gui.pid ]; then
    PID=$(cat gui.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "Display GUI gestoppt (PID: $PID)"
        rm gui.pid
    else
        echo "Display GUI war nicht aktiv (PID $PID nicht gefunden)"
        rm gui.pid
    fi
else
    echo "Keine gui.pid Datei gefunden - GUI war möglicherweise nicht aktiv"
    # Fallback: Töte alle Python Prozesse die main.py ausführen
    pkill -f "python3.*main.py"
fi

echo "Alle Services gestoppt"