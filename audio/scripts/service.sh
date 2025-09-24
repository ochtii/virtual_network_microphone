#!/bin/bash

# PIMIC Audio Streaming - Management Scripts
# Quick management commands for the audio streaming service

SERVICE_DIR="/home/ochtii/pimic/audio"
SERVICE_NAME="pimic-audio"
PM2_APP="pimic-audio-streaming"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "${CYAN}🎵 PIMIC Audio Streaming Management${NC}"
    echo -e "${CYAN}===================================${NC}"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if service directory exists
if [ ! -d "${SERVICE_DIR}" ]; then
    print_error "Service directory not found: ${SERVICE_DIR}"
    exit 1
fi

case "${1:-status}" in
    "start")
        print_header
        print_status "Starting PIMIC Audio Streaming service..."
        
        # Start via systemd
        if sudo systemctl start ${SERVICE_NAME}.service; then
            print_success "Systemd service started"
        else
            print_error "Failed to start systemd service"
        fi
        
        # Also try PM2 if available
        if command -v pm2 &> /dev/null && [ -f "${SERVICE_DIR}/ecosystem.config.js" ]; then
            cd "${SERVICE_DIR}"
            if pm2 start ecosystem.config.js --env production 2>/dev/null; then
                print_success "PM2 service started"
            fi
        fi
        
        sleep 2
        $0 status
        ;;
        
    "stop")
        print_header
        print_status "Stopping PIMIC Audio Streaming service..."
        
        # Stop PM2 if running
        if command -v pm2 &> /dev/null; then
            pm2 stop ${PM2_APP} 2>/dev/null && print_success "PM2 service stopped"
        fi
        
        # Stop systemd service
        if sudo systemctl stop ${SERVICE_NAME}.service; then
            print_success "Systemd service stopped"
        else
            print_error "Failed to stop systemd service"
        fi
        ;;
        
    "restart")
        print_header
        print_status "Restarting PIMIC Audio Streaming service..."
        
        $0 stop
        sleep 2
        $0 start
        ;;
        
    "status")
        print_header
        
        # System service status
        echo -e "\n${YELLOW}📊 System Service Status:${NC}"
        if sudo systemctl is-active --quiet ${SERVICE_NAME}.service; then
            print_success "Systemd service is running"
        else
            print_error "Systemd service is not running"
        fi
        
        # PM2 status
        if command -v pm2 &> /dev/null; then
            echo -e "\n${YELLOW}🔧 PM2 Status:${NC}"
            pm2 show ${PM2_APP} 2>/dev/null || echo "PM2 app not found"
        fi
        
        # Network status
        echo -e "\n${YELLOW}🌐 Network Status:${NC}"
        if netstat -tlnp | grep -q ":6969"; then
            print_success "Web interface listening on port 6969"
            echo "   Access at: http://$(hostname -I | awk '{print $1}'):6969"
        else
            print_error "Web interface not listening on port 6969"
        fi
        
        # Active streams
        STREAM_COUNT=$(netstat -tlnp | grep -c -E ":42[0-9]")
        if [ "$STREAM_COUNT" -gt 0 ]; then
            print_success "${STREAM_COUNT} active audio streams found"
        else
            print_status "No active audio streams"
        fi
        
        # Audio system
        echo -e "\n${YELLOW}🎧 Audio System:${NC}"
        if pgrep -x "pulseaudio" > /dev/null; then
            print_success "PulseAudio is running"
        else
            print_warning "PulseAudio not running"
        fi
        
        # Resource usage
        echo -e "\n${YELLOW}💻 Resource Usage:${NC}"
        if pgrep -f "node.*server.js" > /dev/null; then
            PID=$(pgrep -f "node.*server.js")
            CPU=$(ps -p $PID -o %cpu --no-headers 2>/dev/null | tr -d ' ')
            MEM=$(ps -p $PID -o %mem --no-headers 2>/dev/null | tr -d ' ')
            print_status "CPU: ${CPU}%, Memory: ${MEM}%"
        fi
        
        # Recent errors
        if [ -f "/home/ochtii/pimic/logs/audio-service-error.log" ]; then
            ERROR_COUNT=$(tail -n 100 /home/ochtii/pimic/logs/audio-service-error.log | wc -l)
            if [ "$ERROR_COUNT" -gt 0 ]; then
                print_warning "${ERROR_COUNT} recent errors found"
            fi
        fi
        ;;
        
    "logs")
        print_header
        print_status "PIMIC Audio Streaming Logs"
        echo ""
        
        # Service logs
        echo -e "${YELLOW}📋 Service Logs (last 20 lines):${NC}"
        if [ -f "/home/ochtii/pimic/logs/audio-service.log" ]; then
            tail -n 20 /home/ochtii/pimic/logs/audio-service.log
        else
            print_warning "Service log file not found"
        fi
        
        echo ""
        echo -e "${YELLOW}❌ Error Logs (last 10 lines):${NC}"
        if [ -f "/home/ochtii/pimic/logs/audio-service-error.log" ]; then
            tail -n 10 /home/ochtii/pimic/logs/audio-service-error.log
        else
            print_status "No error logs found"
        fi
        
        # PM2 logs if available
        if command -v pm2 &> /dev/null; then
            echo ""
            echo -e "${YELLOW}🔧 PM2 Logs (last 10 lines):${NC}"
            pm2 logs ${PM2_APP} --lines 10 2>/dev/null || print_status "PM2 logs not available"
        fi
        ;;
        
    "update")
        print_header
        print_status "Updating PIMIC Audio Streaming..."
        
        cd "${SERVICE_DIR}"
        
        # Stop service
        $0 stop
        
        # Update dependencies
        print_status "Updating Node.js dependencies..."
        npm update --production
        
        # Restart service
        print_status "Restarting service..."
        $0 start
        
        print_success "Update completed"
        ;;
        
    "test")
        print_header
        print_status "Testing PIMIC Audio Streaming setup..."
        
        # Test Node.js
        if node --version > /dev/null 2>&1; then
            print_success "Node.js: $(node --version)"
        else
            print_error "Node.js not found"
        fi
        
        # Test dependencies
        cd "${SERVICE_DIR}"
        if [ -f "package.json" ]; then
            print_success "Package.json found"
            if npm list --depth=0 > /dev/null 2>&1; then
                print_success "All dependencies installed"
            else
                print_error "Missing dependencies - run 'npm install'"
            fi
        else
            print_error "Package.json not found"
        fi
        
        # Test audio system
        if command -v aplay &> /dev/null; then
            print_success "ALSA audio system available"
        else
            print_warning "ALSA not found"
        fi
        
        if pgrep -x "pulseaudio" > /dev/null; then
            print_success "PulseAudio running"
        else
            print_warning "PulseAudio not running"
        fi
        
        # Test network
        if netstat --version > /dev/null 2>&1; then
            print_success "Network tools available"
        else
            print_warning "Network tools not found"
        fi
        
        # Test mDNS
        if command -v avahi-browse &> /dev/null; then
            print_success "Avahi/mDNS available"
        else
            print_warning "mDNS/Avahi not available - install avahi-daemon"
        fi
        ;;
        
    "install")
        print_header
        print_status "Installing missing dependencies..."
        
        # Install system packages
        sudo apt-get update
        sudo apt-get install -y build-essential libasound2-dev libavahi-compat-libdnssd-dev
        
        # Install Node dependencies
        cd "${SERVICE_DIR}"
        npm install --production
        
        print_success "Dependencies installed"
        ;;
        
    "help"|*)
        print_header
        echo ""
        echo -e "${YELLOW}Usage:${NC} $0 {command}"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo -e "  ${GREEN}start${NC}     - Start the audio streaming service"
        echo -e "  ${GREEN}stop${NC}      - Stop the audio streaming service"
        echo -e "  ${GREEN}restart${NC}   - Restart the audio streaming service"
        echo -e "  ${GREEN}status${NC}    - Show service status and system info"
        echo -e "  ${GREEN}logs${NC}      - Display recent logs"
        echo -e "  ${GREEN}test${NC}      - Test system configuration"
        echo -e "  ${GREEN}update${NC}    - Update service and dependencies"
        echo -e "  ${GREEN}install${NC}   - Install missing dependencies"
        echo -e "  ${GREEN}help${NC}      - Show this help message"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo -e "  $0 start"
        echo -e "  $0 status"
        echo -e "  $0 logs"
        echo ""
        echo -e "${YELLOW}Web Interface:${NC} http://$(hostname -I | awk '{print $1}'):6969"
        echo ""
        ;;
esac