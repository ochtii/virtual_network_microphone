# Display Module - Python HTTP Server

Dieses Modul wurde von Node.js/Express auf einen einfachen Python HTTP Server umgestellt, um die Installation auf dem Raspberry Pi zu vereinfachen.

## Struktur

```
display/
├── main.py                     # Python tkinter GUI
├── http_server.py             # Python HTTP Server (ersetzt server.js)
├── public/                    # Statische Web-Dateien
│   ├── index.html
│   ├── app.js
│   └── style.css
└── scripts/                   # Start/Stop Scripts
    ├── start_all.sh          # Startet GUI + HTTP Server
    ├── stop_all.sh           # Stoppt alle Services
    ├── start_http_server.sh  # Nur HTTP Server
    ├── stop_http_server.sh   # Nur HTTP Server stoppen
    ├── restart_http_server.sh # HTTP Server neustarten
    ├── start_display.sh      # Original X11/GUI Script
    ├── stop_display.sh       # Original Stop Script
    └── restart_display.sh    # Original Restart Script
```

## Verwendung

### Komplett-Start (GUI + Web-Interface)
```bash
./scripts/start_all.sh
```

### Nur Web-Interface (HTTP Server)
```bash
./scripts/start_http_server.sh
```

### Nur Python GUI
```bash
python3 main.py
```

### Services stoppen
```bash
./scripts/stop_all.sh           # Stoppt alles
./scripts/stop_http_server.sh   # Nur HTTP Server
```

## API Endpunkte

Der Python HTTP Server stellt die gleichen API-Endpunkte bereit wie der ursprüngliche Node.js Server:

- `GET /api/system` - System-Metriken (CPU, RAM, Uptime)
- `GET /api/network` - Netzwerk-Metriken (Download/Upload)

## Vorteile der Python-Lösung

1. **Keine Node.js/npm Installation nötig** - Python ist auf Raspberry Pi standardmäßig installiert
2. **Geringerer Speicherverbrauch** - Python HTTP Server ist leichtgewichtiger als Express
3. **Einfachere Wartung** - Eine Programmiersprache weniger im Projekt
4. **Gleiche Funktionalität** - Alle API-Endpunkte und statische Dateien werden korrekt serviert

## Migration von Node.js

Die folgenden Dateien wurden entfernt:
- `server.js` (Node.js Express Server)
- `package.json` (npm Abhängigkeiten)
- `node_modules/` (npm Pakete)

Ersetzt durch:
- `http_server.py` (Python HTTP Server mit gleicher API)