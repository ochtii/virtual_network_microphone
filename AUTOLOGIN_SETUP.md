# Raspberry Pi Auto-Login und Dashboard Setup

## Konfiguration für automatischen Start ohne manuellen Login

### ✅ Durchgeführte Änderungen

#### 1. **Boot-Target geändert**
```bash
sudo systemctl set-default graphical.target
```
- **Vorher**: `multi-user.target` (nur Text-Konsole)
- **Nachher**: `graphical.target` (grafische Oberfläche)

#### 2. **Automatischer Login konfiguriert**
- **Datei**: `/etc/systemd/system/getty@tty1.service.d/autologin.conf`
- **Funktion**: Automatischer Login für User `ochtii` ohne Passwort-Eingabe
- **Service**: `getty@tty1.service` mit Autologin-Override

#### 3. **Automatischer Desktop-Start**
- **Service**: `auto-desktop.service`
- **Funktion**: Startet X11 und Openbox automatisch nach Login
- **Status**: Aktiviert und enabled für `graphical.target`

#### 4. **X11 Konfiguration**
- **Datei**: `~/.xinitrc`
- **Funktion**: 
  - Deaktiviert Screensaver und Powermanagement
  - Startet Openbox Window Manager
- **Backup-Methode**: `~/.bash_profile` startet X11 falls nötig

#### 5. **Dashboard Autostart**
- **Datei**: `~/.config/openbox/autostart`
- **Funktion**: 
  - Wartet auf System-Bereitschaft (10s)
  - Startet PM2 Services
  - Wartet auf Dashboard-Verfügbarkeit
  - Öffnet Chromium im Kiosk-Modus

### 🔄 Boot-Sequenz

1. **System Boot** → `graphical.target`
2. **Getty Service** → Automatischer Login `ochtii`
3. **Auto-Desktop Service** → Startet X11 + Openbox
4. **Openbox Autostart** → Startet Dashboard im Browser
5. **Chromium Kiosk** → Zeigt Dashboard auf 5" Display

### 🛠️ Services Status

```bash
# Prüfe Boot-Target
systemctl get-default
# Sollte zeigen: graphical.target

# Prüfe Autologin Service
sudo systemctl status getty@tty1

# Prüfe Desktop Service  
sudo systemctl status auto-desktop

# Prüfe PM2 Dashboard Services
/home/ochtii/.npm-global/bin/pm2 status
```

### 🧪 Test und Validierung

#### Nach dem nächsten Reboot sollte automatisch passieren:
1. ✅ Kein Login-Prompt (automatischer Login)
2. ✅ Grafische Oberfläche startet automatisch
3. ✅ Dashboard öffnet sich im Kiosk-Modus
4. ✅ 5" Display zeigt System-Metriken

#### Manueller Test vor Reboot:
```bash
# Service manuell starten
sudo systemctl start auto-desktop

# Dashboard-Skript testen
./start_dashboard_kiosk.sh

# X11 Status prüfen
ps aux | grep Xorg
```

### 🔧 Problembehandlung

#### Dashboard startet nicht:
```bash
# Prüfe X11
echo $DISPLAY
ps aux | grep Xorg

# Prüfe Openbox
ps aux | grep openbox

# Prüfe Browser
ps aux | grep chromium
```

#### Autologin funktioniert nicht:
```bash
# Prüfe getty Service
sudo systemctl status getty@tty1

# Prüfe Autologin-Konfiguration
cat /etc/systemd/system/getty@tty1.service.d/autologin.conf
```

#### Kein grafisches Display:
```bash
# Prüfe Boot-Target
systemctl get-default

# Prüfe Auto-Desktop Service
sudo systemctl status auto-desktop
```

### 📋 Konfigurationsdateien

| Datei | Zweck |
|-------|-------|
| `/etc/systemd/system/getty@tty1.service.d/autologin.conf` | Automatischer Login |
| `/etc/systemd/system/auto-desktop.service` | Desktop Auto-Start |
| `~/.xinitrc` | X11 Konfiguration |
| `~/.bash_profile` | Backup X11 Start |
| `~/.config/openbox/autostart` | Dashboard Browser Start |

### 🎯 Ergebnis

Nach dem **nächsten Reboot** startet das System automatisch:
- ❌ **Kein** Login-Bildschirm
- ✅ **Direkt** grafische Oberfläche  
- ✅ **Automatisch** Dashboard im Kiosk-Modus
- ✅ **Vollbild** auf dem 5" Display
- ✅ **Live-Metriken** mit 300ms Updates und fließenden Farben

Das Display zeigt dauerhaft das Dashboard ohne jegliche Benutzerinteraktion! 🚀