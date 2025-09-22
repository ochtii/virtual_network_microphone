# Sadistic Audio Streaming Tool - Copilot Instructions

## 🎭 Projekt-Übersicht
Experimentelles Audio-Streaming System mit Android App, Web App und Linux Client für lokale Netzwerk-Übertragung.

## 🏗️ System-Architektur

### Audio-Sender (Alternativen):
1. **Android App** → Startet HTTP Server auf Port 42069, streamt Mikrofon-Audio
2. **Web App** → Startet lokalen HTTP Server auf Port 42069, streamt Mikrofon-Audio

### Audio-Empfänger:
- **Linux Client** → Verbindet sich zu IP:42069, erstellt PulseAudio Virtual Mics ("laber-lanze", "brüllwürfel")

## 🌐 Port-Konfiguration

### Web App (NetCast Audio Pro):
- **HTTPS Port:** 8443 (für Browser-Interface)
- **Selbstsigniertes SSL-Zertifikat** für lokales Netzwerk
- **Mikrofon-Zugriff** nur über HTTPS möglich (Browser-Sicherheit)

### Audio-Streaming:
- **Standard Port:** 42069 (HTTP Audio Stream)
- **NICHT ÄNDERN!** Konsistenz zwischen Android App und Web App
- **Mit HTTPS Unterstützung** für sichere Übertragung

### Linux Client:
- **Verbindet zu:** http://SENDER_IP:42069/stream
- **Erstellt Virtual Mics:** laber-lanze, brüllwürfel, etc.

## 💻 Entwicklungsumgebung

### Windows PowerShell (EINZIGE Shell):
```powershell
# ✅ Richtig - PowerShell Escaping
ssh user@host "cd /path && command"

# ✅ Richtig - Anführungszeichen
Invoke-WebRequest -Uri "https://192.168.188.90:8443"

# ❌ Falsch - Bash-Syntax in PowerShell
ssh user@host 'single quotes'  # Funktioniert nicht!
curl -I http://url/             # Ist Invoke-WebRequest Alias!
```

### Wichtige PowerShell-Regeln:
- **Doppelte Anführungszeichen** für Strings
- **SSH Commands** in Anführungszeichen wrappen
- **Escaping** mit Backticks oder doppelte Quotes
- **curl** ist Alias für `Invoke-WebRequest` (andere Syntax!)

## 🔧 Technische Details

### Web App Architektur:
- **FALSCH:** Web App sendet an externen Server → Server leitet weiter
- **RICHTIG:** Web App startet lokalen HTTP Server → Linux Client verbindet direkt

### Audio-Flow:
1. Web App: Mikrofon → Web Audio API → Lokaler HTTP Server Port 42069
2. Linux Client: GET http://WEB_APP_IP:42069/stream → PulseAudio Virtual Mic

### SSL/HTTPS:
- **Web Interface:** HTTPS Port 8443 (Browser-Zugriff, Mikrofon-Berechtigung)
- **Audio Stream:** HTTP/HTTPS Port 42069 (je nach Implementation)
- **Zertifikat:** Selbstsigniert für 192.168.188.90, localhost, raspberrypi

## 🚫 Häufige Fehler

### ❌ Falsche Architektur:
```
Web App → HTTP POST → Pi Server → HTTP GET → Linux Client
```

### ✅ Richtige Architektur:
```
Web App (lokaler HTTP Server) ← HTTP GET ← Linux Client
```

### ❌ Shell-Probleme:
- Bash-Syntax in PowerShell verwenden
- Falsche Anführungszeichen
- curl statt Invoke-WebRequest

### ❌ Port-Verwirrung:
- Audio-Stream Port ändern (muss 42069 bleiben!)
- HTTP statt HTTPS für Web Interface
- Browser blockiert Mikrofon-Zugriff

## 🎯 Deployment-Ziele

### Raspberry Pi:
- **Web App HTTPS Interface** auf Port 8443
- **SSL-Zertifikat** installiert
- **KEIN separater Audio-Server** notwendig!
- **PM2 Process Manager** - NIEMALS bestehende Prozesse stoppen/ändern!
  - PM2 Path: `/home/ochtii/.nvm/versions/node/v22.19.0/bin/pm2`
  - Bestehende Prozesse: auto-deploy, gusch-app, gusch-realtime-monitor
  - **WARNUNG:** Diese Prozesse NIEMALS berühren, stoppen oder ändern!

### Windows Development:
- **Nur PowerShell** verwenden
- **Proper Escaping** beachten
- **HTTPS Web App** testen

### Integration Test:
1. Web App öffnen: https://192.168.188.90:8443
2. Audio-Stream starten (lokaler Server auf Port 42069)
3. Linux Client verbinden: http://WEB_APP_DEVICE_IP:42069/stream
4. Virtual Mics erscheinen: laber-lanze, brüllwürfel

## 🎭 Sadistic Development Style
- **Experimental** und **unkonventionell**
- **Lokale Netzwerk-Hacks** bevorzugt
- **Selbstsignierte Zertifikate** für schnelle SSL
- **Sadistische Namen** für Virtual Mics
- **Port 42069** als Audio-Standard (nicht ändern!)

## 🔍 Debugging-Hinweise

### PowerShell Network Tests:
```powershell
# SSL Certificate Test
Invoke-WebRequest -Uri "https://192.168.188.90:8443" -SkipCertificateCheck

# Port Check
Test-NetConnection -ComputerName 192.168.188.90 -Port 42069

# SSH Commands (proper escaping)
ssh user@host "netstat -tulpn | grep :42069"
```

### Audio-Stream Validation:
1. Web App startet lokalen Server → Port 42069 listening
2. Browser kann Mikrofon zugreifen → HTTPS erforderlich
3. Linux Client kann Stream empfangen → HTTP GET successful
4. Virtual Mics erstellt → PulseAudio Integration

---
*Experimentierfreudige amerikanische Sadisten approved! 🎭*