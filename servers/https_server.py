#!/usr/bin/env python3
"""
HTTPS Web Interface Server
Saubere HTTPS Implementation für Web Interface - KEINE WebSockets!
"""

import ssl
import os
import sys
import json
import time
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HTTPSWebHandler(BaseHTTPRequestHandler):
    """HTTPS Request Handler für Web Interface"""
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_main_page()
        elif parsed_path.path == '/api/status':
            self.serve_api_status()
        elif parsed_path.path == '/api/config':
            self.serve_api_config()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/start-stream':
            self.handle_start_stream()
        elif parsed_path.path == '/api/stop-stream':
            self.handle_stop_stream()
        else:
            self.send_error(404, "Not Found")
    
    def serve_main_page(self):
        """Serve main web interface"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>NetCast Audio Pro</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', sans-serif; 
                    background: linear-gradient(135deg, #1a1a1a, #2d2d2d); 
                    color: #fff; 
                    min-height: 100vh;
                }
                
                .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
                
                .header {
                    text-align: center;
                    margin-bottom: 40px;
                    padding: 30px;
                    background: rgba(0,0,0,0.3);
                    border-radius: 15px;
                    border: 1px solid #333;
                }
                
                .title {
                    font-size: 2.5em;
                    background: linear-gradient(45deg, #00ff00, #00aa00);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 10px;
                }
                
                .subtitle { color: #aaa; font-size: 1.2em; }
                
                .grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                
                .card {
                    background: rgba(0,0,0,0.4);
                    border: 1px solid #333;
                    border-radius: 15px;
                    padding: 25px;
                    transition: all 0.3s ease;
                }
                
                .card:hover {
                    border-color: #00ff00;
                    box-shadow: 0 5px 20px rgba(0,255,0,0.2);
                }
                
                .card h3 {
                    color: #00ff00;
                    margin-bottom: 15px;
                    font-size: 1.3em;
                }
                
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                
                .status-online { background: #00ff00; }
                .status-offline { background: #ff0000; }
                
                .btn {
                    background: linear-gradient(45deg, #007700, #00aa00);
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 1em;
                    transition: all 0.3s ease;
                    margin: 5px;
                }
                
                .btn:hover {
                    background: linear-gradient(45deg, #00aa00, #00dd00);
                    transform: translateY(-2px);
                }
                
                .btn.danger {
                    background: linear-gradient(45deg, #770000, #aa0000);
                }
                
                .btn.danger:hover {
                    background: linear-gradient(45deg, #aa0000, #dd0000);
                }
                
                .info-row {
                    display: flex;
                    justify-content: space-between;
                    margin: 10px 0;
                    padding: 8px 0;
                    border-bottom: 1px solid #333;
                }
                
                .info-label { color: #aaa; }
                .info-value { color: #fff; font-weight: bold; }
                
                .controls {
                    text-align: center;
                    margin: 20px 0;
                }
                
                #log {
                    background: rgba(0,0,0,0.6);
                    border: 1px solid #333;
                    border-radius: 8px;
                    padding: 15px;
                    height: 200px;
                    overflow-y: auto;
                    font-family: 'Consolas', monospace;
                    font-size: 0.9em;
                    margin-top: 20px;
                }
                
                .log-entry {
                    margin: 5px 0;
                    padding: 3px 0;
                }
                
                .log-info { color: #00ff00; }
                .log-error { color: #ff4444; }
                .log-warn { color: #ffaa00; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 class="title">🎵 NetCast Audio Pro</h1>
                    <p class="subtitle">HTTPS Audio Streaming Platform</p>
                </div>
                
                <div class="grid">
                    <div class="card">
                        <h3>🌐 Server Status</h3>
                        <div class="info-row">
                            <span class="info-label">Web Interface:</span>
                            <span class="info-value"><span class="status-indicator status-online"></span>ONLINE</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Audio Server:</span>
                            <span class="info-value"><span class="status-indicator" id="audio-status"></span><span id="audio-text">CHECKING...</span></span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Protocol:</span>
                            <span class="info-value">HTTPS</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Web Port:</span>
                            <span class="info-value">8443</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Audio Port:</span>
                            <span class="info-value">42069</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h3>🎤 Audio Control</h3>
                        <div class="controls">
                            <button class="btn" onclick="startAudioStream()">▶️ Start Stream</button>
                            <button class="btn danger" onclick="stopAudioStream()">⏹️ Stop Stream</button>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Stream URL:</span>
                            <span class="info-value">https://IP:42069/stream</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Status:</span>
                            <span class="info-value" id="stream-status">READY</span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h3>📊 System Log</h3>
                    <div id="log"></div>
                </div>
            </div>
            
            <script>
                function addLogEntry(message, type = 'info') {
                    const log = document.getElementById('log');
                    const entry = document.createElement('div');
                    entry.className = `log-entry log-${type}`;
                    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
                    log.appendChild(entry);
                    log.scrollTop = log.scrollHeight;
                }
                
                function checkAudioServer() {
                    fetch('https://localhost:42069/status')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('audio-status').className = 'status-indicator status-online';
                            document.getElementById('audio-text').textContent = 'ONLINE';
                            addLogEntry('Audio server is online', 'info');
                        })
                        .catch(err => {
                            document.getElementById('audio-status').className = 'status-indicator status-offline';
                            document.getElementById('audio-text').textContent = 'OFFLINE';
                            addLogEntry('Audio server is offline', 'error');
                        });
                }
                
                function startAudioStream() {
                    addLogEntry('Starting audio stream...', 'info');
                    fetch('/api/start-stream', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('stream-status').textContent = 'STREAMING';
                            addLogEntry('Audio stream started successfully', 'info');
                        })
                        .catch(err => {
                            addLogEntry('Failed to start audio stream: ' + err, 'error');
                        });
                }
                
                function stopAudioStream() {
                    addLogEntry('Stopping audio stream...', 'info');
                    fetch('/api/stop-stream', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('stream-status').textContent = 'STOPPED';
                            addLogEntry('Audio stream stopped', 'info');
                        })
                        .catch(err => {
                            addLogEntry('Failed to stop audio stream: ' + err, 'error');
                        });
                }
                
                // Initialize
                addLogEntry('NetCast Audio Pro initialized', 'info');
                checkAudioServer();
                setInterval(checkAudioServer, 10000); // Check every 10 seconds
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(html_content)))
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_api_status(self):
        """Serve API status"""
        status = {
            "status": "online",
            "protocol": "https",
            "port": 8443,
            "audio_port": 42069,
            "timestamp": datetime.now().isoformat(),
            "server": "NetCast Web Interface"
        }
        
        response = json.dumps(status, indent=2)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode())
    
    def serve_api_config(self):
        """Serve API configuration"""
        config = {
            "web_port": 8443,
            "audio_port": 42069,
            "protocol": "https",
            "audio_url": "https://localhost:42069/stream"
        }
        
        response = json.dumps(config, indent=2)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode())
    
    def handle_start_stream(self):
        """Handle start stream request"""
        result = {"status": "success", "message": "Stream started"}
        response = json.dumps(result)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode())
        
        logger.info("Audio stream start requested")
    
    def handle_stop_stream(self):
        """Handle stop stream request"""
        result = {"status": "success", "message": "Stream stopped"}
        response = json.dumps(result)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response.encode())
        
        logger.info("Audio stream stop requested")
    
    def log_message(self, format, *args):
        """Override to use proper logging"""
        logger.info(f"{self.address_string()} - {format % args}")

def create_ssl_context():
    """Create SSL context for HTTPS"""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Suche nach SSL Zertifikaten
    cert_file = None
    key_file = None
    
    # Mögliche Pfade für Zertifikate
    cert_paths = [
        'server.crt',
        '../server.crt',
        '../../server.crt',
        '/etc/ssl/certs/server.crt'
    ]
    
    key_paths = [
        'server.key',
        '../server.key', 
        '../../server.key',
        '/etc/ssl/private/server.key'
    ]
    
    for cert_path in cert_paths:
        if os.path.exists(cert_path):
            cert_file = cert_path
            break
    
    for key_path in key_paths:
        if os.path.exists(key_path):
            key_file = key_path
            break
    
    if not cert_file or not key_file:
        logger.error("SSL Zertifikate nicht gefunden!")
        logger.error("Benötigt: server.crt und server.key")
        sys.exit(1)
    
    logger.info(f"SSL Zertifikat: {cert_file}")
    logger.info(f"SSL Schlüssel: {key_file}")
    
    context.load_cert_chain(cert_file, key_file)
    return context

def main():
    """Start HTTPS Web Interface Server"""
    port = 8443
    
    logger.info("🚀 Starte HTTPS Web Interface...")
    logger.info(f"Port: {port}")
    
    try:
        # SSL Context erstellen
        ssl_context = create_ssl_context()
        
        # Server erstellen
        server = HTTPServer(('0.0.0.0', port), HTTPSWebHandler)
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
        
        logger.info(f"✅ HTTPS Web Interface läuft auf Port {port}")
        logger.info(f"🌐 URL: https://localhost:{port}")
        
        # Server starten
        server.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("🛑 Server gestoppt durch Benutzer")
    except Exception as e:
        logger.error(f"❌ Server Fehler: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()