#!/usr/bin/env python3
"""
NetCast Audio Pro - WebSocket Audio Streaming Server
Real network audio streaming on port 42069
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime
import socket

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioStreamServer:
    def __init__(self, host='0.0.0.0', port=42069):
        self.host = host
        self.port = port
        self.clients = set()
        self.stream_active = False
        
    async def register_client(self, websocket, path):
        """Register new client connection"""
        self.clients.add(websocket)
        client_ip = websocket.remote_address[0]
        logger.info(f"🎙️ Client connected: {client_ip} (Total: {len(self.clients)})")
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'connection',
                'message': 'Connected to NetCast Audio Pro',
                'clients': len(self.clients),
                'timestamp': datetime.now().isoformat()
            }))
            
            # Keep connection alive and handle messages
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Client error: {e}")
        finally:
            self.clients.remove(websocket)
            logger.info(f"📤 Client disconnected: {client_ip} (Total: {len(self.clients)})")
    
    async def handle_message(self, websocket, message):
        """Handle incoming messages from clients"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'audio_data':
                # Broadcast audio data to all other clients
                await self.broadcast_audio(data, exclude=websocket)
                
            elif msg_type == 'stream_control':
                # Handle stream start/stop
                action = data.get('action')
                if action == 'start':
                    self.stream_active = True
                    await self.broadcast_message({
                        'type': 'stream_status',
                        'status': 'started',
                        'timestamp': datetime.now().isoformat()
                    })
                elif action == 'stop':
                    self.stream_active = False
                    await self.broadcast_message({
                        'type': 'stream_status', 
                        'status': 'stopped',
                        'timestamp': datetime.now().isoformat()
                    })
                    
            elif msg_type == 'ping':
                # Respond to ping
                await websocket.send(json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                }))
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    async def broadcast_audio(self, audio_data, exclude=None):
        """Broadcast audio data to all connected clients"""
        if not self.clients:
            return
            
        message = json.dumps(audio_data)
        disconnected = set()
        
        for client in self.clients:
            if client == exclude:
                continue
                
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    async def broadcast_message(self, message_data):
        """Broadcast general message to all clients"""
        if not self.clients:
            return
            
        message = json.dumps(message_data)
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    async def start_server(self):
        """Start the WebSocket server"""
        local_ip = self.get_local_ip()
        logger.info(f"🚀 NetCast Audio Pro Server starting...")
        logger.info(f"📡 WebSocket: ws://{local_ip}:{self.port}")
        logger.info(f"🌐 Network: ws://{self.host}:{self.port}")
        
        async with websockets.serve(
            self.register_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10
        ):
            logger.info(f"✅ Server running on port {self.port}")
            logger.info(f"🎙️ Ready for audio streaming!")
            
            # Keep server running
            await asyncio.Future()  # Run forever

def main():
    """Main entry point"""
    server = AudioStreamServer()
    
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"💥 Server error: {e}")

if __name__ == "__main__":
    main()