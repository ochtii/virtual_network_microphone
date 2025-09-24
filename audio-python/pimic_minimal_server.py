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
from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
import socketserver
from urllib.parse import urlparse, parse_qs
import base64
import hashlib
import struct
import hashlib

# Configuration
CONFIG = {
    'web_port': 6969,
    'default_stream_port': 9420,
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
audio_stream_handler = None  # Will be initialized in main

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


class AudioStreamHandler:
    """Handle audio streaming via WebSocket"""
    
    def __init__(self):
        self.audio_clients = {}  # client_ip -> audio_buffer
        self.stream_buffers = {}  # stream_id -> audio_buffer
        
    def handle_audio_websocket(self, request_handler):
        """Handle WebSocket connection for audio streaming"""
        try:
            client_ip = request_handler.client_address[0]
            logger.info(f"Audio WebSocket connected from {client_ip}")
            
            # Start reading WebSocket frames
            self.read_websocket_frames(request_handler, client_ip)
            
        except Exception as e:
            logger.error(f"Audio WebSocket error: {e}")
    
    def read_websocket_frames(self, request_handler, client_ip):
        """Read and process WebSocket frames"""
        try:
            while True:
                # Read WebSocket frame header
                frame_header = request_handler.rfile.read(2)
                if len(frame_header) != 2:
                    break
                    
                fin_rsv_opcode = frame_header[0]
                mask_len = frame_header[1]
                
                # Parse frame
                opcode = fin_rsv_opcode & 0x0F
                masked = bool(mask_len & 0x80)
                payload_len = mask_len & 0x7F
                
                # Handle different payload lengths
                if payload_len == 126:
                    payload_len = struct.unpack('>H', request_handler.rfile.read(2))[0]
                elif payload_len == 127:
                    payload_len = struct.unpack('>Q', request_handler.rfile.read(8))[0]
                
                # Read mask if present
                mask = b''
                if masked:
                    mask = request_handler.rfile.read(4)
                
                # Read payload
                payload = request_handler.rfile.read(payload_len)
                
                # Unmask payload if needed
                if masked:
                    payload = bytes(payload[i] ^ mask[i % 4] for i in range(len(payload)))
                
                # Handle different frame types
                if opcode == 0x1:  # Text frame (JSON config)
                    self.handle_config_message(json.loads(payload.decode()), client_ip)
                elif opcode == 0x2:  # Binary frame (audio data)
                    self.handle_audio_data(payload, client_ip)
                elif opcode == 0x8:  # Close frame
                    break
                    
        except Exception as e:
            logger.error(f"WebSocket frame reading error: {e}")
        finally:
            if client_ip in self.audio_clients:
                del self.audio_clients[client_ip]
            logger.info(f"Audio WebSocket closed for {client_ip}")
    
    def handle_config_message(self, config, client_ip):
        """Handle stream configuration message"""
        logger.info(f"Audio stream config from {client_ip}: {config}")
        self.audio_clients[client_ip] = {
            'config': config,
            'buffer': b'',
            'last_data': time.time()
        }
    
    def handle_audio_data(self, data, client_ip):
        """Handle incoming audio data"""
        if client_ip in self.audio_clients:
            self.audio_clients[client_ip]['buffer'] += data
            self.audio_clients[client_ip]['last_data'] = time.time()
            # In a full implementation, this would forward to stream endpoints
            
    def get_audio_stream(self, client_ip):
        """Get audio stream for a specific client"""
        if client_ip in self.audio_clients:
            client_data = self.audio_clients[client_ip]
            buffer = client_data['buffer']
            client_data['buffer'] = b''  # Clear buffer after reading
            return buffer
        return b''


class StreamServer:
    """TCP Stream Server für Audio-Daten"""
    
    def __init__(self, port: int):
        self.port = port
        self.server_socket = None
        self.running = False
        
    def start(self):
        """Start stream server"""
        try:
            logger.info(f"Creating socket for stream server on port {self.port}")
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set socket timeout to prevent hanging
            self.server_socket.settimeout(5.0)
            
            logger.info(f"Binding socket to port {self.port}")
            self.server_socket.bind(('0.0.0.0', self.port))
            
            logger.info(f"Starting to listen on port {self.port}")
            self.server_socket.listen(5)
            self.running = True
            
            # Remove timeout for accept operations
            self.server_socket.settimeout(None)
            
            threading.Thread(target=self._accept_loop, daemon=True).start()
            logger.info(f"Stream server started successfully on port {self.port}")
            
        except socket.timeout:
            logger.error(f"Stream server bind/listen timeout on port {self.port}")
            raise
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.error(f"Port {self.port} already in use")
            else:
                logger.error(f"Stream server socket error: {e}")
            raise
        except Exception as e:
            logger.error(f"Stream server start failed: {e}")
            raise
    
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
        elif self.path.startswith('/client/') and self.path.endswith('/stream'):
            self.serve_client_stream()
        elif self.path == '/ws/audio-stream' and 'upgrade' in self.headers.get('Connection', '').lower():
            self.handle_audio_websocket_upgrade()
        elif self.path == '/ws' or 'upgrade' in self.headers.get('Connection', '').lower():
            self.handle_websocket_upgrade()
        else:
            self.send_error(404)
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == '/api/stream/start':
            self.handle_start_stream()
        elif self.path == '/api/stream/register':
            self.handle_register_stream()
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
    
    def handle_audio_websocket_upgrade(self):
        """Handle audio streaming WebSocket upgrade"""
        try:
            if self.websocket_handler.handle_websocket_handshake(self):
                # Hand over to audio stream handler
                audio_stream_handler.handle_audio_websocket(self)
        except Exception as e:
            logger.error(f"Audio WebSocket upgrade failed: {e}")
            self.send_error(500)
    
    def serve_client_stream(self):
        """Serve audio stream for a specific client"""
        try:
            # Parse client IP from URL: /client/192.168.1.100/stream
            path_parts = self.path.split('/')
            if len(path_parts) >= 3:
                client_ip = path_parts[2]
                
                logger.info(f"Serving stream for client {client_ip}")
                
                # Get audio data from WebSocket buffer
                audio_data = audio_stream_handler.get_audio_stream(client_ip)
                
                if audio_data:
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/webm')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    
                    self.wfile.write(audio_data)
                else:
                    # No data available, send minimal response
                    self.send_response(204)  # No Content
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
            else:
                self.send_error(400, "Invalid stream URL")
                
        except Exception as e:
            logger.error(f"Client stream serving error: {e}")
            self.send_error(500)
    
    def serve_events_stream(self):
        """Serve Server-Sent Events stream"""
        self.send_response(200)
        self.send_header('Content-type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Send initial config and close connection immediately to avoid blocking
        config_event = f"data: {json.dumps({'type': 'config', 'config': CONFIG})}\\n\\n"
        self.wfile.write(config_event.encode())
        self.wfile.flush()
        
        # Send one heartbeat and close (no blocking while loop)
        heartbeat = f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\\n\\n"
        self.wfile.write(heartbeat.encode())
        self.wfile.flush()
        
        # Connection closes automatically, no blocking
    
    def handle_start_stream(self):
        """Handle stream start request"""
        try:
            logger.info("Processing stream start request")
            logger.info(f"Headers: {dict(self.headers)}")
            
            # Check if Content-Length header exists
            if 'Content-Length' not in self.headers:
                logger.error("Missing Content-Length header")
                self.send_json_response({'success': False, 'error': 'Missing Content-Length header'})
                return
                
            content_length = int(self.headers['Content-Length'])
            logger.info(f"Content-Length: {content_length}")
            
            if content_length <= 0:
                logger.error("Invalid Content-Length")
                self.send_json_response({'success': False, 'error': 'Invalid Content-Length'})
                return
                
            post_data = self.rfile.read(content_length)
            
            logger.info(f"Received POST data ({len(post_data)} bytes): {post_data}")
            
            # Check if post_data is empty or invalid
            if not post_data or not post_data.strip():
                logger.error("Empty POST data received")
                self.send_json_response({'success': False, 'error': 'Empty request body'})
                return
                
            data = json.loads(post_data.decode('utf-8'))
            logger.info(f"Parsed JSON data: {data}")
            
            client_ip = self.client_address[0]
            stream_id = f"stream_{int(time.time() * 1000)}_{client_ip.replace('.', '_')}"
            stream_port = data.get('port', CONFIG['default_stream_port'])
            
            logger.info(f"Looking for available port starting from {stream_port}")
            
            # Find available port with safety limit
            max_port_attempts = 100
            port_attempts = 0
            original_port = stream_port
            
            while any(s['port'] == stream_port for s in active_streams.values()) and port_attempts < max_port_attempts:
                stream_port += 1
                port_attempts += 1
                if stream_port > 65535:
                    stream_port = CONFIG['default_stream_port']
                
            if port_attempts >= max_port_attempts:
                logger.error(f"Could not find available port after {max_port_attempts} attempts")
                self.send_json_response({'success': False, 'error': 'No available ports'})
                return
                
            logger.info(f"Selected port {stream_port} for stream {stream_id}")
            
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
            
            logger.info(f"Creating stream server for {stream_id} on port {stream_port}")
            
            # Start stream server
            stream_server = StreamServer(stream_port)
            try:
                stream_server.start()
                stream_config['server'] = stream_server
                active_streams[stream_id] = stream_config
                
                logger.info(f"Stream server started successfully for {stream_id}")
                
            except Exception as server_error:
                logger.error(f"Failed to start stream server: {server_error}")
                self.send_json_response({'success': False, 'error': f'Failed to start stream server: {server_error}'})
                return
            
            # Send response
            response = {
                'success': True,
                'streamId': stream_id,
                'port': stream_port,
                'config': {k: v for k, v in stream_config.items() if k not in ['server']}
            }
            
            self.send_json_response(response)
            logger.info(f"Stream started successfully: {stream_id} on port {stream_port}")
            
        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error: {je}")
            self.send_json_response({'success': False, 'error': f'Invalid JSON: {je}'})
        except Exception as e:
            logger.error(f"Stream start error: {e}")
            self.send_json_response({'success': False, 'error': str(e)})
    
    def handle_register_stream(self):
        """Handle client-side stream registration"""
        try:
            logger.info("Processing stream registration request")
            
            # Check Content-Length
            if 'Content-Length' not in self.headers:
                logger.error("Missing Content-Length header")
                self.send_json_response({'success': False, 'error': 'Missing Content-Length header'})
                return
                
            content_length = int(self.headers['Content-Length'])
            if content_length <= 0:
                logger.error("Invalid Content-Length")
                self.send_json_response({'success': False, 'error': 'Invalid Content-Length'})
                return
                
            post_data = self.rfile.read(content_length)
            logger.info(f"Received registration data ({len(post_data)} bytes): {post_data}")
            
            if not post_data or not post_data.strip():
                logger.error("Empty registration data received")
                self.send_json_response({'success': False, 'error': 'Empty request body'})
                return
                
            data = json.loads(post_data.decode('utf-8'))
            logger.info(f"Parsed registration data: {data}")
            
            # Extract stream information
            stream_id = data.get('streamId')
            client_ip = data.get('clientIP') or self.client_address[0]
            port = data.get('port', CONFIG['default_stream_port'])
            
            if not stream_id:
                logger.error("Missing streamId in registration")
                self.send_json_response({'success': False, 'error': 'streamId required'})
                return
            
            # Generate proxy stream URL
            pi_host = self.headers.get('Host', 'localhost').split(':')[0]
            proxy_stream_url = f"http://{pi_host}:{CONFIG['web_port']}/client/{client_ip}/stream"
            
            # Register stream in coordination system (Pi proxies the stream)
            stream_config = {
                'id': stream_id,
                'client_ip': client_ip,
                'stream_url': proxy_stream_url,
                'port': port,
                'bitrate': max(CONFIG['min_bitrate'], min(CONFIG['max_bitrate'], 
                              data.get('bitrate', 128))),
                'audio_source': data.get('audioSource', 'microphone'),
                'name': data.get('name', f'Client {client_ip}'),
                'start_time': datetime.now().isoformat(),
                'is_active': True,
                'type': 'client_proxy_stream',  # Mark as Pi-proxied client stream
                'requires_proxy': True
            }
            
            active_streams[stream_id] = stream_config
            
            response = {
                'success': True,
                'streamId': stream_id,
                'clientIP': client_ip,
                'streamUrl': proxy_stream_url,
                'message': 'Stream registered with Pi proxy'
            }
            
            self.send_json_response(response)
            logger.info(f"Client stream registered: {stream_id} at {proxy_stream_url}")
            
        except json.JSONDecodeError as je:
            logger.error(f"JSON decode error in registration: {je}")
            self.send_json_response({'success': False, 'error': f'Invalid JSON: {je}'})
        except Exception as e:
            logger.error(f"Stream registration error: {e}")
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
        
        # Start HTTP server with threading support
        self.http_server = ThreadingHTTPServer(("0.0.0.0", CONFIG['web_port']), HTTPHandler)
        
        # Check for HTTPS certificates and setup SSL context
        script_dir = Path(__file__).parent
        cert_file = script_dir / "server.crt"
        key_file = script_dir / "server.key"
        
        if cert_file.exists() and key_file.exists():
            try:
                import ssl
                
                # Create SSL context
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(str(cert_file), str(key_file))
                
                # Create HTTPS server by wrapping the socket
                self.http_server.socket = ssl_context.wrap_socket(
                    self.http_server.socket,
                    server_side=True
                )
                
                logger.info(f"🔒 HTTPS enabled on port {CONFIG['web_port']}")
                print(f"🔒 HTTPS: https://{self.get_server_ip()}:{CONFIG['web_port']}")
                
            except Exception as e:
                logger.error(f"HTTPS setup failed: {e}")
                print(f"⚠️  HTTPS setup failed, falling back to HTTP: {e}")
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
        
        # Initialize global handlers
        global audio_stream_handler
        audio_stream_handler = AudioStreamHandler()
        
        server = PimicAudioServer()
        server.start()
        
    except KeyboardInterrupt:
        print("\\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}")
        print(f"❌ Startup Error: {e}")
        sys.exit(1)