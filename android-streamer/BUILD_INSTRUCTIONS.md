# Android Audio Streamer - Build Anweisungen 😈

## Voraussetzungen

1. **Android Studio** (neueste Version)
2. **JDK 11 oder höher**
3. **Android SDK** (API Level 23+)

## Build-Prozess

### Option 1: Android Studio (Empfohlen)

1. **Android Studio öffnen**
2. **"Open an existing project"** wählen
3. **Ordner auswählen**: `D:\wlan-tools\virtual_mic\android-streamer`
4. **Gradle Sync** warten (kann bei erstem Mal länger dauern)
5. **Build → Make Project** (Strg+F9)
6. **Run → Run 'app'** (Strg+R) für direkte Installation

### Option 2: Command Line (Für Profis)

```powershell
cd "D:\wlan-tools\virtual_mic\android-streamer"

# Gradle Wrapper ausführbar machen (Linux/Mac)
chmod +x gradlew

# Windows: gradlew.bat verwenden
.\gradlew.bat build

# APK erstellen
.\gradlew.bat assembleDebug
```

### Option 3: Ohne Gradle Wrapper

Falls der Gradle Wrapper Probleme macht:

```powershell
# Mit lokal installiertem Gradle
gradle build
gradle assembleDebug
```

## APK Location

Nach erfolgreichem Build findest du die APK unter:
```
android-streamer\app\build\outputs\apk\debug\app-debug.apk
```

## Installation auf Gerät

### Via Android Studio
- Gerät via USB verbinden
- Developer Options aktivieren
- USB Debugging aktivieren  
- **Run** Button in Android Studio drücken

### Via ADB (Command Line)
```powershell
# APK installieren
adb install app\build\outputs\apk\debug\app-debug.apk

# Falls bereits installiert
adb install -r app\build\outputs\apk\debug\app-debug.apk
```

### Via File Transfer
1. APK auf Android-Gerät kopieren
2. "Install from unknown sources" aktivieren
3. APK-Datei antippen und installieren

## Troubleshooting

### Gradle Wrapper Fehler
Falls `gradlew` nicht funktioniert:
1. Android Studio verwenden (automatisches Download)
2. Oder Gradle manuell installieren

### Build Fehler
```powershell
# Clean build
.\gradlew.bat clean
.\gradlew.bat build

# Gradle Cache löschen
rm -rf ~/.gradle/caches/
```

### SDK Probleme
- Android Studio: Tools → SDK Manager
- Benötigte SDKs installieren (API 23-34)

### Permission Denied
```powershell
# Windows: Als Administrator ausführen
# Linux/Mac: chmod +x gradlew
```

## Dependencies

Die App verwendet folgende Bibliotheken:
- **androidx.appcompat** - UI Components
- **com.google.android.material** - Material Design
- **org.nanohttpd** - HTTP Server für Streaming

## Erste Schritte nach Installation

1. **App öffnen**: "Audio Streamer 😈"
2. **Mikrofon-Berechtigung** gewähren
3. **Lokale IP** notieren (wird angezeigt)
4. **"Start Evil Stream"** drücken
5. **Port 42069** ist nun aktiv für sadistische Audio-Experimente!

## Build-Konfiguration

- **Minimum SDK**: 23 (Android 6.0)
- **Target SDK**: 34 (Android 14)  
- **Build Tools**: 34.0.0
- **Gradle**: 8.0+
- **Package**: com.sadistic.audiostreamer

---

*"Ready to build your sadistic audio streaming empire? Let the evil compilation begin! 😈"*