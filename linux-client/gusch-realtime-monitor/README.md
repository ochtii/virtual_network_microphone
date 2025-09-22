# Gusch Real-time Monitor

Ein real-time Audio-Monitoring Server für das Gusch-System mit WebSocket-basiertem Streaming und dynamischer Visualisierung.

## Features

- 🎤 **Real-time Audio Monitoring**: Live-Überwachung der Raum-Audiopegel mit PyAudio
- 🌐 **WebSocket Streaming**: Echtzeit-Datenübertragung mit 20 FPS Update-Rate  
- 🎨 **Dynamic Background Colors**: Automatische Hintergrundfarbe basierend auf Audiopegel (grün=leise, rot=laut)
- 👥 **Client Management**: Live-Anzeige aller verbundenen Clients mit individuellen Leveln
- 📊 **Real-time Statistics**: Durchschnitt, Peak-Level, aktive Clients und Uptime-Tracking
- 🔄 **Auto-reconnect**: Automatische Wiederverbindung bei Verbindungsabbruch

## Technische Details

### Backend (FastAPI)
- **Port**: 8001
- **Audio Processing**: PyAudio mit RMS/dB-Berechnung
- **Update Rate**: 20 FPS (50ms Intervall)
- **Color Algorithm**: Dynamische RGB-Berechnung basierend auf Audiopegel
- **WebSocket Management**: Multi-Client Broadcasting mit automatischer Cleanup

## Installation

```bash
cd gusch-realtime-monitor
pip install -r requirements.txt
python main.py
```

## Zugriff

- **Monitor Interface**: http://localhost:8001/monitor
- **WebSocket Endpoint**: ws://localhost:8001/ws
- **Health Check**: http://localhost:8001/health

## PM2 Integration

Der Server ist in `ecosystem.config.js` konfiguriert:
- **Name**: gusch-realtime-monitor
- **Memory Limit**: 500M
- **Auto-restart**: Aktiviert
- **Logs**: PM2 Log-Management

## Audio-Konfiguration

Das System erkennt automatisch verfügbare Audio-Eingabegeräte und wählt das Standardgerät aus. Bei Problemen werden Fallback-Modi verwendet.

## Deployment

Der Server wird über das Auto-Deploy-System automatisch mit den anderen Gusch-Komponenten deployed.