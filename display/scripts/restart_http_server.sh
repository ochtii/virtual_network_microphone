#!/bin/bash
# Neustart des Python HTTP Servers
echo "Stoppe HTTP Server..."
$(dirname "$0")/stop_http_server.sh
sleep 2
echo "Starte HTTP Server..."
$(dirname "$0")/start_http_server.sh