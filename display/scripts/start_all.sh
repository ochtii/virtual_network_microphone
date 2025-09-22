#!/bin/bash
# Startet sowohl das Python GUI als auch den HTTP Server
cd "$(dirname "$0")/.."

echo "Starte HTTP Server..."
$(dirname "$0")/start_http_server.sh

echo "Starte Display GUI..."
python3 main.py &
echo $! > gui.pid
echo "Display GUI gestartet (PID: $(cat gui.pid))"

echo ""
echo "Beide Services gestartet:"
echo "- HTTP Server: http://localhost:3000"
echo "- GUI: Python tkinter Anwendung"