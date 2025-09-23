# PIMIC Dashboard Autostart Setup

## Automatischer Start bei Systemboot

Das Dashboard wird automatisch beim Start des Raspberry Pi im Kiosk-Modus auf dem angeschlossenen Display angezeigt.

### Option 1: Openbox Autostart ✅
- **Datei**: `~/.config/openbox/autostart`
- **Funktion**: Startet Browser automatisch bei Desktop-Start
- **Status**: Konfiguriert und aktiv

### Option 2: systemd User Service ✅  
- **Service**: `pimic-dashboard.service`
- **Kommandos**:
  - Start: `systemctl --user start pimic-dashboard`
  - Stop: `systemctl --user stop pimic-dashboard`
  - Status: `systemctl --user status pimic-dashboard`
- **Status**: Service erstellt und aktiviert

### Option 3: Manueller Start ✅
- **Skript**: `~/start_dashboard_kiosk.sh`
- **Direkt ausführen**: `./start_dashboard_kiosk.sh`
- **Status**: Skript erstellt und ausführbar

## Technische Details

### Dashboard URL
- **Lokal**: http://localhost:3000
- **Netzwerk**: http://192.168.188.90:3000

### Browser-Konfiguration
- **Kiosk-Modus**: Vollbild ohne Browser-UI
- **Optimiert für**: 5" Touch-Display
- **Browser**: Chromium mit deaktivierten Features für Performance

### Automatische Services
1. **PM2 Services** werden automatisch gestartet falls nicht laufend
2. **Dashboard Verfügbarkeit** wird geprüft vor Browser-Start
3. **Browser Restart** bei Fehlern automatisch

### Startvorgang
1. System bootet
2. Desktop-Umgebung (Openbox) startet
3. Autostart-Skript wartet 10 Sekunden
4. PM2 Services werden gestartet (falls nötig)
5. Dashboard-Verfügbarkeit wird geprüft
6. Chromium startet im Kiosk-Modus
7. Dashboard wird automatisch angezeigt

## Test und Validierung

### Manueller Test
```bash
ssh ochtii@pi3
./start_dashboard_kiosk.sh
```

### Service Status prüfen
```bash
ssh ochtii@pi3
systemctl --user status pimic-dashboard
```

### PM2 Status prüfen
```bash
ssh ochtii@pi3
/home/ochtii/.npm-global/bin/pm2 status
```

## Problembehandlung

### Browser läuft nicht
- Display-Variable prüfen: `echo $DISPLAY`
- X-Server läuft: `ps aux | grep Xorg`

### Dashboard nicht erreichbar
- PM2 Services: `/home/ochtii/.npm-global/bin/pm2 status`
- Port prüfen: `curl http://localhost:3000`

### Autostart funktioniert nicht
- Openbox Autostart: `cat ~/.config/openbox/autostart`
- Service Status: `systemctl --user status pimic-dashboard`