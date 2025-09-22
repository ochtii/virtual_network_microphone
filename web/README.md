# NetCast Audio Pro - Web Application

Eine moderne Webanwendung für Audio-Streaming über das lokale Netzwerk.

## Features

### 🎙️ Core Funktionen
- **Stream Control**: Start/Stop Audio-Streaming über lokales Netzwerk
- **Voice Activation**: Schwellwert-basierte Aktivierung mit visueller Anzeige
- **Notfall-Mode**: "Hilfe Mama, i hab kan Akku"-Mode für maximale Qualität
- **Real-time Audio Level**: DJ-Mixer-Style LED-Bar mit dB-Anzeige

### 📊 Audio Meter
- **40-Segment LED-Bar**: Grün/Gelb/Orange/Rot Farbkodierung
- **Threshold Marker**: Visueller Schwellwert-Indikator
- **Real-time dB Display**: Präzise Pegelanzeige
- **Smooth Animations**: Flüssige LED-Übergänge

### ⚙️ Stream Settings
- **Bitrate**: 64/128/192/320 kbps
- **Qualität**: Niedrig/Mittel/Hoch
- **Auto Enhancement**: BETA Audio-Verbesserung
- **Port Configuration**: Standard 42069 (anpassbar)

### 🌐 Network Features
- **Auto IP Detection**: Automatische lokale IP-Erkennung
- **Stream URL Sharing**: Kopieren & Teilen Funktionen
- **Connection Monitoring**: Live Verbindungsanzahl
- **Uptime Tracking**: Stream-Laufzeit Anzeige

## Technologie Stack

### Frontend
- **HTML5**: Semantic markup mit Web Audio API
- **CSS3**: Moderne UI mit Glasmorphism-Design
- **JavaScript ES6+**: Klassen-basierte Architektur
- **WebRTC**: IP-Erkennung
- **MediaRecorder API**: Audio-Streaming

### Design
- **Responsive**: Mobile-first Design
- **Dark Theme**: Professionelle Optik
- **Animations**: Smooth transitions und LED-Effekte
- **Typography**: Segoe UI für beste Lesbarkeit

## Installation

```bash
# Klone das Repository
git clone <repository-url>

# Navigiere zum Web-Verzeichnis
cd virtual_mic/web

# Starte einen lokalen Server (optional)
python -m http.server 8080
# oder
npx serve .
```

## Verwendung

1. **Öffne** `index.html` in einem modernen Browser
2. **Erlaube** Mikrofon-Zugriff wenn gefragt
3. **Konfiguriere** Port und Einstellungen
4. **Starte** den Stream mit dem großen Button
5. **Teile** die Stream-URL mit anderen Geräten
6. **Überwache** Audio-Level in der LED-Bar

## Browser Kompatibilität

- ✅ **Chrome 80+**: Vollständig unterstützt
- ✅ **Firefox 75+**: Vollständig unterstützt  
- ✅ **Safari 14+**: Vollständig unterstützt
- ⚠️ **Edge Legacy**: Eingeschränkt
- ❌ **IE**: Nicht unterstützt

## Features im Detail

### Voice Activation
- **Threshold Slider**: -60dB bis 0dB Bereich
- **Visual Feedback**: Marker in LED-Bar
- **Real-time Processing**: Smooth activation/deactivation

### Emergency Mode
- **One-Click Activation**: Optimale Einstellungen
- **Max Quality**: 320kbps, High Quality
- **No Voice Gate**: Kontinuierlicher Stream
- **Visual Indicator**: Orange Warning-Style

### Audio Enhancement (BETA)
- **Noise Reduction**: Browser-native Processing
- **Dynamic Range**: Automatische Anpassung
- **Quality Boost**: Algorithmic Improvements

## API Integration

Die Web-App kann mit folgenden Endpunkten erweitert werden:

```javascript
// WebSocket für Real-time Streaming
const ws = new WebSocket('ws://localhost:42069/stream');

// HTTP POST für Audio-Chunks
fetch('/audio/upload', {
    method: 'POST',
    body: audioBlob
});
```

## Customization

### Themes
```css
:root {
    --primary-color: #2c3e50;
    --accent-color: #e74c3c;
    /* Weitere Variablen... */
}
```

### LED Bar Configuration
```javascript
const segmentCount = 40; // Anzahl LED-Segmente
const colorThresholds = [0.6, 0.8, 0.9]; // Farbübergänge
```

## Roadmap

- [ ] **WebSocket Integration**: Real-time Streaming
- [ ] **Multi-Channel Support**: Stereo/Surround
- [ ] **Recording**: Stream-to-File Funktionalität
- [ ] **Effects**: Real-time Audio-Effects
- [ ] **Analytics**: Detailed Stream-Statistiken

---

**NetCast Audio Pro** - Professional Network Audio Streaming 🎙️