# 🎵 PIMIC Audio Streaming Service

Ein vollständiger Netzwerk-Audio-Streaming-Service für Raspberry Pi, der es Benutzern ermöglicht, Audio direkt vom Browser ins lokale Netzwerk zu streamen.

## ✨ Features

### 🎧 Audio-Streaming
- **Browser-basiert**: Streaming direkt vom Client-Browser
- **Konfigurierbare Ports**: Standard Port 420, freiwählbar
- **Variable Bitrate**: 64-320 kbps einstellbar
- **Mehrere Quellen**: Mikrofon, System-Audio oder beides
- **Real-time Übertragung**: Niedrige Latenz für Live-Audio

### 📊 Audio-Monitoring
- **Animierte Pegelanzeige**: Canvas-basierte Visualisierung
- **dB-Werte**: Präzise Pegelmessung in Dezibel
- **Farb-codiert**: Grün/Gelb/Rot je nach Pegel
- **Real-time Updates**: Live-Monitoring während Streaming

### 🌐 Netzwerk-Discovery
- **mDNS/Bonjour**: Automatische Service-Erkennung
- **UDP Broadcast**: Fallback für Discovery
- **LAN-weite Verfügbarkeit**: Alle Geräte im Netzwerk können Streams finden
- **Service-Announcement**: Streams werden automatisch angekündigt

### 🛠️ Management
- **PM2 Integration**: Prozess-Management und Auto-Restart
- **Systemd Service**: System-Integration
- **Web-Interface**: Benutzerfreundliche Kontrolle
- **REST API**: Programmatische Steuerung

## 📁 Projekt-Struktur

```
pimic/audio/
├── server.js              # Haupt-Server mit Socket.IO
├── network-discovery.js   # mDNS/UDP Discovery System
├── package.json           # Node.js Dependencies
├── ecosystem.config.js    # PM2 Konfiguration
├── public/
│   ├── index.html         # Web-Interface
│   ├── style.css          # Responsive Design
│   └── app.js             # Client-JavaScript
└── scripts/
    ├── install_service.sh # Installations-Script
    └── service.sh         # Management-Script
```

## 🚀 Installation

### Automatische Installation

```bash
# Repository klonen
cd /home/pi/pimic
git pull

# Audio-Service installieren
cd audio
chmod +x scripts/install_service.sh
./scripts/install_service.sh
```

### Manuelle Installation

1. **System-Dependencies:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential libasound2-dev libavahi-compat-libdnssd-dev pulseaudio
```

2. **Node.js Dependencies:**
```bash
cd /home/pi/pimic/audio
npm install --production
```

3. **PM2 Setup:**
```bash
npm install -g pm2
pm2 start ecosystem.config.js --env production
pm2 save
pm2 startup
```

## 🎮 Verwendung

### Web-Interface

1. **Browser öffnen:**
   - Lokal: `http://localhost:6969`
   - Netzwerk: `http://[PI-IP]:6969`

2. **Stream konfigurieren:**
   - Audio-Quelle wählen (Mikrofon/System/Beide)
   - Bitrate einstellen (64-320 kbps)
   - Stream-Port festlegen (Standard: 420)
   - Stream-Name eingeben

3. **Streaming starten:**
   - "Stream Starten" klicken
   - Mikrofon-Berechtigung erteilen
   - Pegelmeter überwachen

### Management-Commands

```bash
cd /home/pi/pimic/audio

# Service starten
./scripts/service.sh start

# Status prüfen
./scripts/service.sh status

# Logs anzeigen
./scripts/service.sh logs

# Service stoppen
./scripts/service.sh stop

# Neustart
./scripts/service.sh restart

# System testen
./scripts/service.sh test
```

## 🌐 Netzwerk-Konfiguration

### Ports

- **6969**: Web-Interface (HTTP)
- **420+**: Audio-Streams (TCP)
- **5353**: mDNS Discovery (UDP)
- **6970**: UDP Broadcast Discovery

### Firewall

```bash
sudo ufw allow 6969/tcp comment "PIMIC Audio Web"
sudo ufw allow 420:65535/tcp comment "PIMIC Audio Streams"  
sudo ufw allow 5353/udp comment "mDNS Discovery"
```

### Netzwerk-Discovery

Der Service verwendet mehrere Discovery-Methoden:

1. **mDNS/Bonjour**: Automatische Service-Ankündigung
2. **UDP Broadcast**: Fallback für mDNS-Probleme
3. **Service-Liste**: Web-Interface zeigt alle gefundenen Streams

## 🔧 Konfiguration

### Server-Konfiguration

**ecosystem.config.js:**
```javascript
env: {
  NODE_ENV: 'production',
  PORT: 6969,           // Web-Interface Port
  STREAM_PORT: 420,     // Standard Stream-Port
  MAX_BITRATE: 320,     // Maximale Bitrate
  MIN_BITRATE: 64       // Minimale Bitrate
}
```

### Audio-System

**PulseAudio konfigurieren:**
```bash
# Standard-Mikrofon setzen
pactl set-default-source [SOURCE_NAME]

# Verfügbare Quellen anzeigen
pactl list short sources

# Audio-Test
arecord -f cd -t wav -d 5 test.wav
```

## 📊 API-Endpunkte

### REST API

```bash
# Aktuelle Streams abrufen
GET /api/streams

# Server-Konfiguration
GET /api/config

# Netzwerk-Informationen
GET /api/network

# Health Check
GET /health
```

### WebSocket Events

**Client → Server:**
- `start-stream`: Stream starten
- `stop-stream`: Stream stoppen
- `audio-data`: Audio-Daten senden
- `audio-level`: Pegeldaten senden

**Server → Client:**
- `stream-started`: Stream bestätigung
- `stream-stopped`: Stream gestoppt
- `stream-list-updated`: Stream-Liste aktualisiert
- `audio-level-update`: Pegel-Updates

## 🎵 Audio-Features

### Unterstützte Formate
- **Sample Rate**: 44.1 kHz
- **Channels**: Stereo (2)
- **Bitrate**: 64-320 kbps
- **Encoding**: PCM/Opus (Browser-abhängig)

### Audio-Quellen
- **Mikrofon**: Standard-Mikrofon-Eingabe
- **System-Audio**: Desktop-Audio (erfordert Berechtigung)
- **Kombiniert**: Mikrofon + System gemischt

### Pegelmeter
- **dB-Range**: -60 dB bis 0 dB
- **Farb-Kodierung**: 
  - Grün: < -20 dB (sicher)
  - Gelb: -20 bis -6 dB (warnung)
  - Rot: > -6 dB (übersteuert)
- **Peak-Hold**: Weißer Balken zeigt Spitzenwerte

## 🔍 Troubleshooting

### Häufige Probleme

1. **Mikrofon-Berechtigung:**
   - Browser-Berechtigung erteilen
   - HTTPS für erweiterte Features verwenden

2. **Audio nicht verfügbar:**
   ```bash
   # PulseAudio neustarten
   pulseaudio --kill
   pulseaudio --start
   
   # Benutzer zu audio-Gruppe hinzufügen
   sudo usermod -a -G audio pi
   ```

3. **Netzwerk-Discovery funktioniert nicht:**
   ```bash
   # Avahi installieren
   sudo apt-get install avahi-daemon
   sudo systemctl enable avahi-daemon
   sudo systemctl start avahi-daemon
   ```

4. **Port-Konflikte:**
   ```bash
   # Ports prüfen
   sudo netstat -tlnp | grep :6969
   sudo netstat -tlnp | grep :420
   ```

### Logs prüfen

```bash
# Service-Logs
./scripts/service.sh logs

# Systemd-Logs  
journalctl -u pimic-audio.service -f

# PM2-Logs
pm2 logs pimic-audio-streaming

# Audio-System
journalctl -u pulseaudio.service
```

## 🚀 Deployment

### PM2 Deployment

```bash
# Produktions-Start
pm2 start ecosystem.config.js --env production

# Auto-Start bei Boot
pm2 startup
pm2 save

# Monitoring
pm2 monit
```

### Systemd Service

```bash
# Service aktivieren
sudo systemctl enable pimic-audio.service

# Service starten
sudo systemctl start pimic-audio.service

# Status prüfen
sudo systemctl status pimic-audio.service
```

## 🔒 Sicherheit

### Netzwerk-Sicherheit
- Service läuft nur im lokalen Netzwerk
- Keine externe Internet-Verbindung erforderlich
- Firewall-Regeln beschränken Zugriff

### Audio-Berechtigungen
- Browser-Berechtigungen erforderlich
- Mikrofon-Zugriff nur bei aktiver Nutzung
- Keine permanente Aufzeichnung

## 📈 Performance

### System-Anforderungen
- **CPU**: Minimal 500 MHz ARM
- **RAM**: 256 MB (512 MB empfohlen)
- **Netzwerk**: 100 Mbit/s LAN empfohlen
- **Audio**: USB-Audio-Interface empfohlen

### Optimierung
- Niedrigere Bitrate für bessere Performance
- PM2 Cluster-Modus für höhere Last
- Audio-Puffer-Einstellungen anpassen

## 📝 Lizenz

MIT License - siehe LICENSE-Datei für Details.

## 🤝 Beitragen

1. Fork das Repository
2. Feature-Branch erstellen
3. Änderungen committen
4. Pull Request erstellen

## 📞 Support

- **Issues**: GitHub Issues verwenden
- **Dokumentation**: README.md und Code-Kommentare
- **Logs**: Service-Logs für Debugging nutzen

---

**🎵 PIMIC Audio Streaming - Professioneller Audio-Service für Raspberry Pi**