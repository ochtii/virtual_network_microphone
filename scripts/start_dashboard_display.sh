#!/bin/bash
# Dashboard Auto-Start Script für Raspberry Pi
# Startet Chromium im Kiosk-Modus für das Dashboard

echo "🚀 Starte Dashboard Display..."

# Warte bis X11 bereit ist
sleep 5

# Töte eventuell laufende Chromium-Prozesse
sudo pkill -f chromium > /dev/null 2>&1 || true

# Warte kurz
sleep 2

# Starte Chromium im Kiosk-Modus
DISPLAY=:0 chromium-browser \
    --kiosk \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --no-sandbox \
    --disable-dev-shm-usage \
    --disable-gpu \
    --disable-software-rasterizer \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    --disable-features=TranslateUI \
    --disable-extensions \
    --no-first-run \
    --fast \
    --fast-start \
    --disable-default-apps \
    --disable-popup-blocking \
    http://localhost:3000 \
    > /dev/null 2>&1 &

echo "✅ Dashboard Display gestartet"