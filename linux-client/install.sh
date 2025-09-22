#!/bin/bash
# Installation script für den sadistischen Virtual Microphone Client
# Für Raspberry Pi 3B mit Raspbian Lite

echo "😈 Installing Sadistic Virtual Microphone Client..."
echo "=================================================="

# Update package list
echo "📦 Updating package list..."
sudo apt update

# Install required system packages
echo "🔧 Installing system dependencies..."
sudo apt install -y python3 python3-pip pulseaudio-utils ffmpeg

# Install Python requirements
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Make script executable
echo "⚡ Making script executable..."
chmod +x virtual_mic_client.py

# Create systemd service (optional)
echo "🛠️  Creating systemd service..."
sudo tee /etc/systemd/system/virtual-mic.service > /dev/null <<EOF
[Unit]
Description=Sadistic Virtual Microphone Client
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 $(pwd)/virtual_mic_client.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  ./virtual_mic_client.py    # Interactive mode"
echo ""
echo "Enable auto-start (optional):"
echo "  sudo systemctl enable virtual-mic"
echo "  sudo systemctl start virtual-mic"
echo ""
echo "😈 Ready for sadistic audio streaming experiments!"