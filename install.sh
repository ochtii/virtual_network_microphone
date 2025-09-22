#!/bin/bash

# Sadistic Audio Streaming Tool - Raspberry Pi Installation Script
# This script installs the Linux client for receiving Android audio streams
# and creating virtual microphones with sadistic names

set -e

echo "🎙️  Installing Sadistic Audio Streaming Tool on Raspberry Pi..."
echo "================================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ This script should not be run as root!${NC}"
   echo "Please run as regular user (ochtii)"
   exit 1
fi

echo -e "${BLUE}📦 Updating package lists...${NC}"
sudo apt update

echo -e "${BLUE}🔧 Installing required packages...${NC}"
sudo apt install -y \
    pulseaudio \
    pulseaudio-utils \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    wget \
    git

echo -e "${BLUE}🎵 Configuring PulseAudio...${NC}"
# Enable network modules for PulseAudio
sudo sed -i 's/#load-module module-native-protocol-tcp/load-module module-native-protocol-tcp auth-anonymous=1/' /etc/pulse/system.pa
sudo sed -i 's/#load-module module-zeroconf-publish/load-module module-zeroconf-publish/' /etc/pulse/system.pa

# Create virtual microphone configuration
echo -e "${YELLOW}🎤 Setting up virtual microphones with sadistic names...${NC}"

# Create PulseAudio configuration directory for user
mkdir -p ~/.config/pulse

# Create custom PulseAudio configuration
cat > ~/.config/pulse/default.pa << 'EOF'
# Load default configuration
.include /etc/pulse/default.pa

# Create virtual microphones with sadistic names
load-module module-null-sink sink_name=laber_lanze_sink sink_properties=device.description="Laber-Lanze"
load-module module-null-sink sink_name=bruellwuerfel_sink sink_properties=device.description="Brüllwürfel"
load-module module-null-sink sink_name=schrei_maschine_sink sink_properties=device.description="Schrei-Maschine"
load-module module-null-sink sink_name=terror_rohr_sink sink_properties=device.description="Terror-Rohr"

# Create virtual sources (microphones) from the sinks
load-module module-virtual-source source_name=laber_lanze master=laber_lanze_sink.monitor source_properties=device.description="Laber-Lanze-Mic"
load-module module-virtual-source source_name=bruellwuerfel master=bruellwuerfel_sink.monitor source_properties=device.description="Brüllwürfel-Mic"
load-module module-virtual-source source_name=schrei_maschine master=schrei_maschine_sink.monitor source_properties=device.description="Schrei-Maschine-Mic"
load-module module-virtual-source source_name=terror_rohr master=terror_rohr_sink.monitor source_properties=device.description="Terror-Rohr-Mic"
EOF

echo -e "${BLUE}🐍 Setting up Python environment...${NC}"
# Create virtual environment
python3 -m venv ~/virtual_mic_env

# Activate virtual environment and install packages
source ~/virtual_mic_env/bin/activate
pip install --upgrade pip
pip install -r ~/virtual_mic/requirements.txt

echo -e "${BLUE}🚀 Making scripts executable...${NC}"
chmod +x ~/virtual_mic/virtual_mic_client.py

echo -e "${BLUE}⚙️  Creating systemd service...${NC}"
# Create systemd service for auto-start
sudo tee /etc/systemd/system/sadistic-audio-client.service > /dev/null << EOF
[Unit]
Description=Sadistic Audio Streaming Client
After=network.target sound.target

[Service]
Type=simple
User=ochtii
Group=audio
WorkingDirectory=/home/ochtii/virtual_mic
Environment=PATH=/home/ochtii/virtual_mic_env/bin
ExecStart=/home/ochtii/virtual_mic_env/bin/python /home/ochtii/virtual_mic/virtual_mic_client.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${BLUE}🔄 Restarting PulseAudio...${NC}"
pulseaudio --kill
sleep 2
pulseaudio --start

echo -e "${GREEN}✅ Installation completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Restart the system: sudo reboot"
echo "2. Enable the service: sudo systemctl enable sadistic-audio-client"
echo "3. Start the service: sudo systemctl start sadistic-audio-client"
echo ""
echo -e "${YELLOW}🎤 Available virtual microphones:${NC}"
echo "• Laber-Lanze-Mic"
echo "• Brüllwürfel-Mic"
echo "• Schrei-Maschine-Mic"
echo "• Terror-Rohr-Mic"
echo ""
echo -e "${YELLOW}🔍 Useful commands:${NC}"
echo "• Check service status: sudo systemctl status sadistic-audio-client"
echo "• View logs: journalctl -u sadistic-audio-client -f"
echo "• List audio sources: pactl list sources short"
echo "• Test microphone: pactl info"
echo ""
echo -e "${GREEN}🎉 Ready to receive sadistic audio streams!${NC}"