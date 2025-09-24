#!/usr/bin/env python3
"""
PIMIC Audio Streaming Service - Python Minimal Version
Pure Python Audio Streaming ohne externe Dependencies 
Port 6969 für Web Interface, Browser-basierte Audio-Verarbeitung
"""

import asyncio
import json
import os
import sys
import time
import signal
import logging
import threading
import socket
import subprocess
import platform
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import base64
import hashlib

# Configuration
CONFIG = {
    'web_port': 6969,
    'default_stream_port': 420,
    'max_bitrate': 320,
    'min_bitrate': 64,
    'sample_rate': 44100,
    'channels': 2,
    'chunk_size': 1024
}

# Global state
active_streams: Dict[str, dict] = {}
connected_clients: Set[str] = set()  # Changed from websocket objects to client IDs
audio_levels: Dict[str, dict] = {}
server_running = True

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/pimic-audio.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class NetworkDiscovery:
    """Network service discovery and announcement"""
    
    def __init__(self):
        self.services = {}
        self.announcement_socket = None
        
    def start_discovery(self):
        """Start network discovery service"""
        try:
            # Create UDP socket for service announcement
            self.announcement_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.announcement_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Start announcement thread
            threading.Thread(target=self._announcement_loop, daemon=True).start()
            logger.info("Network discovery started")
            
        except Exception as e:
            logger.error(f"Network discovery start failed: {e}")
    
    def _announcement_loop(self):
        """Periodic service announcement"""
        while server_running:
            try:
                announcement = {
                    'type': 'pimic-audio-service',
                    'port': CONFIG['web_port'],
                    'stream_ports': list(range(CONFIG['default_stream_port'], CONFIG['default_stream_port'] + 100)),
                    'active_streams': len(active_streams),
                    'timestamp': time.time(),
                    'hostname': socket.gethostname()
                }
                
                message = json.dumps(announcement).encode('utf-8')
                
                # Broadcast to common network ranges
                broadcast_addresses = ['255.255.255.255', '192.168.1.255', '192.168.0.255']
                
                for addr in broadcast_addresses:
                    try:
                        self.announcement_socket.sendto(message, (addr, CONFIG['web_port'] + 1))
                    except:
                        pass  # Ignore broadcast errors
                
                time.sleep(30)  # Announce every 30 seconds
                
            except Exception as e:
                logger.error(f"Service announcement error: {e}")
                time.sleep(60)
    
    def get_network_info(self) -> List[dict]:
        """Get network interface information"""
        network_info = []
        try:
            # Get network interfaces using system commands
            if platform.system() == "Linux":
                result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
                # Parse IP addresses (simplified)
                lines = result.stdout.split('\n')
                current_interface = None
                
                for line in lines:
                    if line and not line.startswith(' '):
                        parts = line.split(':')
                        if len(parts) > 1:
                            current_interface = parts[1].strip()
                    elif 'inet ' in line and current_interface:
                        inet_part = line.strip().split('inet ')[1].split('/')[0]
                        if inet_part != '127.0.0.1':
                            network_info.append({
                                'interface': current_interface,
                                'address': inet_part,
                                'family': 'IPv4'
                            })
            else:
                # Windows fallback
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                network_info.append({
                    'interface': 'default',
                    'address': ip,
                    'family': 'IPv4'
                })
            
        except Exception as e:
            logger.error(f"Network info gathering failed: {e}")
            # Fallback
            network_info.append({
                'interface': 'eth0',
                'address': socket.gethostbyname(socket.gethostname()),
                'family': 'IPv4'
            })
        
        return network_info


class SimpleWebSocketHandler:
    """Minimale WebSocket-Implementierung ohne externe Dependencies"""
    
    def __init__(self):
        self.clients = {}  # client_id -> client_info
        
    def handle_websocket_handshake(self, request_handler):
        """Handle WebSocket handshake using HTTP upgrade"""
        try:
            # Extract WebSocket key
            websocket_key = request_handler.headers.get('Sec-WebSocket-Key', '')
            if not websocket_key:
                return False
                
            # Generate accept key
            accept_key = base64.b64encode(
                hashlib.sha1((websocket_key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()
            ).decode()
            
            # Send handshake response
            response = (
                'HTTP/1.1 101 Switching Protocols\\r\\n'
                'Upgrade: websocket\\r\\n'
                'Connection: Upgrade\\r\\n'
                f'Sec-WebSocket-Accept: {accept_key}\\r\\n'
                '\\r\\n'
            )
            
            request_handler.wfile.write(response.encode())
            return True
            
        except Exception as e:
            logger.error(f"WebSocket handshake failed: {e}")
            return False
    
    def add_client(self, client_id: str, client_info: dict):
        """Add WebSocket client"""
        self.clients[client_id] = client_info
        connected_clients.add(client_id)
        logger.info(f"WebSocket client connected: {client_id}")
    
    def remove_client(self, client_id: str):
        """Remove WebSocket client"""
        if client_id in self.clients:
            del self.clients[client_id]
        connected_clients.discard(client_id)
        
        # Clean up streams from this client
        streams_to_remove = [
            stream_id for stream_id, stream in active_streams.items()
            if stream.get('client_id') == client_id
        ]
        for stream_id in streams_to_remove:
            del active_streams[stream_id]
        
        logger.info(f"WebSocket client disconnected: {client_id}")
    
    def broadcast_message(self, message: dict):
        """Broadcast message to all clients (simplified)"""
        # In a real implementation, this would send WebSocket frames
        # For now, we'll use SSE (Server-Sent Events) as a fallback
        logger.info(f"Broadcasting message: {message['type']}")


class StreamServer:
    """TCP Stream Server für Audio-Daten"""
    
    def __init__(self, port: int):
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start stream server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            self.running = True
            
            threading.Thread(target=self._accept_loop, daemon=True).start()
            logger.info(f"Stream server started on port {self.port}")
            
        except Exception as e:
            logger.error(f"Stream server start failed: {e}")
    
    def _accept_loop(self):
        """Accept incoming connections"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"Stream client connected: {address}")
                
                # Handle client in separate thread
                threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket, address), 
                    daemon=True
                ).start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Stream accept error: {e}")
    
    def _handle_client(self, client_socket, address):
        """Handle stream client"""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                # Process audio data (simplified)
                logger.debug(f"Received audio data from {address}: {len(data)} bytes")
                
        except Exception as e:
            logger.error(f"Stream client error: {e}")
        finally:
            client_socket.close()
            logger.info(f"Stream client disconnected: {address}")
    
    def stop(self):
        """Stop stream server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()


class HTTPHandler(SimpleHTTPRequestHandler):
    """Enhanced HTTP handler for web interface and API"""
    
    def __init__(self, *args, **kwargs):
        self.network_discovery = NetworkDiscovery()
        self.websocket_handler = SimpleWebSocketHandler()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.serve_index()
        elif self.path == '/api/streams':
            self.serve_streams_api()
        elif self.path == '/api/config':
            self.serve_config_api()
        elif self.path == '/api/network':
            self.serve_network_api()
        elif self.path == '/api/events':
            self.serve_events_stream()
        elif self.path == '/health':
            self.serve_health()
        elif self.path.startswith('/static/'):
            self.serve_static_file()
        elif self.path == '/ws' or 'upgrade' in self.headers.get('Connection', '').lower():
            self.handle_websocket_upgrade()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/stream/start':
            self.handle_start_stream()
        elif self.path == '/api/stream/stop':
            self.handle_stop_stream()
        elif self.path == '/api/audio/level':
            self.handle_audio_level()
        else:
            self.send_error(404)
    
    def handle_websocket_upgrade(self):
        """Handle WebSocket upgrade request"""
        if self.websocket_handler.handle_websocket_handshake(self):
            client_id = f"{self.client_address[0]}_{int(time.time())}"
            self.websocket_handler.add_client(client_id, {
                'address': self.client_address,
                'connected_at': datetime.now()
            })
    
    def serve_events_stream(self):
        """Serve Server-Sent Events stream"""
        self.send_response(200)
        self.send_header('Content-type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Send initial config
        config_event = f"data: {json.dumps({'type': 'config', 'config': CONFIG})}\\n\\n"
        self.wfile.write(config_event.encode())
        self.wfile.flush()
        
        # Keep connection alive (simplified - in production use proper SSE)
        try:
            while server_running:
                # Send heartbeat
                heartbeat = f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\\n\\n"
                self.wfile.write(heartbeat.encode())
                self.wfile.flush()
                time.sleep(30)
        except:
            pass
    
    def handle_start_stream(self):
        """Handle stream start request"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            client_ip = self.client_address[0]
            stream_id = f"stream_{int(time.time() * 1000)}_{client_ip.replace('.', '_')}"
            stream_port = data.get('port', CONFIG['default_stream_port'])
            
            # Find available port
            while any(s['port'] == stream_port for s in active_streams.values()):
                stream_port += 1
                if stream_port > 65535:
                    stream_port = CONFIG['default_stream_port']
                    break
            
            stream_config = {
                'id': stream_id,
                'client_ip': client_ip,
                'port': stream_port,
                'bitrate': max(CONFIG['min_bitrate'], min(CONFIG['max_bitrate'], 
                              data.get('bitrate', 128))),
                'audio_source': data.get('audioSource', 'microphone'),
                'name': data.get('name', f'Stream from {client_ip}'),
                'start_time': datetime.now().isoformat(),
                'is_active': True
            }
            
            active_streams[stream_id] = stream_config
            
            # Start stream server
            stream_server = StreamServer(stream_port)
            stream_server.start()
            stream_config['server'] = stream_server
            
            # Send response
            response = {
                'success': True,
                'streamId': stream_id,
                'port': stream_port,
                'config': {k: v for k, v in stream_config.items() if k not in ['server']}
            }
            
            self.send_json_response(response)
            logger.info(f"Stream started: {stream_id} on port {stream_port}")
            
        except Exception as e:
            logger.error(f"Stream start error: {e}")
            self.send_json_response({'success': False, 'error': str(e)})
    
    def handle_stop_stream(self):
        """Handle stream stop request"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            stream_id = data.get('streamId')
            if stream_id in active_streams:
                stream = active_streams[stream_id]
                
                # Stop stream server
                if 'server' in stream:
                    stream['server'].stop()
                
                del active_streams[stream_id]
                
                response = {'success': True, 'streamId': stream_id}
                logger.info(f"Stream stopped: {stream_id}")
            else:
                response = {'success': False, 'error': 'Stream not found'}
            
            self.send_json_response(response)
            
        except Exception as e:
            logger.error(f"Stream stop error: {e}")
            self.send_json_response({'success': False, 'error': str(e)})
    
    def handle_audio_level(self):
        """Handle audio level update"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            stream_id = data.get('streamId')
            level = data.get('level', 0)
            db = data.get('db', -60)
            
            if stream_id in active_streams:
                audio_levels[stream_id] = {
                    'level': level,
                    'db': db,
                    'timestamp': time.time()
                }
            
            self.send_json_response({'success': True})
            
        except Exception as e:
            logger.error(f"Audio level error: {e}")
            self.send_json_response({'success': False, 'error': str(e)})
    
    def serve_index(self):
        """Serve main HTML page"""
        try:
            # Load HTML from template file
            template_path = Path(__file__).parent / 'templates' / 'index.html'
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except FileNotFoundError:
            logger.error(f"Template file not found: {template_path}")
            self.send_error(500, "Template not found")
        except Exception as e:
            logger.error(f"Error serving index: {e}")
            self.send_error(500, "Internal server error")
    
    def serve_streams_api(self):
        """Serve streams API"""
        streams = [
            {k: v for k, v in stream.items() if k not in ['server']}
            for stream in active_streams.values()
        ]
        
        response = {
            'success': True,
            'streams': streams,
            'totalStreams': len(streams)
        }
        
        self.send_json_response(response)
    
    def serve_config_api(self):
        """Serve configuration API"""
        response = {
            'success': True,
            'config': CONFIG
        }
        
        self.send_json_response(response)
    
    def serve_network_api(self):
        """Serve network information API"""
        network_info = self.network_discovery.get_network_info()
        
        response = {
            'success': True,
            'network': network_info
        }
        
        self.send_json_response(response)
    
    def serve_health(self):
        """Serve health check"""
        response = {
            'status': 'healthy',
            'service': 'pimic-audio-streaming-python',
            'version': '2.0.0-minimal',
            'active_streams': len(active_streams),
            'connected_clients': len(connected_clients),
            'timestamp': datetime.now().isoformat(),
            'dependencies': 'python-stdlib-only'
        }
        
        self.send_json_response(response)
    
    def serve_static_file(self):
        """Serve static files (CSS, JS)"""
        file_path = self.path[1:]  # Remove leading /
        
        try:
            # Load from static directory
            static_path = Path(__file__).parent / file_path
            
            if not static_path.exists():
                self.send_error(404)
                return
            
            # Determine content type
            if file_path.endswith('.css'):
                content_type = 'text/css'
            elif file_path.endswith('.js'):
                content_type = 'application/javascript'
            else:
                content_type = 'text/plain'
            
            with open(static_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error serving static file {file_path}: {e}")
            self.send_error(500)
    
    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))


class PimicAudioServer:
    """Main PIMIC Audio Streaming Server - Pure Python Version"""
    
    def __init__(self):
        self.http_server = None
        self.network_discovery = None
    
    def get_server_ip(self):
        """Get the server's IP address"""
        try:
            # Create a socket to get the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "localhost"
        
    def start(self):
        """Start all server components"""
        print(f"""
🎵 PIMIC Audio Streaming Server (Pure Python) 🎵
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Web Interface:  http://localhost:{CONFIG['web_port']}
🎧 Stream Ports:   {CONFIG['default_stream_port']}+
🔊 Bitrate Range:  {CONFIG['min_bitrate']}-{CONFIG['max_bitrate']} kbps
🐍 Runtime:        Python {sys.version.split()[0]}
🚀 Dependencies:   Standard Library Only
⚡ Performance:    Raspberry Pi Optimized
✨ No npm/node:    Pure Python Implementation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """)
        
        # Start network discovery
        self.network_discovery = NetworkDiscovery()
        self.network_discovery.start_discovery()
        
        # Start HTTP server
        self.http_server = HTTPServer(("0.0.0.0", CONFIG['web_port']), HTTPHandler)
        
        # Check for HTTPS certificates and wrap server if available
        cert_file = "/opt/pimic-audio/server.crt"
        key_file = "/opt/pimic-audio/server.key"
        
        if os.path.exists(cert_file) and os.path.exists(key_file):
            try:
                import ssl
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(cert_file, key_file)
                self.http_server.socket = context.wrap_socket(self.http_server.socket, server_side=True)
                logger.info(f"🔒 HTTPS enabled on port {CONFIG['web_port']}")
                print(f"🔒 HTTPS: https://{self.get_server_ip()}:{CONFIG['web_port']}")
            except Exception as e:
                logger.warning(f"HTTPS setup failed, using HTTP: {e}")
                print(f"⚠️  HTTPS setup failed, using HTTP: {e}")
        else:
            logger.info("📡 HTTP server (no SSL certificates found)")
            print(f"⚠️  HTTP only: Microphone access requires HTTPS in modern browsers")
            print(f"💡 For HTTPS, generate certificates or use localhost")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        logger.info("PIMIC Audio Server (Pure Python) started successfully")
        
        try:
            self.http_server.serve_forever()
        except KeyboardInterrupt:
            pass
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        global server_running
        server_running = False
        
        print("\\n[SHUTDOWN] Stopping PIMIC Audio Server...")
        
        if self.http_server:
            self.http_server.shutdown()
        
        # Stop all stream servers
        for stream in active_streams.values():
            if 'server' in stream:
                stream['server'].stop()
        
        logger.info("PIMIC Audio Server stopped")
        sys.exit(0)


if __name__ == "__main__":
    try:
        # Check Python version
        if sys.version_info < (3, 6):
            print("❌ Python 3.6+ required")
            sys.exit(1)
        
        print(f"🐍 Starting with Python {sys.version.split()[0]}")
        print("✅ All dependencies available in standard library")
        
        server = PimicAudioServer()
        server.start()
        
    except KeyboardInterrupt:
        print("\\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        print(f"❌ Startup Error: {e}")
        sys.exit(1)