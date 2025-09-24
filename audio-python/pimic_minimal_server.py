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

# Global audio handler instance
global_audio_handler = None
global_rtp_streamer = None

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


class RTPStreamer:
    """RTP Audio Streaming for professional audio tools"""
    
    def __init__(self):
        self.active_rtp_streams = {}
        self.rtp_base_port = 5004
        
    def start_rtp_stream(self, client_ip: str, audio_handler) -> dict:
        """Start RTP stream for a client"""
        try:
            if client_ip in self.active_rtp_streams:
                # Nur serialisierbare Felder zurückgeben
                stream = self.active_rtp_streams[client_ip]
                return {
                    'success': True,
                    'rtp_url': f"rtp://0.0.0.0:{stream['port']}",
                    'rtcp_url': f"rtp://0.0.0.0:{stream['rtcp_port']}",
                    'payload_type': stream['payload_type'],
                    'client_ip': client_ip
                }
            
            # Find available port
            rtp_port = self.rtp_base_port
            while rtp_port in [stream['port'] for stream in self.active_rtp_streams.values()]:
                rtp_port += 2  # RTP uses even ports, RTCP uses odd
            
            # Create RTP stream configuration
            rtp_config = {
                'client_ip': client_ip,
                'port': rtp_port,
                'rtcp_port': rtp_port + 1,
                'payload_type': 96,  # Dynamic payload type for Opus
                'ssrc': self._generate_ssrc(client_ip),
                'sequence_number': 0,
                'timestamp': 0,
                'socket': None,
                'thread': None,
                'running': False
            }
            
            # Create UDP socket for RTP
            rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            rtp_socket.bind(('0.0.0.0', rtp_port))
            rtp_config['socket'] = rtp_socket
            
            # Start RTP streaming thread
            rtp_config['running'] = True
            rtp_thread = threading.Thread(
                target=self._rtp_streaming_loop,
                args=(rtp_config, audio_handler),
                daemon=True
            )
            rtp_thread.start()
            rtp_config['thread'] = rtp_thread
            
            self.active_rtp_streams[client_ip] = rtp_config
            
            logger.info(f"RTP stream started for {client_ip} on port {rtp_port}")
            
            return {
                'success': True,
                'rtp_url': f'rtp://0.0.0.0:{rtp_port}',
                'rtcp_url': f'rtp://0.0.0.0:{rtp_port + 1}',
                'payload_type': rtp_config['payload_type'],
                'client_ip': client_ip
            }
            
        except Exception as e:
            logger.error(f"RTP stream start failed for {client_ip}: {e}")
            return {'success': False, 'error': str(e)}
    
    def stop_rtp_stream(self, client_ip: str) -> dict:
        """Stop RTP stream for a client"""
        try:
            if client_ip not in self.active_rtp_streams:
                return {'success': False, 'error': 'RTP stream not found'}
            
            stream = self.active_rtp_streams[client_ip]
            
            # Stop streaming
            stream['running'] = False
            
            # Close socket
            if stream['socket']:
                stream['socket'].close()
            
            # Wait for thread to finish
            if stream['thread'] and stream['thread'].is_alive():
                stream['thread'].join(timeout=1.0)
            
            del self.active_rtp_streams[client_ip]
            
            logger.info(f"RTP stream stopped for {client_ip}")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"RTP stream stop failed for {client_ip}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_ssrc(self, client_ip: str) -> int:
        """Generate SSRC from client IP"""
        hash_obj = hashlib.md5(client_ip.encode())
        return struct.unpack('>I', hash_obj.digest()[:4])[0]
    
    def _rtp_streaming_loop(self, rtp_config, audio_handler):
        """Main RTP streaming loop"""
        try:
            client_ip = rtp_config['client_ip']
            rtp_socket = rtp_config['socket']
            
            # RTP packet header template (12 bytes)
            # V=2, P=0, X=0, CC=0, M=0, PT=payload_type
            version_flags = 0x80  # Version 2
            payload_type = rtp_config['payload_type']
            
            logger.info(f"RTP streaming loop started for {client_ip}")
            
            while rtp_config['running'] and server_running:
                try:
                    # Get audio data from handler
                    if not audio_handler.has_audio_data(client_ip):
                        time.sleep(0.01)  # 10ms sleep
                        continue
                    
                    audio_data = audio_handler.get_audio_chunk(client_ip)
                    if not audio_data:
                        time.sleep(0.01)
                        continue
                    
                    # Create RTP header
                    sequence_number = rtp_config['sequence_number']
                    timestamp = rtp_config['timestamp']
                    ssrc = rtp_config['ssrc']
                    
                    # Pack RTP header
                    rtp_header = struct.pack(
                        '>BBHII',
                        version_flags,
                        payload_type,
                        sequence_number & 0xFFFF,
                        timestamp & 0xFFFFFFFF,
                        ssrc & 0xFFFFFFFF
                    )
                    
                    # Create RTP packet
                    rtp_packet = rtp_header + audio_data
                    
                    # Send to all multicast addresses or specific destinations
                    # For now, send to multicast address for easy consumption
                    multicast_addr = ('224.0.0.1', rtp_config['port'])
                    
                    try:
                        rtp_socket.sendto(rtp_packet, multicast_addr)
                    except Exception as send_error:
                        logger.debug(f"RTP send error: {send_error}")
                    
                    # Update sequence number and timestamp
                    rtp_config['sequence_number'] = (sequence_number + 1) & 0xFFFF
                    rtp_config['timestamp'] = (timestamp + 960) & 0xFFFFFFFF  # 960 samples for 20ms at 48kHz
                    
                    # Small delay to maintain timing
                    time.sleep(0.02)  # 20ms delay
                    
                except Exception as e:
                    if rtp_config['running']:
                        logger.debug(f"RTP streaming error for {client_ip}: {e}")
                    time.sleep(0.01)
            
        except Exception as e:
            logger.error(f"RTP streaming loop error for {client_ip}: {e}")
        finally:
            logger.info(f"RTP streaming loop ended for {client_ip}")
    
    def get_active_streams(self) -> dict:
        """Get information about active RTP streams"""
        return {
            'active_count': len(self.active_rtp_streams),
            'streams': [
                {
                    'client_ip': config['client_ip'],
                    'rtp_port': config['port'],
                    'rtcp_port': config['rtcp_port'],
                    'rtp_url': f'rtp://224.0.0.1:{config["port"]}',
                    'payload_type': config['payload_type']
                }
                for config in self.active_rtp_streams.values()
            ]
        }


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
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.audio_clients = {}  # client_ip -> audio_buffer
            cls._instance.stream_buffers = {}  # stream_id -> audio_buffer
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if not hasattr(self, 'initialized'):
            self.audio_clients = {}  # client_ip -> audio_buffer
            self.stream_buffers = {}  # stream_id -> audio_buffer
            self.initialized = True
        
    def handle_audio_websocket(self, request_handler):
        """Handle WebSocket connection for audio streaming"""
        try:
            client_ip = request_handler.client_address[0]
            logger.info(f"Audio WebSocket connected from {client_ip}")
            
            # Set socket timeout to prevent indefinite blocking
            request_handler.connection.settimeout(0.1)
            
            # Start reading WebSocket frames
            self.read_websocket_frames(request_handler, client_ip)
            
        except Exception as e:
            logger.error(f"Audio WebSocket error: {e}")
        finally:
            # Reset socket timeout
            request_handler.connection.settimeout(None)
    
    def read_websocket_frames(self, request_handler, client_ip):
        """Read and process WebSocket frames"""
        try:
            while True:
                try:
                    # Read WebSocket frame header with timeout
                    frame_header = request_handler.rfile.read(2)
                    if len(frame_header) != 2:
                        break
                except socket.timeout:
                    # Timeout is normal, continue reading
                    continue
                except Exception:
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
            logger.info(f"Audio data received from {client_ip}: {len(data)} bytes, buffer size: {len(self.audio_clients[client_ip]['buffer'])} bytes")
            # In a full implementation, this would forward to stream endpoints
    
    def handle_http_audio_data(self, data, client_ip):
        """Handle HTTP-uploaded audio data"""
        # Initialize client if not exists
        if client_ip not in self.audio_clients:
            self.audio_clients[client_ip] = {
                'config': {'format': 'audio/webm'},
                'buffer': b'',
                'last_data': time.time()
            }
        
        # Add data to buffer
        self.audio_clients[client_ip]['buffer'] += data
        self.audio_clients[client_ip]['last_data'] = time.time()
        logger.info(f"HTTP audio data received from {client_ip}: {len(data)} bytes, buffer size: {len(self.audio_clients[client_ip]['buffer'])} bytes")
            
    def get_audio_stream(self, client_ip):
        """Get audio stream for a specific client"""
        if client_ip in self.audio_clients:
            client_data = self.audio_clients[client_ip]
            buffer = client_data['buffer']
            
            # For continuous streaming, return data and keep some in buffer
            # Only clear buffer if it's getting too large (> 1MB)
            if len(buffer) > 1024 * 1024:  # 1MB limit
                # Keep the last 100KB for continuity
                client_data['buffer'] = buffer[-100*1024:]
                return buffer[:-100*1024]
            else:
                # Return a copy of buffer without clearing it
                return buffer
        return b''
    
    def has_audio_data(self, client_ip):
        """Check if client has active audio data (within last 10 seconds)"""
        if client_ip in self.audio_clients:
            client_data = self.audio_clients[client_ip]
            # Check if we have recent data (within last 10 seconds)
            time_since_last = time.time() - client_data['last_data']
            has_buffer = len(client_data['buffer']) > 0
            is_recent = time_since_last < 10.0  # 10 seconds timeout
            return has_buffer and is_recent
        return False
    
    def get_audio_chunk(self, client_ip, chunk_size=960):
        """Get audio chunk for RTP streaming"""
        if client_ip not in self.audio_clients:
            return None
        
        client_data = self.audio_clients[client_ip]
        buffer = client_data['buffer']
        
        # Use available buffer size if less than requested chunk_size
        # This prevents RTP from waiting for exact chunk sizes
        if len(buffer) == 0:
            return None
        
        actual_chunk_size = min(len(buffer), chunk_size)
        
        # Extract chunk and update buffer
        chunk = buffer[:actual_chunk_size]
        client_data['buffer'] = buffer[actual_chunk_size:]
        
        return chunk
    
    def get_audio_levels(self):
        """Get current audio levels for all active clients"""
        levels = {}
        current_time = time.time()
        
        for client_ip, client_data in self.audio_clients.items():
            # Check if client is active (data within last 5 seconds)
            time_since_last = current_time - client_data['last_data']
            if time_since_last > 5.0:
                continue
            
            buffer = client_data['buffer']
            if len(buffer) == 0:
                levels[client_ip] = {
                    'level': 0,
                    'peak': 0,
                    'active': False,
                    'last_update': current_time
                }
                continue
            
            # Calculate audio level from buffer
            # Take sample from buffer to calculate level
            sample_size = min(1024, len(buffer))
            sample = buffer[-sample_size:] if sample_size > 0 else b''
            
            if sample:
                # Simple level calculation (RMS-like)
                level_sum = sum(abs(b - 128) for b in sample) / len(sample)
                normalized_level = min(100, (level_sum / 128.0) * 100)
                
                # Calculate peak (max value in sample)
                peak = max(abs(b - 128) for b in sample) / 128.0 * 100
                
                levels[client_ip] = {
                    'level': round(normalized_level, 1),
                    'peak': round(peak, 1),
                    'active': True,
                    'buffer_size': len(buffer),
                    'last_update': current_time,
                    'time_since_data': round(time_since_last, 2)
                }
            else:
                levels[client_ip] = {
                    'level': 0,
                    'peak': 0,
                    'active': False,
                    'last_update': current_time
                }
        
        return levels


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
        elif self.path == '/api/rtp/streams':
            if hasattr(self.server, 'server_port') and self.server.server_port == 8081:
                self.send_json_response({
                    'success': False, 
                    'error': 'RTP functions require HTTPS server. Please use https://192.168.188.90:6969/api/rtp/streams'
                })
            else:
                self.serve_rtp_streams_api()
        elif self.path == '/api/audio/levels':
            self.serve_audio_levels_api()
        elif self.path.startswith('/static/'):
            self.serve_static_file()
        elif self.path.startswith('/client/') and self.path.endswith('/stream'):
            self.serve_client_stream()
        elif self.path.startswith('/client/') and self.path.endswith('/audio'):
            self.serve_client_audio_player()
        elif self.path.startswith('/client/') and self.path.endswith('/wav'):
            self.serve_client_wav_stream()
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
        elif self.path == '/api/audio/upload':
            self.handle_audio_upload()
        elif self.path == '/api/rtp/start':
            # Check if this is the HTTPS server (port 6969) or HTTP server (port 8081)
            if hasattr(self.server, 'server_port') and self.server.server_port == 8081:
                self.send_json_response({
                    'success': False, 
                    'error': 'RTP functions require HTTPS server. Please use https://192.168.188.90:6969/api/rtp/start'
                })
            else:
                self.handle_rtp_start()
        elif self.path == '/api/rtp/stop':
            if hasattr(self.server, 'server_port') and self.server.server_port == 8081:
                self.send_json_response({
                    'success': False, 
                    'error': 'RTP functions require HTTPS server. Please use https://192.168.188.90:6969/api/rtp/stop'
                })
            else:
                self.handle_rtp_stop()
        else:
            self.send_error(404)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.add_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        """Handle HEAD requests - check if resource exists without returning body"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.add_cors_headers()
            self.end_headers()
        elif self.path == '/api/streams':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.add_cors_headers()
            self.end_headers()
        elif self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.add_cors_headers()
            self.end_headers()
        elif self.path == '/api/network':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.add_cors_headers()
            self.end_headers()
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.add_cors_headers()
            self.end_headers()
        elif self.path.startswith('/static/'):
            # Check if static file exists
            file_path = self.path[1:]  # Remove leading /
            static_path = Path(__file__).parent / file_path
            if static_path.exists():
                self.send_response(200)
                if file_path.endswith('.css'):
                    content_type = 'text/css'
                elif file_path.endswith('.js'):
                    content_type = 'application/javascript'
                elif file_path.endswith('.html'):
                    content_type = 'text/html'
                else:
                    content_type = 'text/plain'
                self.send_header('Content-type', content_type)
                self.add_cors_headers()
                self.end_headers()
            else:
                self.send_response(404)
                self.add_cors_headers()
                self.end_headers()
        elif self.path.startswith('/client/') and self.path.endswith('/stream'):
            # Always respond 200 for client stream HEAD requests (matches GET behavior)
            path_parts = self.path.split('/')
            if len(path_parts) >= 3:
                client_ip = path_parts[2]
                logger.info(f"HEAD request for client stream: {client_ip}")
                self.send_response(200)
                self.send_header('Content-type', 'audio/webm')
                self.add_cors_headers()
                self.end_headers()
            else:
                self.send_response(400)
                self.add_cors_headers()
                self.end_headers()
        else:
            self.send_response(404)
            self.add_cors_headers()
            self.end_headers()
    
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
            logger.info(f"Audio WebSocket upgrade request from {self.client_address[0]}")
            logger.info(f"Headers: {dict(self.headers)}")
            if self.websocket_handler.handle_websocket_handshake(self):
                logger.info("Audio WebSocket handshake successful")
                # Hand over to audio stream handler
                AudioStreamHandler().handle_audio_websocket(self)
            else:
                logger.error("Audio WebSocket handshake failed")
                self.send_error(400, "WebSocket handshake failed")
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
                
                # Get audio data from HTTP audio buffer
                global global_audio_handler
                if global_audio_handler is None:
                    global_audio_handler = AudioStreamHandler()
                audio_data = global_audio_handler.get_audio_stream(client_ip)
                
                if audio_data and len(audio_data) > 0:
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/webm')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Accept-Ranges', 'bytes')
                    self.end_headers()
                    
                    self.wfile.write(audio_data)
                    logger.info(f"Served {len(audio_data)} bytes of audio for client {client_ip}")
                else:
                    # No data available, send minimal response
                    self.send_response(204)  # No Content
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    logger.info(f"No audio data available for client {client_ip}")
            else:
                self.send_error(400, "Invalid stream URL")
                
        except Exception as e:
            logger.error(f"Client stream serving error: {e}")
            self.send_error(500)
    
    def serve_client_audio_player(self):
        """Serve a chunked audio stream that browsers can play"""
        try:
            # Parse client IP from URL: /client/192.168.1.100/audio
            path_parts = self.path.split('/')
            if len(path_parts) >= 3:
                client_ip = path_parts[2]
                
                logger.info(f"Serving chunked audio for client {client_ip}")
                
                # Start chunked response
                self.send_response(200)
                self.send_header('Content-Type', 'audio/webm')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Transfer-Encoding', 'chunked')
                self.end_headers()
                
                # Stream audio data in chunks
                global global_audio_handler
                if global_audio_handler is None:
                    global_audio_handler = AudioStreamHandler()
                audio_handler = global_audio_handler
                chunk_size = 4096  # 4KB chunks
                timeout = 30  # 30 seconds timeout
                start_time = time.time()
                
                try:
                    while (time.time() - start_time) < timeout:
                        audio_data = audio_handler.get_audio_stream(client_ip)
                        
                        if audio_data and len(audio_data) > 0:
                            # Send data in chunks
                            for i in range(0, len(audio_data), chunk_size):
                                chunk = audio_data[i:i + chunk_size]
                                if chunk:
                                    # Write chunk size in hex followed by CRLF
                                    chunk_size_hex = hex(len(chunk))[2:].encode() + b'\r\n'
                                    self.wfile.write(chunk_size_hex)
                                    # Write chunk data followed by CRLF
                                    self.wfile.write(chunk + b'\r\n')
                                    self.wfile.flush()
                        
                        # Small delay to prevent busy loop
                        time.sleep(0.05)  # 50ms delay
                    
                    # End chunked encoding
                    self.wfile.write(b'0\r\n\r\n')
                    
                except Exception as e:
                    logger.error(f"Chunked streaming error: {e}")
                    # Try to end chunked encoding gracefully
                    try:
                        self.wfile.write(b'0\r\n\r\n')
                    except:
                        pass
            else:
                self.send_error(400, "Invalid audio URL")
                
        except Exception as e:
            logger.error(f"Client audio serving error: {e}")
            self.send_error(500)
    
    def serve_client_wav_stream(self):
        """Serve audio stream as simple WAV header + raw data for browser compatibility"""
        try:
            # Parse client IP from URL: /client/192.168.1.100/wav
            path_parts = self.path.split('/')
            if len(path_parts) >= 3:
                client_ip = path_parts[2]
                
                logger.info(f"Serving WAV stream for client {client_ip}")
                
                # Get audio data
                global global_audio_handler
                if global_audio_handler is None:
                    global_audio_handler = AudioStreamHandler()
                audio_data = global_audio_handler.get_audio_stream(client_ip)
                
                if audio_data and len(audio_data) > 0:
                    # Create minimal WAV header for PCM data
                    # This is a simplified approach - real WebM->WAV conversion would be more complex
                    sample_rate = 48000  # Assume 48kHz
                    channels = 1  # Mono
                    bits_per_sample = 16
                    
                    # WAV header (44 bytes)
                    wav_header = bytearray(44)
                    wav_header[0:4] = b'RIFF'
                    wav_header[4:8] = (len(audio_data) + 36).to_bytes(4, 'little')  # File size - 8
                    wav_header[8:12] = b'WAVE'
                    wav_header[12:16] = b'fmt '
                    wav_header[16:20] = (16).to_bytes(4, 'little')  # Subchunk1Size
                    wav_header[20:22] = (1).to_bytes(2, 'little')   # AudioFormat (PCM)
                    wav_header[22:24] = channels.to_bytes(2, 'little')  # NumChannels
                    wav_header[24:28] = sample_rate.to_bytes(4, 'little')  # SampleRate
                    wav_header[28:32] = (sample_rate * channels * bits_per_sample // 8).to_bytes(4, 'little')  # ByteRate
                    wav_header[32:34] = (channels * bits_per_sample // 8).to_bytes(2, 'little')  # BlockAlign
                    wav_header[34:36] = bits_per_sample.to_bytes(2, 'little')  # BitsPerSample
                    wav_header[36:40] = b'data'
                    wav_header[40:44] = len(audio_data).to_bytes(4, 'little')  # Subchunk2Size
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'audio/wav')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.send_header('Content-Length', str(44 + len(audio_data)))
                    self.end_headers()
                    
                    # Send WAV header + audio data
                    self.wfile.write(wav_header)
                    self.wfile.write(audio_data)
                else:
                    # No data available
                    self.send_response(204)  # No Content
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
            else:
                self.send_error(400, "Invalid WAV stream URL")
                
        except Exception as e:
            logger.error(f"WAV stream serving error: {e}")
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
    
    def handle_audio_upload(self):
        """Handle HTTP audio data upload"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No content")
                return
                
            # Read multipart form data
            content = self.rfile.read(content_length)
            
            # Extract client IP from form data (simplified parsing)
            client_ip = self.client_address[0]  # Fallback to connection IP
            
            # Try to extract client IP from form data
            content_str = content.decode('utf-8', errors='ignore')
            if 'clientIP' in content_str:
                import re
                match = re.search(r'name="clientIP"\r?\n\r?\n([^\r\n]+)', content_str)
                if match:
                    client_ip = match.group(1).strip()
            
            # Find audio data in multipart content
            audio_start = content.find(b'\r\n\r\n') + 4
            audio_end = content.rfind(b'\r\n--')
            if audio_end == -1:
                audio_end = len(content)
                
            audio_data = content[audio_start:audio_end]
            
            if len(audio_data) > 0:
                # Store audio data in AudioStreamHandler
                global global_audio_handler
                if global_audio_handler is None:
                    global_audio_handler = AudioStreamHandler()
                global_audio_handler.handle_http_audio_data(audio_data, client_ip)
                logger.info(f"HTTP audio upload from {client_ip}: {len(audio_data)} bytes")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {"status": "ok", "bytes": len(audio_data)}
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_error(400, "No audio data found")
                
        except Exception as e:
            logger.error(f"Audio upload error: {e}")
            self.send_error(500, "Upload failed")
    
    def handle_rtp_start(self):
        """Handle RTP stream start request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                self.send_json_response({'success': False, 'error': 'Invalid request'})
                return
            
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            client_ip = data.get('client_ip')
            if not client_ip:
                self.send_json_response({'success': False, 'error': 'Missing client_ip'})
                return
            
            # Get global RTP streamer instance
            global global_rtp_streamer, global_audio_handler
            if not global_rtp_streamer:
                global_rtp_streamer = RTPStreamer()
            
            if not global_audio_handler:
                global_audio_handler = AudioStreamHandler()
            
            # Start RTP stream
            result = global_rtp_streamer.start_rtp_stream(client_ip, global_audio_handler)
            self.send_json_response(result)
            
        except Exception as e:
            logger.error(f"RTP start error: {e}")
            self.send_json_response({'success': False, 'error': str(e)})
    
    def handle_rtp_stop(self):
        """Handle RTP stream stop request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                self.send_json_response({'success': False, 'error': 'Invalid request'})
                return
            
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            client_ip = data.get('client_ip')
            if not client_ip:
                self.send_json_response({'success': False, 'error': 'Missing client_ip'})
                return
            
            # Get global RTP streamer instance
            global global_rtp_streamer
            if not global_rtp_streamer:
                self.send_json_response({'success': False, 'error': 'RTP streamer not initialized'})
                return
            
            # Stop RTP stream
            result = global_rtp_streamer.stop_rtp_stream(client_ip)
            self.send_json_response(result)
            
        except Exception as e:
            logger.error(f"RTP stop error: {e}")
            self.send_json_response({'success': False, 'error': str(e)})
    
    def serve_rtp_streams_api(self):
        """Serve RTP streams API"""
        try:
            global global_rtp_streamer
            if not global_rtp_streamer:
                global_rtp_streamer = RTPStreamer()
            
            rtp_info = global_rtp_streamer.get_active_streams()
            self.send_json_response({
                'success': True,
                'rtp_streams': rtp_info
            })
            
        except Exception as e:
            logger.error(f"RTP streams API error: {e}")
            self.send_json_response({'success': False, 'error': str(e)})

    def serve_audio_levels_api(self):
        """Serve real-time audio levels for all active clients"""
        try:
            global global_audio_handler
            if not global_audio_handler:
                global_audio_handler = AudioStreamHandler()
            
            audio_levels = global_audio_handler.get_audio_levels()
            self.send_json_response({
                'success': True,
                'levels': audio_levels,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.error(f"Audio levels API error: {e}")
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
            self.add_cors_headers()
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
            elif file_path.endswith('.html'):
                content_type = 'text/html'
            elif file_path.endswith('.json'):
                content_type = 'application/json'
            elif file_path.endswith('.png'):
                content_type = 'image/png'
            elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            elif file_path.endswith('.svg'):
                content_type = 'image/svg+xml'
            else:
                content_type = 'text/plain'
            
            # Handle binary files
            if file_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico')):
                with open(static_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(len(content)))
                self.add_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            else:
                # Handle text files
                with open(static_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(len(content.encode('utf-8'))))
                self.add_cors_headers()
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error serving static file {file_path}: {e}")
            self.send_error(500)
    
    def add_cors_headers(self):
        """Add CORS headers to response"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, HEAD, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization')
        self.send_header('Access-Control-Max-Age', '86400')

    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.add_cors_headers()
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
        
        # Start HTTPS server with threading support
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
        
        # Start additional HTTP server on port 8081 for dashboard access
        def start_http_server():
            try:
                http_port = 8081
                http_server = ThreadingHTTPServer(("0.0.0.0", http_port), HTTPHandler)
                logger.info(f"📡 Additional HTTP server started on port {http_port}")
                print(f"🌍 HTTP Dashboard: http://{self.get_server_ip()}:{http_port}/static/dashboard.html")
                print(f"🌍 HTTP Access: http://{self.get_server_ip()}:{http_port}/")
                http_server.serve_forever()
            except Exception as e:
                logger.error(f"HTTP server failed: {e}")
        
        # Start HTTP server in background thread
        import threading
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()
        
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