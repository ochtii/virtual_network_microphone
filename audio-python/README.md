# 🎵 PIMIC Audio Streaming Service - Pure Python Version

Ein vollständiger Netzwerk-Audio-Streaming-Service, implementiert in reinem Python ohne externe Dependencies.

## 🚀 Features

- **🎧 Browser-zu-Netzwerk Audio Streaming** - Streame Audio vom Browser ins lokale Netzwerk
- **🐍 Pure Python** - Keine npm/node.js Dependencies erforderlich  
- **⚡ Raspberry Pi optimiert** - Leichtgewichtige Standard Library Implementierung
- **🌐 Web Interface** - Vollständige Steuerung über Browser-Interface
- **📊 Echtzeit Audio Meter** - Animierte dB-Anzeige mit Pegelanzeige
- **🔧 Konfigurierbare Ports** - Web Interface auf 6969, Streams auf 420+
- **🎛️ Mehrere Audio-Quellen** - Mikrofon, System Audio oder beide
- **🔊 Variable Bitrate** - 64-320 kbps einstellbar
- **📡 Network Discovery** - Automatische Service-Ankündigung
- **🛠️ PM2 Integration** - Professionelle Prozessverwaltung mit Auto-Restart
- **📁 Saubere Architektur** - Getrennte Template- und Static-Dateien

## 📂 Projekt-Struktur

```
audio-python/
├── pimic_minimal_server.py     # Hauptserver (Pure Python)
├── templates/
│   └── index.html             # Web Interface Template
├── static/
│   ├── style.css              # Responsive CSS (Python-grün)
│   └── app.js                 # Browser Audio Processing
├── install-pimic-audio.sh     # PM2 Installation Script
├── manage-pimic-audio.sh      # Service Management
└── README.md                  # Dokumentation
```

## 📋 Systemanforderungen

- **Python 3.6+** (Standard auf Raspberry Pi OS)
- **PM2** (wird automatisch installiert)
- **Node.js** (für PM2 - wird automatisch installiert)
- **Linux System** (getestet auf Raspberry Pi OS)
- **Netzwerk-Interface** (Ethernet/WiFi)

### 🔧 Dependencies

**Erforderlich:**
- Python 3 Standard Library (automatisch verfügbar)
- PM2 Process Manager (automatische Installation)

**Optional (Pi-spezifisch):**
```bash
sudo apt-get install alsa-utils pulseaudio
```

## 🛠️ Installation

### Automatische Installation

1. **Repository klonen oder Dateien herunterladen**
```bash
cd /tmp
# Dateien in Verzeichnis kopieren
```

2. **Installation ausführen**
```bash
chmod +x install-pimic-audio.sh
sudo ./install-pimic-audio.sh
```

**Installation erfolgt:**
- **PM2** Installation und Konfiguration
- **Service-Verzeichnis:** `/opt/pimic-audio/`
- **Templates:** `/opt/pimic-audio/templates/`
- **Static Files:** `/opt/pimic-audio/static/`
- **Logs:** `/var/log/pimic/`
- **PM2 Ecosystem:** Automatischer Start/Restart

3. **Service prüfen**
```bash
pm2 status pimic-audio
```

### Manuelle Installation

1. **Service-Verzeichnis erstellen**
```bash
sudo mkdir -p /opt/pimic-audio/templates /opt/pimic-audio/static
sudo cp pimic_minimal_server.py /opt/pimic-audio/
sudo cp -r templates/ static/ /opt/pimic-audio/
sudo chmod +x /opt/pimic-audio/pimic_minimal_server.py
```

2. **PM2 Service konfigurieren**
```bash
# PM2 global installieren falls nicht vorhanden
sudo npm install -g pm2

# Service starten
cd /opt/pimic-audio
pm2 start ecosystem.config.js
pm2 save
```

## 🎛️ Verwendung

### Web Interface

Öffne den Browser und navigiere zu:
- **Lokal:** http://localhost:6969
- **Netzwerk:** http://[PI-IP]:6969

### Service Management

**Mit Management-Script:**
```bash
chmod +x manage-pimic-audio.sh

./manage-pimic-audio.sh start      # Service starten
./manage-pimic-audio.sh stop       # Service stoppen
./manage-pimic-audio.sh restart    # Service neu starten
./manage-pimic-audio.sh status     # Status anzeigen
./manage-pimic-audio.sh logs       # Logs anzeigen
./manage-pimic-audio.sh network    # Netzwerk-Info
```

**Mit PM2 direkt:**
```bash
pm2 start pimic-audio     # Starten
pm2 stop pimic-audio      # Stoppen
pm2 restart pimic-audio   # Neu starten
pm2 status pimic-audio    # Status
pm2 monit                 # Live-Monitoring
```

### Logs

```bash
# PM2 Live-Logs
pm2 logs pimic-audio

# Letzte 50 Zeilen
pm2 logs pimic-audio --lines 50

# Log-Dateien direkt
tail -f /var/log/pimic/pimic-audio.log
```

## 📡 API Endpoints

### REST API

- **GET /** - Haupt-Web-Interface
- **GET /api/streams** - Aktive Streams auflisten
- **GET /api/config** - Service-Konfiguration
- **GET /api/network** - Netzwerk-Informationen
- **GET /health** - Health Check
- **POST /api/stream/start** - Stream starten
- **POST /api/stream/stop** - Stream stoppen
- **POST /api/audio/level** - Audio-Pegel senden

### Server-Sent Events

- **GET /api/events** - Echtzeit-Events (SSE)

## 🔧 Konfiguration

### Standard-Konfiguration

```python
CONFIG = {
    'web_port': 6969,           # Web Interface Port
    'default_stream_port': 420,  # Basis-Port für Streams
    'max_bitrate': 320,         # Maximale Bitrate (kbps)
    'min_bitrate': 64,          # Minimale Bitrate (kbps)
    'sample_rate': 44100,       # Sample Rate (Hz)
    'channels': 2,              # Audio-Kanäle
    'chunk_size': 1024          # Audio Chunk Size
}
```

### Anpassung

Editiere `/opt/pimic-audio/pimic_minimal_server.py` und ändere die CONFIG-Werte.

## 🌐 Netzwerk-Konfiguration

### Firewall (UFW)

```bash
sudo ufw allow 6969/tcp comment "PIMIC Audio Web Interface"
sudo ufw allow 420:520/tcp comment "PIMIC Audio Streams"
```

### Port-Übersicht

- **6969** - Web Interface & API
- **420+** - Audio Stream Ports (dynamisch zugewiesen)
- **6970** - UDP Service Discovery (optional)

## 🔍 Troubleshooting

### Service startet nicht

1. **Python-Version prüfen:**
```bash
python3 --version
```

2. **PM2-Status prüfen:**
```bash
pm2 status pimic-audio
```

3. **Ports prüfen:**
```bash
netstat -tlnp | grep 6969
```

4. **Logs analysieren:**
```bash
pm2 logs pimic-audio --lines 50
```

### Keine Web-Verbindung

1. **Service-Status:**
```bash
pm2 status pimic-audio
```

2. **Firewall prüfen:**
```bash
sudo ufw status
```

3. **Netzwerk-Konnektivität:**
```bash
curl http://localhost:6969/health
```

### Audio-Probleme

1. **Browser-Berechtigungen:** Mikrofon-Zugriff erlauben
2. **HTTPS:** Für Produktivumgebung HTTPS konfigurieren
3. **Audio-System:** ALSA/PulseAudio-Konfiguration prüfen

### PM2 Probleme

1. **PM2 neu installieren:**
```bash
sudo npm install -g pm2@latest
```

2. **PM2 Startup zurücksetzen:**
```bash
pm2 unstartup
pm2 startup
pm2 save
```

## 🔄 Updates

### Service aktualisieren

1. **Service stoppen:**
```bash
pm2 stop pimic-audio
```

2. **Neue Version kopieren:**
```bash
sudo cp pimic_minimal_server.py /opt/pimic-audio/
sudo cp -r templates/ static/ /opt/pimic-audio/
```

3. **Service starten:**
```bash
pm2 restart pimic-audio
```

### Deinstallation

**Mit Management-Script:**
```bash
./manage-pimic-audio.sh uninstall
```

**Manuell:**
```bash
pm2 stop pimic-audio
pm2 delete pimic-audio
pm2 save
sudo rm -rf /opt/pimic-audio
sudo rm -rf /var/log/pimic
```

## 🏗️ Architektur

### Komponenten

1. **HTTP Server** - Web Interface & API (Python http.server)
2. **Template Engine** - Jinja2-ähnliche Template-Verarbeitung
3. **Static File Server** - CSS/JavaScript Bereitstellung
4. **Audio Processing** - Browser Web Audio API
5. **Stream Management** - TCP Socket Server für Audio-Daten
6. **Network Discovery** - UDP Broadcast für Service-Ankündigung
7. **Real-time Communication** - Server-Sent Events (SSE)
8. **PM2 Process Management** - Automatischer Restart und Monitoring

### Datenfluss

```
Browser -> Web Audio API -> HTTP POST -> Python Server -> TCP Stream -> Network
```

### Datei-Struktur

```
/opt/pimic-audio/
├── pimic_minimal_server.py     # Hauptserver
├── templates/
│   └── index.html             # Web Interface Template
├── static/
│   ├── style.css              # CSS Styling
│   └── app.js                 # Browser JavaScript
└── ecosystem.config.js        # PM2 Konfiguration
```

## 🛡️ Sicherheit

- **No External Dependencies** - Reduziert Angriffsfläche
- **Standard Library Only** - Vertrauenswürdige Python-Implementierung
- **Separated Templates** - XSS-Schutz durch Template-Trennung
- **Local Network** - Beschränkt auf lokales Netzwerk
- **Port-Beschränkung** - Konfigurierbare Port-Bereiche
- **PM2 Process Isolation** - Sichere Prozessverwaltung

## 📄 Lizenz

MIT License - Siehe LICENSE-Datei für Details.

## 🤝 Beitragen

1. Fork des Repositories
2. Feature Branch erstellen (`git checkout -b feature/new-feature`)
3. Änderungen committen (`git commit -am 'Add new feature'`)
4. Branch pushen (`git push origin feature/new-feature`)
5. Pull Request erstellen

## 📞 Support

- **Issues:** GitHub Issues verwenden
- **Diskussionen:** GitHub Discussions
- **Documentation:** Diese README-Datei

---

**🎵 PIMIC Audio Streaming - Pure Python Network Audio Solution 🎵**

*Entwickelt für Raspberry Pi, funktioniert überall wo Python läuft.*