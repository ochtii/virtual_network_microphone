#!/bin/bash

# PIMIC Audio Streaming - Deployment Script
# Deploy the complete audio streaming service to Raspberry Pi

set -e

# Configuration
PI_HOST="raspi"
PI_USER="pi"
REMOTE_PATH="/home/pi/pimic"
LOCAL_PATH="D:/wlan-tools/pimic"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
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

echo "🎵 PIMIC Audio Streaming - Deployment"
echo "====================================="

# Check if SSH connection works
print_status "Testing SSH connection to ${PI_HOST}..."
if ! ssh -o ConnectTimeout=5 ${PI_USER}@${PI_HOST} "echo 'Connection test successful'" > /dev/null 2>&1; then
    print_error "Cannot connect to ${PI_HOST}. Please check:"
    echo "  - Raspberry Pi is running and connected"
    echo "  - SSH is enabled on the Pi" 
    echo "  - Hostname 'raspi' is resolvable (or update PI_HOST variable)"
    exit 1
fi
print_success "SSH connection to ${PI_HOST} successful"

# Create remote directories
print_status "Creating remote directories..."
ssh ${PI_USER}@${PI_HOST} "
    mkdir -p ${REMOTE_PATH}/audio/public
    mkdir -p ${REMOTE_PATH}/audio/scripts
    mkdir -p ${REMOTE_PATH}/logs
"

# Deploy audio service files
print_status "Deploying audio service files..."
scp -r ${LOCAL_PATH}/audio/* ${PI_USER}@${PI_HOST}:${REMOTE_PATH}/audio/

# Set proper permissions
print_status "Setting file permissions..."
ssh ${PI_USER}@${PI_HOST} "
    chmod +x ${REMOTE_PATH}/audio/scripts/*.sh
    chmod 644 ${REMOTE_PATH}/audio/*.js
    chmod 644 ${REMOTE_PATH}/audio/public/*
    chown -R ${PI_USER}:${PI_USER} ${REMOTE_PATH}
"

# Install Node.js dependencies
print_status "Installing Node.js dependencies..."
ssh ${PI_USER}@${PI_HOST} "
    cd ${REMOTE_PATH}/audio
    npm install --production --no-optional
"

# Install system service
print_status "Installing system service..."
ssh ${PI_USER}@${PI_HOST} "
    cd ${REMOTE_PATH}/audio
    
    # Stop existing services
    sudo systemctl stop pimic-audio.service 2>/dev/null || true
    pm2 stop pimic-audio-streaming 2>/dev/null || true
    
    # Install service
    if [ -f scripts/install_service.sh ]; then
        chmod +x scripts/install_service.sh
        ./scripts/install_service.sh
    else
        echo 'Installation script not found - manual setup required'
    fi
"

# Test the service
print_status "Testing service installation..."
ssh ${PI_USER}@${PI_HOST} "
    cd ${REMOTE_PATH}/audio
    ./scripts/service.sh test
"

# Start the service
print_status "Starting PIMIC Audio Streaming service..."
ssh ${PI_USER}@${PI_HOST} "
    cd ${REMOTE_PATH}/audio
    ./scripts/service.sh start
"

# Wait a moment for service to start
sleep 3

# Check service status
print_status "Checking service status..."
if ssh ${PI_USER}@${PI_HOST} "cd ${REMOTE_PATH}/audio && ./scripts/service.sh status" > /dev/null 2>&1; then
    print_success "Service is running successfully!"
else
    print_warning "Service may not be running properly - check logs"
fi

# Get Raspberry Pi IP
PI_IP=$(ssh ${PI_USER}@${PI_HOST} "hostname -I | awk '{print \$1}'")

echo ""
print_success "🎵 PIMIC Audio Streaming deployment completed!"
echo ""
echo "📋 Service Information:"
echo "   • Web Interface:    http://${PI_IP}:6969"
echo "   • Stream Ports:     420 and above"
echo "   • Service Status:   ${REMOTE_PATH}/audio/scripts/service.sh status"
echo "   • Service Logs:     ${REMOTE_PATH}/audio/scripts/service.sh logs"
echo ""
echo "🎧 How to use:"
echo "   1. Open http://${PI_IP}:6969 in your browser"
echo "   2. Select audio source (microphone/system)" 
echo "   3. Choose bitrate and port settings"
echo "   4. Click 'Stream Starten' to begin streaming"
echo "   5. Stream will be available to all devices in your network"
echo ""
echo "🛠️ Management:"
echo "   • Start:     ssh ${PI_USER}@${PI_HOST} 'cd ${REMOTE_PATH}/audio && ./scripts/service.sh start'"
echo "   • Stop:      ssh ${PI_USER}@${PI_HOST} 'cd ${REMOTE_PATH}/audio && ./scripts/service.sh stop'"
echo "   • Status:    ssh ${PI_USER}@${PI_HOST} 'cd ${REMOTE_PATH}/audio && ./scripts/service.sh status'"
echo "   • Logs:      ssh ${PI_USER}@${PI_HOST} 'cd ${REMOTE_PATH}/audio && ./scripts/service.sh logs'"
echo ""

# Check if service is accessible
print_status "Testing web interface accessibility..."
if curl -s --connect-timeout 5 "http://${PI_IP}:6969/health" > /dev/null 2>&1; then
    print_success "✅ Web interface is accessible at http://${PI_IP}:6969"
else
    print_warning "⚠️  Web interface may not be accessible yet (service still starting up)"
    echo "   Wait a few seconds and try: http://${PI_IP}:6969"
fi

echo ""
print_success "🚀 Deployment complete! Your PIMIC Audio Streaming service is ready to use."