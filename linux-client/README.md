# 🎵 Raspberry Pi Sound Monitor v2.1

Ein modernes, webbasiertes Audio-Monitoring-System für Raspberry Pi mit Echtzeit-Dashboard, Hardware-Management, Multi-Teilnehmer-Support und automatischem Deployment.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![Auto-Deploy](https://img.shields.io/badge/Auto--Deploy-Active-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

### 🎤 Audio-Monitoring
- **Multi-Teilnehmer-Support** - Überwachung mehrerer Audio-Quellen gleichzeitig
- **Echtzeit-Pegel-Anzeige** - Live Audio-Level-Meter mit WebSocket-Updates
- **USB-Audio-Geräte-Management** - Automatische Erkennung und Verwaltung von Audio-Hardware
- **Audio-Statistiken** - Teilnehmer-Stats, Lautstärke-Metriken, Peak-Tracking

### 🌐 Modern Dashboard
- **Dark Mode Interface** - Professionelles, augenfreundliches Design
- **Tabbed Navigation** - Übersichtliche Struktur (Dashboard, Hardware, Live-Monitoring, Admin)
- **Responsive Design** - Optimiert für Desktop und mobile Geräte
- **Echtzeit-Updates** - WebSocket-basierte Live-Datenaktualisierung

### 📊 System-Monitoring
- **Hardware-Übersicht** - CPU, Memory, Storage, Network-Interfaces
- **Live-Metriken** - System-Performance in Echtzeit
- **Netzwerk-Status** - LAN/WLAN-Verbindungen mit Details
- **Uptime-Tracking** - System-Laufzeit und Load-Average

### 🔧 Hardware-Management
- **Scan-Funktionen** - Audio- und USB-Geräte-Erkennung auf Knopfdruck
- **Device-Linking** - USB-Audio-Geräteverknüpfung
- **Status-Überwachung** - Hardware-Zustandsanzeige
- **Hot-Plug-Support** - Dynamische Geräteerkennung

## 🚀 Quick Start

### Voraussetzungen
- **Raspberry Pi** (empfohlen: Pi 4 mit 4GB+ RAM)
- **Raspberry Pi OS** (Bullseye oder neuer)
- **Python 3.8+**
- **USB-Audio-Interface** (optional, für erweiterte Funktionen)

### Installation

1. **Repository klonen:**
```bash
git clone https://github.com/ochtii/gusch.git
cd gusch
```

2. **Virtual Environment erstellen:**
```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Dependencies installieren:**
```bash
pip install -r requirements.txt
```

4. **Audio-System vorbereiten:**
```bash
# ALSA-Tools installieren
sudo apt update
sudo apt install alsa-utils portaudio19-dev python3-pyaudio

# Audio-Geräte auflisten
arecord -l
aplay -l
```

5. **Anwendung starten:**
```bash
# Entwicklungsmodus
python main.py

# Oder mit uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

6. **Dashboard öffnen:**
```
http://[raspberry-pi-ip]:8000
```

### Produktionsdeployment

```bash
# PM2 für Prozess-Management installieren
npm install -g pm2

# Anwendung starten
chmod +x start.sh
./start.sh

# PM2 Status prüfen
pm2 status
pm2 logs sound-monitor
```

## 📁 Projektstruktur

```
gusch/
├── app/                          # FastAPI Application
│   ├── api/                      # API Endpoints
│   │   ├── hardware_api.py       # Hardware & Device Management
│   │   ├── metrics_api.py        # System Metrics
│   │   └── websocket_api.py      # WebSocket Connections
│   ├── core/                     # Core Components
│   │   ├── audio_manager.py      # Audio Processing
│   │   ├── config.py            # Configuration Management
│   │   └── websocket_manager.py  # WebSocket Handler
│   └── models/                   # Data Models
│       ├── audio_models.py       # Audio-related Models
│       └── system_models.py      # System Metrics Models
├── logs/                         # Application Logs
├── main.py                       # Application Entry Point
├── requirements.txt              # Python Dependencies
├── start.sh                      # Production Startup Script
└── README.md                     # This File
```

## 🔧 Konfiguration

### Audio-Einstellungen
```python
# In app/core/config.py anpassen
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHUNK_SIZE = 1024
AUDIO_CHANNELS = 1
AUDIO_FORMAT = pyaudio.paInt16
```

### WebSocket-Konfiguration
```python
# WebSocket Update-Intervalle
METRICS_UPDATE_INTERVAL = 2.0  # Sekunden
AUDIO_UPDATE_INTERVAL = 0.1    # Sekunden
HARDWARE_SCAN_INTERVAL = 30.0  # Sekunden
```

### Netzwerk-Einstellungen
```bash
# Standard-Port ändern
uvicorn main:app --host 0.0.0.0 --port 8080
```

## 📊 API-Dokumentation

Das System bietet eine vollständige REST-API mit interaktiver Dokumentation:

- **Swagger UI:** `http://[ip]:8000/docs`
- **ReDoc:** `http://[ip]:8000/redoc`

### Wichtige Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/` | GET | Dashboard Interface |
| `/api/metrics/system` | GET | System-Metriken |
| `/api/audio-devices` | GET | Audio-Geräte auflisten |
| `/api/audio-devices/scan` | POST | Audio-Geräte scannen |
| `/api/usb-devices` | GET | USB-Geräte auflisten |
| `/api/usb-devices/scan` | POST | USB-Geräte scannen |
| `/api/system-hardware` | GET | Hardware-Informationen |
| `/api/network-interfaces` | GET | Netzwerk-Interfaces |
| `/api/audio-stats` | GET | Audio-Statistiken |
| `/ws/dashboard/{client_id}` | WebSocket | Echtzeit-Updates |

## 🎛️ Dashboard-Features

### 📈 Dashboard-Tab
- **System-Metriken:** CPU, Memory, Disk, Network, Uptime
- **Live-Charts:** CPU-Verlauf und Audio-Level-Diagramme
- **Status-Karten:** Schnellübersicht aller wichtigen Systeminformationen

### 🔧 Hardware-Tab
- **Audio-Hardware:** Verfügbare Ein-/Ausgabegeräte mit Scan-Funktion
- **USB-Geräte:** Angeschlossene USB-Hardware mit Audio-Verknüpfung
- **System-Hardware:** CPU, Memory, Storage, Network-Details

### 📺 Live-Monitoring-Tab
- **Audio-Pegel:** Echtzeit-Visualisierung aller Teilnehmer
- **Event-Log:** Erkannte Audio-Events und Schwellwert-Überschreitungen
- **Server-Logs:** Live-Anzeige der Anwendungslogs

### ⚙️ Admin-Tab
- **System-Kontrolle:** Server-Neustart, Log-Bereinigung
- **Konfiguration:** Einstellungen exportieren/importieren
- **Monitoring-Kontrolle:** Audio-Überwachung ein-/ausschalten

## 🌐 Netzwerk-Features

### Netzwerk-Status-Karten
- **Ethernet (eth0):** Kabelgebundene Verbindung mit IP und Statistics
- **WiFi (wlan0):** Drahtlose Verbindung mit Signal-Qualität
- **Speed-Anzeige:** Interface-Geschwindigkeit und MTU-Größe
- **Traffic-Monitoring:** Gesendete/Empfangene Datenpakete

### Audio-Statistiken
- **Teilnehmer-Count:** Aktive/Inaktive Teilnehmer-Anzahl
- **Lautstärke-Metrics:** Durchschnitt, Peak, Min/Max-Werte
- **Quality-Score:** Verbindungsqualität in Prozent
- **Session-Info:** Sitzungsdauer und Event-Zähler

## 🔊 Audio-System

### Unterstützte Formate
- **Sample Rates:** 8kHz - 96kHz (Standard: 44.1kHz)
- **Bit Depth:** 16-bit, 24-bit, 32-bit
- **Channels:** Mono/Stereo/Multi-Channel
- **Codecs:** PCM, ALSA-kompatible Formate

### USB-Audio-Geräte
- **Automatische Erkennung** von USB-Audio-Interfaces
- **Hot-Plug-Support** für dynamisches An-/Abstecken
- **Geräteverknüpfung** zwischen USB- und Audio-Subsystem
- **Status-Überwachung** mit visuellen Indikatoren

## 🛠️ Troubleshooting

### Häufige Probleme

**1. Audio-Geräte nicht erkannt:**
```bash
# ALSA-System neustarten
sudo alsa force-reload

# Berechtigungen prüfen
sudo usermod -a -G audio $USER

# Neustart erforderlich
sudo reboot
```

**2. WebSocket-Verbindungsfehler:**
```bash
# Firewall-Regeln prüfen
sudo ufw status
sudo ufw allow 8000

# Port-Verfügbarkeit testen
netstat -tlnp | grep 8000
```

**3. Performance-Probleme:**
```bash
# GPU Memory Split anpassen
sudo raspi-config
# Advanced Options > Memory Split > 64

# CPU-Governor auf Performance setzen
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Debug-Modus

```bash
# Verbose Logging aktivieren
export LOG_LEVEL=DEBUG
python main.py

# Oder in der Konfiguration
LOG_LEVEL = "DEBUG"
```

### Log-Analyse

```bash
# Live-Logs verfolgen
tail -f logs/sound_monitor.log

# PM2-Logs (falls verwendet)
pm2 logs sound-monitor

# System-Logs für Audio
journalctl -u alsa-state -f
```

## 🚀 Erweiterte Features

### Custom Audio-Processing
```python
# Eigene Audio-Verarbeitung implementieren
class CustomAudioProcessor:
    def process_chunk(self, audio_data):
        # Ihre Verarbeitung hier
        return processed_data
```

### WebSocket-Events erweitern
```javascript
// Custom Event-Handler hinzufügen
window.dashboard.on('custom_event', (data) => {
    console.log('Custom event received:', data);
});
```

### API-Erweiterungen
```python
# Neue Endpoints in app/api/ hinzufügen
@router.get("/custom-endpoint")
async def custom_endpoint():
    return {"message": "Custom functionality"}
```

## 📝 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe LICENSE-Datei für Details.

## 🤝 Contributing

Beiträge sind willkommen! Bitte:

1. Fork des Repositories erstellen
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Änderungen committen (`git commit -m 'Add some AmazingFeature'`)
4. Branch pushen (`git push origin feature/AmazingFeature`)
5. Pull Request öffnen

## 📞 Support

Bei Fragen oder Problemen:
- **GitHub Issues:** Für Bug-Reports und Feature-Requests
- **Dokumentation:** Detaillierte API-Docs unter `/docs`
- **Logs:** Prüfen Sie die Log-Dateien in `logs/`

## 🏆 Changelog

### v2.0 - Modern Dashboard Edition
- ✅ Komplett überarbeitetes Dashboard mit Dark Mode
- ✅ WebSocket-basierte Echtzeit-Updates
- ✅ Hardware-Management mit Scan-Funktionen
- ✅ Netzwerk-Status und Audio-Statistiken
- ✅ Responsive Design für alle Geräte
- ✅ REST-API mit vollständiger Dokumentation

### v1.x - Legacy Version
- Basic Audio-Monitoring
- Simple Web Interface
- Grundlegende Hardware-Erkennung

---

**Made with ❤️ for the Raspberry Pi Community**