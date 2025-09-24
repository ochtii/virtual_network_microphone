#!/bin/bash

# PIMIC Audio Streaming - Installation Script
# Installs the audio streaming service on Raspberry Pi

set -e

echo "🎵 PIMIC Audio Streaming - Installation"
echo "======================================"

# Configuration
USER="pi"
SERVICE_DIR="/home/${USER}/pimic/audio"
LOG_DIR="/home/${USER}/pimic/logs"
SYSTEMD_SERVICE="pimic-audio.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run this script as root"
    exit 1
fi

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    print_warning "This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create directories
print_status "Creating directories..."
mkdir -p "${SERVICE_DIR}"
mkdir -p "${LOG_DIR}"
mkdir -p "${SERVICE_DIR}/public"
mkdir -p "${SERVICE_DIR}/scripts"

# Check Node.js installation
print_status "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    print_status "Installing Node.js..."
    
    # Install Node.js via NodeSource repository
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    print_success "Node.js installed successfully"
else
    NODE_VERSION=$(node --version)
    print_success "Node.js ${NODE_VERSION} is already installed"
fi

# Check PM2 installation
print_status "Checking PM2 installation..."
if ! command -v pm2 &> /dev/null; then
    print_status "Installing PM2..."
    npm install -g pm2
    
    # Setup PM2 startup
    pm2 startup
    
    print_success "PM2 installed successfully"
else
    print_success "PM2 is already installed"
fi

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    libasound2-dev \
    libavahi-compat-libdnssd-dev \
    pulseaudio \
    pulseaudio-utils

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
cd "${SERVICE_DIR}"

# Copy package.json if it doesn't exist
if [ ! -f "package.json" ]; then
    print_status "Creating package.json..."
    cat > package.json << 'EOF'
{
  "name": "pimic-audio-streaming",
  "version": "1.0.0",
  "description": "PIMIC Network Audio Streaming Service",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "socket.io": "^4.7.2",
    "ws": "^8.13.0",
    "node-speaker": "^0.5.4",
    "pcm-util": "^3.0.0",
    "mdns": "^2.7.2",
    "cors": "^2.8.5",
    "body-parser": "^1.20.2"
  }
}
EOF
fi

npm install --production

# Create systemd service file
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/${SYSTEMD_SERVICE} > /dev/null << EOF
[Unit]
Description=PIMIC Audio Streaming Service
Documentation=https://github.com/pimic/audio-streaming
After=network.target
After=sound.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${SERVICE_DIR}
Environment=NODE_ENV=production
Environment=PORT=6969
Environment=STREAM_PORT=420
ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=5

# Logging
StandardOutput=append:${LOG_DIR}/audio-service.log
StandardError=append:${LOG_DIR}/audio-service-error.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${SERVICE_DIR} ${LOG_DIR}

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
sudo chown -R ${USER}:${USER} "${SERVICE_DIR}"
sudo chown -R ${USER}:${USER} "${LOG_DIR}"
chmod +x "${SERVICE_DIR}/scripts/"*.sh 2>/dev/null || true

# Enable and start the service
print_status "Enabling systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable ${SYSTEMD_SERVICE}

# Test PM2 configuration
if [ -f "ecosystem.config.js" ]; then
    print_status "Testing PM2 configuration..."
    pm2 start ecosystem.config.js --env production
    pm2 save
    pm2 stop pimic-audio-streaming
    print_success "PM2 configuration tested successfully"
fi

# Audio system setup
print_status "Configuring audio system..."
if command -v pulseaudio &> /dev/null; then
    # Start PulseAudio if not running
    if ! pgrep -x "pulseaudio" > /dev/null; then
        pulseaudio --start --log-target=syslog
        print_success "PulseAudio started"
    fi
    
    # Set default audio device
    pactl set-default-source alsa_input.usb-C-Media_Electronics_Inc._USB_Audio_Device-00.mono-fallback 2>/dev/null || \
    pactl set-default-source alsa_input.0.analog-mono 2>/dev/null || \
    print_warning "Could not set default audio source - please configure manually"
fi

# Firewall configuration
if command -v ufw &> /dev/null; then
    print_status "Configuring firewall..."
    sudo ufw allow 6969/tcp comment "PIMIC Audio Web Interface"
    sudo ufw allow 420:65535/tcp comment "PIMIC Audio Streams"
    sudo ufw allow 5353/udp comment "mDNS Discovery"
    print_success "Firewall rules added"
fi

# Create convenient management scripts
print_status "Creating management scripts..."

# Start script
cat > "${SERVICE_DIR}/scripts/start_audio.sh" << 'EOF'
#!/bin/bash
echo "🎵 Starting PIMIC Audio Streaming..."
sudo systemctl start pimic-audio.service
sudo systemctl status pimic-audio.service --no-pager -l
EOF

# Stop script
cat > "${SERVICE_DIR}/scripts/stop_audio.sh" << 'EOF'
#!/bin/bash
echo "🛑 Stopping PIMIC Audio Streaming..."
sudo systemctl stop pimic-audio.service
EOF

# Restart script
cat > "${SERVICE_DIR}/scripts/restart_audio.sh" << 'EOF'
#!/bin/bash
echo "🔄 Restarting PIMIC Audio Streaming..."
sudo systemctl restart pimic-audio.service
sudo systemctl status pimic-audio.service --no-pager -l
EOF

# Status script
cat > "${SERVICE_DIR}/scripts/status_audio.sh" << 'EOF'
#!/bin/bash
echo "📊 PIMIC Audio Streaming Status:"
echo "================================="
sudo systemctl status pimic-audio.service --no-pager -l
echo ""
echo "🌐 Network connections on port 6969:"
sudo netstat -tlnp | grep :6969 || echo "No connections on port 6969"
echo ""
echo "🎧 Active audio streams:"
sudo netstat -tlnp | grep -E ":42[0-9]" || echo "No active audio streams"
EOF

# Logs script
cat > "${SERVICE_DIR}/scripts/logs_audio.sh" << 'EOF'
#!/bin/bash
echo "📋 PIMIC Audio Streaming Logs:"
echo "=============================="
echo "Recent logs:"
tail -n 50 /home/pi/pimic/logs/audio-service.log
echo ""
echo "Recent errors:"
tail -n 20 /home/pi/pimic/logs/audio-service-error.log
EOF

# Make scripts executable
chmod +x "${SERVICE_DIR}/scripts/"*.sh

# Create web interface shortcut
cat > "${SERVICE_DIR}/open_interface.sh" << 'EOF'
#!/bin/bash
# Open PIMIC Audio Streaming web interface
if command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:6969"
elif command -v firefox &> /dev/null; then
    firefox "http://localhost:6969" &
elif command -v chromium-browser &> /dev/null; then
    chromium-browser "http://localhost:6969" &
else
    echo "🌐 Open your browser and navigate to: http://localhost:6969"
fi
EOF
chmod +x "${SERVICE_DIR}/open_interface.sh"

# Final setup
print_status "Final setup..."

# Add user to audio group
sudo usermod -a -G audio ${USER}

# Create desktop shortcut if desktop environment is available
if [ -d "/home/${USER}/Desktop" ]; then
    cat > "/home/${USER}/Desktop/PIMIC Audio.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=PIMIC Audio Streaming
Comment=Network Audio Streaming Service
Exec=/bin/bash ${SERVICE_DIR}/open_interface.sh
Icon=audio-card
Terminal=false
Categories=AudioVideo;Audio;
EOF
    chmod +x "/home/${USER}/Desktop/PIMIC Audio.desktop"
    print_success "Desktop shortcut created"
fi

echo ""
print_success "🎵 PIMIC Audio Streaming installation completed!"
echo ""
echo "📋 Quick Start:"
echo "   • Start service:    ${SERVICE_DIR}/scripts/start_audio.sh"
echo "   • Stop service:     ${SERVICE_DIR}/scripts/stop_audio.sh"
echo "   • View status:      ${SERVICE_DIR}/scripts/status_audio.sh"
echo "   • View logs:        ${SERVICE_DIR}/scripts/logs_audio.sh"
echo "   • Web interface:    http://localhost:6969"
echo ""
echo "🌐 Network access:"
echo "   • Local:            http://$(hostname -I | awk '{print $1}'):6969"
echo "   • Stream ports:     420 and above"
echo ""
echo "🎧 To start streaming:"
echo "   1. Open the web interface"
echo "   2. Select audio source (microphone/system)"
echo "   3. Choose bitrate and port"
echo "   4. Click 'Stream Starten'"
echo ""
print_warning "Note: You may need to log out and back in for audio group changes to take effect"
echo ""
echo "🚀 Starting the service now..."
sudo systemctl start ${SYSTEMD_SERVICE}

# Show final status
sleep 2
if sudo systemctl is-active --quiet ${SYSTEMD_SERVICE}; then
    print_success "PIMIC Audio Streaming is running! 🎵"
    echo "   Access the web interface at: http://$(hostname -I | awk '{print $1}'):6969"
else
    print_error "Service failed to start. Check logs with: journalctl -u ${SYSTEMD_SERVICE}"
fi