#!/bin/bash
"""
SSL-Zertifikat zum Browser hinzufügen
Für lokale Entwicklung mit NetCast Audio Pro
"""

echo "🔒 SSL-ZERTIFIKAT INSTALLATION"
echo "====================================="

# Zertifikat zum lokalen Downloads-Ordner kopieren
CERT_FILE="/home/ochtii/virtual_mic/server.crt"
DOWNLOAD_DIR="$HOME/Downloads"

if [ -f "$CERT_FILE" ]; then
    cp "$CERT_FILE" "$DOWNLOAD_DIR/sadistic-audio-cert.crt"
    echo "✅ Zertifikat kopiert nach: $DOWNLOAD_DIR/sadistic-audio-cert.crt"
    echo ""
    echo "🔧 MANUELLE INSTALLATION NOTWENDIG:"
    echo "====================================="
    echo "1. 🌐 Browser öffnen"
    echo "2. ⚙️  Settings/Einstellungen → Privacy & Security → Certificates"
    echo "3. 📋 'View Certificates' oder 'Zertifikate anzeigen'"
    echo "4. ➕ 'Import' oder 'Importieren'"
    echo "5. 📁 Datei auswählen: $DOWNLOAD_DIR/sadistic-audio-cert.crt"
    echo "6. ✅ 'Trust this certificate for identifying websites'"
    echo ""
    echo "🎭 Danach funktioniert HTTPS ohne Warnung!"
    echo "🌐 Web App: https://192.168.188.90:8443"
    echo "🎤 Audio Server: https://192.168.188.90:42070"
else
    echo "❌ Zertifikat nicht gefunden: $CERT_FILE"
    echo "Erstelle zuerst ein Zertifikat mit:"
    echo "openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes -subj '/CN=192.168.188.90'"
fi

echo ""
echo "🔑 Zertifikat Details:"
if [ -f "$CERT_FILE" ]; then
    openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|DNS:|IP Address:|Not After)"
fi