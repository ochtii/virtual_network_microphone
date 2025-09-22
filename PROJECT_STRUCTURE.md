# Virtual Microphone Tools - Project Structure

```
virtual_mic/
├── README.md                           # Main project overview
├── SETUP_GUIDE.md                      # Complete setup instructions
│
├── android-streamer/                   # Android Audio Streaming App
│   ├── README.md                       # Android-specific documentation
│   ├── app/
│   │   ├── build.gradle                # Android dependencies
│   │   ├── src/main/
│   │   │   ├── AndroidManifest.xml     # App permissions & services
│   │   │   ├── java/com/sadistic/audiostreamer/
│   │   │   │   ├── MainActivity.java   # Main UI and controls
│   │   │   │   └── AudioStreamingService.java  # Background streaming service
│   │   │   └── res/
│   │   │       ├── layout/
│   │   │       │   └── activity_main.xml      # UI layout with evil theme
│   │   │       └── values/
│   │   │           └── strings.xml     # App strings & sadistic messages
│   │   └── proguard-rules.pro          # Build configuration
│   └── gradle/                         # Gradle wrapper files
│
└── linux-client/                      # Raspberry Pi Virtual Microphone Client
    ├── README.md                       # Linux client documentation  
    ├── virtual_mic_client.py           # Main Python script (interactive)
    ├── requirements.txt                # Python dependencies
    ├── install.sh                      # Automated installation script
    └── systemd/
        └── virtual-mic.service          # Optional systemd service
```

## Key Components

### Android App Features
- **MainActivity**: UI controls, audio level display, voice activation settings
- **AudioStreamingService**: Background audio capture and HTTP streaming
- **Evil UI Theme**: Dark theme with sadistic color scheme
- **Voice Activation**: Configurable threshold with "Hilfe mama, i hab kan akku" mode
- **Background Operation**: Continues streaming when minimized

### Linux Client Features  
- **Network Scanner**: Intelligent discovery of audio streams
- **Virtual Microphone Manager**: Creates up to 10 virtual audio inputs
- **Sadistic Naming**: Random names from predefined list
- **PulseAudio Integration**: Seamless integration with Linux audio system
- **Interactive CLI**: User-friendly menu system

### Documentation
- **Individual READMEs**: Component-specific setup and usage
- **Complete Setup Guide**: End-to-end installation and configuration
- **Troubleshooting**: Common issues and solutions
- **Security Notes**: Important considerations for responsible use

## Getting Started

1. **Read SETUP_GUIDE.md** for complete instructions
2. **Android**: Build and install the streaming app  
3. **Linux**: Run the installation script
4. **Test**: Start streaming and discover with client
5. **Enjoy**: Your sadistic audio streaming setup is ready! 😈