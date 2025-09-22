#!/bin/bash
# Stoppt den Python HTTP Server
cd "$(dirname "$0")/.."
if [ -f server.pid ]; then
    PID=$(cat server.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "HTTP Server gestoppt (PID: $PID)"
        rm server.pid
    else
        echo "HTTP Server war nicht aktiv (PID $PID nicht gefunden)"
        rm server.pid
    fi
else
    echo "Keine server.pid Datei gefunden - Server war möglicherweise nicht aktiv"
    # Fallback: Töte alle Python Prozesse die http_server.py ausführen
    pkill -f "python3.*http_server.py"
fi