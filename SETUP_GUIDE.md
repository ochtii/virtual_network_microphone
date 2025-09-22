# Virtual Microphone Tools - Complete Setup Guide 🎤😈

Ein diabolischer Setup-Guide für die komplette Virtual Microphone Tool Suite!

## 🚀 Quick Start

### 1. Android App Setup
```bash
cd android-streamer
# Open in Android Studio
# Build & Install APK
```

### 2. Linux Client Setup  
```bash
cd linux-client
chmod +x install.sh
./install.sh
```

### 3. Test the Evil Connection
1. **Android**: Start stream on port 42069
2. **Linux**: Run `./virtual_mic_client.py`
3. **Discover**: Find your Android stream
4. **Connect**: Create virtual microphone
5. **Use**: Select the sadistic microphone in any app

## 📋 Detailed Setup Instructions

### Android App (Detailed)

1. **Prerequisites**
   - Android device (API 23+)
   - Developer options enabled
   - USB debugging enabled

2. **Build Process**
   ```bash
   cd android-streamer
   # Android Studio:
   # File → Open → Select android-streamer folder
   # Build → Make Project
   # Run → Install on device
   ```

3. **First Run**
   - Grant microphone permission
   - Note the displayed IP address
   - Test with default port 42069

### Linux Client (Detailed)

1. **System Requirements**
   - Raspberry Pi 3B or similar Linux system
   - Raspbian Lite or Ubuntu
   - Network connection to Android device

2. **Installation**
   ```bash
   # Clone or copy the linux-client folder
   cd linux-client
   
   # Auto-install everything
   chmod +x install.sh
   ./install.sh
   
   # OR manual installation:
   sudo apt update
   sudo apt install python3 python3-pip pulseaudio-utils ffmpeg
   pip3 install -r requirements.txt
   chmod +x virtual_mic_client.py
   ```

3. **First Run**
   ```bash
   ./virtual_mic_client.py
   
   # Choose option 1: Quick scan
   # Connect to found streams
   # Check audio settings for new microphones
   ```

## 🔧 Configuration Options

### Android App Configuration

#### Port Settings
- **Default**: 42069 (recommended)
- **Alternative**: Any free port 1024-65535
- **Change**: Edit in app before starting stream

#### Voice Activation
- **Threshold**: -60 dB to 0 dB
- **Recommendation**: -30 dB for normal speech
- **Tip**: Test with different environments

#### Background Operation
- **Battery Optimization**: Disable for app
- **Protected Apps**: Add to whitelist (manufacturer-specific)

### Linux Client Configuration

#### Network Settings
```python
# In virtual_mic_client.py, modify these constants:
DEFAULT_PORT = 42069
SCAN_TIMEOUT = 2  # seconds
MAX_CONCURRENT_MICS = 10
```

#### Audio Quality
```bash
# Modify FFmpeg parameters in the script:
# Higher quality (more CPU):
'-ar', '48000', '-ac', '2'  # 48kHz stereo

# Lower latency (may drop audio):
'-probesize', '32', '-analyzeduration', '0'
```

## 🌐 Network Setup

### WLAN Configuration

1. **Same Network**: Both devices must be on same WLAN
2. **IP Range**: Usually 192.168.1.x or 192.168.0.x
3. **Firewall**: Ensure port 42069 is not blocked

### Firewall Settings

#### Android (if rooted)
```bash
# Usually no firewall by default
# If using firewall app, allow port 42069
```

#### Linux
```bash
# UFW (Ubuntu)
sudo ufw allow 42069

# iptables (manual)
sudo iptables -A INPUT -p tcp --dport 42069 -j ACCEPT
```

### Router Configuration
- **UPnP**: Can help with automatic port forwarding
- **Port Forwarding**: Not needed for local network
- **Guest Network**: May isolate devices (avoid)

## 🧪 Testing & Validation

### Test 1: Basic Connectivity
```bash
# From Linux, test Android stream:
curl -I http://ANDROID_IP:42069/audio

# Expected: HTTP/1.1 200 OK with audio content-type
```

### Test 2: Audio Pipeline
```bash
# Test FFmpeg connection:
ffmpeg -i http://ANDROID_IP:42069/audio -t 10 test_output.wav

# Should create a 10-second audio file
```

### Test 3: Virtual Microphone
```bash
# List PulseAudio sources:
pactl list sources short

# Should show virtual sources with sadistic names
```

### Test 4: Application Integration
```bash
# Test with arecord:
arecord -D pulse -d 5 -f cd test_mic.wav

# Choose virtual microphone in recording dialog
```

## 🎯 Usage Scenarios

### Scenario 1: Remote Microphone
- **Use Case**: Raspberry Pi in different room
- **Setup**: Android phone as mobile microphone
- **Application**: Home automation voice commands

### Scenario 2: Multiple Audio Sources
- **Use Case**: Multiple Android devices streaming
- **Setup**: Up to 10 virtual microphones
- **Application**: Multi-room audio input system

### Scenario 3: Voice Activation Testing
- **Use Case**: Test voice detection systems
- **Setup**: Use voice activation mode
- **Application**: Smart home voice trigger testing

### Scenario 4: Audio Recording Studio
- **Use Case**: Remote recording setup
- **Setup**: High-quality Android microphone streaming
- **Application**: Podcast or music recording

## 🐛 Troubleshooting Guide

### Android App Issues

#### App Crashes on Start
```bash
# Check logs:
adb logcat | grep AudioStreamer

# Common issues:
# - Missing microphone permission
# - Port already in use
# - Audio system problems
```

#### No Audio in Stream
- Check microphone permission
- Test with voice activation disabled
- Verify Android audio settings

#### Can't Connect from Linux
- Verify IP address (may change with DHCP)
- Check if port 42069 is accessible
- Test with different port number

### Linux Client Issues

#### No Streams Found
```bash
# Test network connectivity:
ping ANDROID_IP

# Test port manually:
telnet ANDROID_IP 42069

# Check network interface:
ip addr show
```

#### Virtual Microphones Not Created
```bash
# Check PulseAudio status:
pulseaudio --check

# Restart PulseAudio:
pulseaudio -k && pulseaudio --start

# Check for running PulseAudio:
ps aux | grep pulseaudio
```

#### FFmpeg Errors
```bash
# Test FFmpeg installation:
ffmpeg -version

# Test direct stream access:
ffmpeg -i http://ANDROID_IP:42069/audio -f null -

# Check for codec issues
```

#### Permission Denied
```bash
# Make script executable:
chmod +x virtual_mic_client.py

# Add user to audio group:
sudo usermod -a -G audio $USER
# (Logout/login required)
```

## 📊 Performance Optimization

### Android Optimizations
- **Battery**: Disable optimization for app
- **CPU**: Use lower sample rates if needed
- **Network**: Use 5GHz WiFi for better bandwidth

### Linux Optimizations
```bash
# Increase audio buffer:
echo "default-fragments = 8" >> ~/.pulse/daemon.conf
echo "default-fragment-size-msec = 25" >> ~/.pulse/daemon.conf

# Restart PulseAudio:
pulseaudio -k && pulseaudio --start
```

### Network Optimizations
- **Dedicated WLAN**: Use separate network for audio
- **QoS**: Prioritize audio traffic if router supports it
- **Distance**: Keep devices close for best connection

## 🔒 Security Considerations

### Network Security
- **Encryption**: Streams are unencrypted (HTTP)
- **Authentication**: No authentication implemented
- **Access Control**: Anyone on network can access streams

### Privacy Considerations
- **Microphone Access**: App has full microphone access
- **Network Broadcast**: Audio is broadcast on network
- **Storage**: No audio storage implemented

### Recommendations
- **Private Networks**: Only use on trusted networks
- **Firewall**: Consider restricting access by IP
- **Monitoring**: Monitor network traffic if needed

## 📈 Advanced Usage

### Custom Microphone Names
```python
# In virtual_mic_client.py, modify:
SADISTIC_MIC_NAMES = [
    'your-custom-name-1',
    'your-custom-name-2',
    # ... add your own names
]
```

### Systemd Service Configuration
```bash
# Edit service file:
sudo nano /etc/systemd/system/virtual-mic.service

# Auto-start on boot:
sudo systemctl enable virtual-mic

# Start service:
sudo systemctl start virtual-mic
```

### Multiple Network Interfaces
```bash
# Scan specific network:
# Modify get_local_network() in virtual_mic_client.py
# to return your desired network range
```

## 🎉 Success Indicators

### Android App Success
- ✅ Microphone permission granted
- ✅ Local IP displayed correctly  
- ✅ Stream status shows "Broadcasting evil"
- ✅ Audio level indicator responds to voice

### Linux Client Success
- ✅ Dependencies installed without errors
- ✅ Stream discovery finds Android device
- ✅ Virtual microphone creation succeeds
- ✅ Audio applications see sadistic microphone names

### End-to-End Success
- ✅ Audio from Android appears in Linux recording
- ✅ Latency is acceptable for use case
- ✅ Voice activation works as expected
- ✅ Multiple streams can be handled simultaneously

---

*"Congratulations, fellow sadistic audio engineer! You now have the power to stream voices across the network with maximum... 'efficiency'. Use your new powers responsibly... or not. 😈"*

## 📞 Support

If you encounter issues:
1. Check this complete setup guide
2. Review individual component READMEs
3. Test each component separately
4. Check network configuration
5. Embrace the chaos and experiment! 🎪

*Remember: "Vielleicht hilfts, probieren kannst es." - The official motto of experimental sadistic audio engineering.*