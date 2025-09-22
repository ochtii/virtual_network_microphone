#!/bin/bash
# Startet den Python HTTP Server für das Web-Frontend
cd "$(dirname "$0")/.."
python3 http_server.py 3000 &
echo $! > server.pid
echo "HTTP Server gestartet (PID: $(cat server.pid))"