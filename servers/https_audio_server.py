#!/usr/bin/env python3
"""
HTTPS Audio Server
Saubere HTTPS Implementation für Audio Streaming - KEINE WebSockets!
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

class HTTPSAudioHandler(BaseHTTPRequestHandler):
    """HTTPS Request Handler für Audio Streaming"""
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.serve_index()
        elif parsed_path.path == '/stream':
            self.serve_audio_stream()
        elif parsed_path.path == '/status':
            self.serve_status()
        else:
            self.send_error(404, "Not Found")
    
    def serve_index(self):
        """Serve main page"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>HTTPS Audio Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #fff; }
                h1 { color: #00ff00; }
                .status { background: #333; padding: 20px; border-radius: 8px; margin: 20px 0; }
                button { background: #007700; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background: #009900; }
            </style>
        </head>
        <body>
            <h1>🎵 HTTPS Audio Server</h1>
            <div class="status">
                <h3>Server Status</h3>
                <p>Status: <span style="color: #00ff00;">ONLINE</span></p>
                <p>Protocol: <span style="color: #00ff00;">HTTPS</span></p>
                <p>Port: <span style="color: #00ff00;">42069</span></p>
                <p>Time: <span id="time"></span></p>
            </div>
            
            <div class="status">
                <h3>Audio Stream</h3>
                <p>Stream URL: <code>https://localhost:42069/stream</code></p>
                <button onclick="testStream()">Test Stream</button>
            </div>
            
            <script>
                function updateTime() {
                    document.getElementById('time').textContent = new Date().toLocaleString();
                }
                setInterval(updateTime, 1000);
                updateTime();
                
                function testStream() {
                    fetch('/stream')
                        .then(response => {
                            if (response.ok) {
                                alert('Stream connection successful!');
                            } else {
                                alert('Stream connection failed!');
                            }
                        })
                        .catch(err => alert('Error: ' + err));
                }
            </script>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', str(len(html_content)))
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_audio_stream(self):
        """Serve audio stream endpoint"""
        # Hier würde der echte Audio Stream kommen
        # Für jetzt senden wir einen Mock Response
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Mock audio data - hier würde echte Audio-Daten kommen
        logger.info("Audio stream request received")
        mock_data = b"AUDIO_STREAM_DATA_" + str(int(time.time())).encode()
        self.wfile.write(mock_data)
    
    def serve_status(self):
        """Serve status endpoint"""
        status = {
            "status": "online",
            "protocol": "https",
            "port": 42069,
            "timestamp": datetime.now().isoformat(),
            "server": "HTTPS Audio Server"
        }
        
        response = json.dumps(status, indent=2)
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode())
    
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
    """Start HTTPS Audio Server"""
    port = 42069
    
    logger.info("🚀 Starte HTTPS Audio Server...")
    logger.info(f"Port: {port}")
    
    try:
        # SSL Context erstellen
        ssl_context = create_ssl_context()
        
        # Server erstellen
        server = HTTPServer(('0.0.0.0', port), HTTPSAudioHandler)
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
        
        logger.info(f"✅ HTTPS Audio Server läuft auf Port {port}")
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