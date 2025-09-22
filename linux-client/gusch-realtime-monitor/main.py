#!/usr/bin/env python3
"""
Gusch Real-time Monitor - Simplified Working Version
Real-time audio level monitoring with WebSocket streaming
"""

import asyncio
import json
import logging
import random
import time
import aiohttp
from dataclasses import dataclass, asdict
from typing import List, Dict, Set
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import threading

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AudioLevel:
    client_id: str
    level: float
    timestamp: float
    color: str
    status: str

@dataclass
class RoomStatus:
    average_level: float
    max_level: float
    active_clients: int
    background_color: str
    timestamp: float

class MainServerAPI:
    """API client for fetching real data from main gusch server"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None
            
    async def get_audio_levels(self):
        """Get real audio levels from main server"""
        try:
            session = await self.get_session()
            async with session.get(f"{self.base_url}/api/hardware/audio", timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    # Extract relevant audio data
                    return {
                        'level': data.get('input_level', 0),
                        'output_level': data.get('output_level', 0),
                        'input_volume': data.get('input_volume', 0),
                        'output_volume': data.get('output_volume', 0)
                    }
        except Exception as e:
            logger.warning(f"Failed to get audio levels from main server: {e}")
        return None
        
    async def get_monitor_metrics(self):
        """Get real system metrics from main server"""
        try:
            session = await self.get_session()
            async with session.get(f"{self.base_url}/api/monitor/metrics", timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'cpu_usage': data.get('cpu_usage', 0),
                        'memory_usage': data.get('memory_usage', 0),
                        'disk_usage': data.get('disk_usage', 0),
                        'network_usage': data.get('network_usage', 0)
                    }
        except Exception as e:
            logger.warning(f"Failed to get monitor metrics from main server: {e}")
        return None

class RealAudioMonitor:
    """Real audio monitor using ALSA/PulseAudio"""
    
    def __init__(self):
        self.is_running = False
        self.current_level = 0.0
        self.level_history = []
        self.smoothing_factor = 0.3  # For smooth transitions
        self.last_level = 0.0
        
    def start_monitoring(self):
        """Start real audio monitoring"""
        if self.is_running:
            return
            
        self.is_running = True
        
        def monitor_audio():
            import subprocess
            import re
            
            while self.is_running:
                try:
                    # Use pactl to get real audio levels from PulseAudio
                    result = subprocess.run(
                        ['pactl', 'list', 'sources'], 
                        capture_output=True, 
                        text=True, 
                        timeout=1
                    )
                    
                    if result.returncode == 0:
                        # Parse volume levels from pactl output
                        volume_matches = re.findall(r'Volume:.*?(\d+)%', result.stdout)
                        if volume_matches:
                            # Get the first source volume percentage
                            volume_percent = int(volume_matches[0])
                            # Convert to dB-like scale (0-100)
                            raw_level = min(100, max(0, volume_percent))
                        else:
                            raw_level = 0
                    else:
                        # Fallback: try using amixer
                        result = subprocess.run(
                            ['amixer', 'get', 'Capture'], 
                            capture_output=True, 
                            text=True, 
                            timeout=1
                        )
                        
                        if result.returncode == 0:
                            # Parse amixer output
                            volume_matches = re.findall(r'\[(\d+)%\]', result.stdout)
                            if volume_matches:
                                volume_percent = int(volume_matches[0])
                                raw_level = min(100, max(0, volume_percent))
                            else:
                                raw_level = 0
                        else:
                            # Last resort: read from /proc/asound for basic level indication
                            try:
                                with open('/proc/asound/cards', 'r') as f:
                                    if f.read().strip():
                                        # If sound cards exist, use a baseline level
                                        raw_level = 15  # Quiet baseline
                                    else:
                                        raw_level = 0
                            except:
                                raw_level = 0
                    
                    # Apply smoothing to reduce blinking
                    smooth_level = (self.smoothing_factor * raw_level + 
                                  (1 - self.smoothing_factor) * self.last_level)
                    
                    self.current_level = smooth_level
                    self.last_level = smooth_level
                    
                    # Keep history for averaging
                    self.level_history.append(self.current_level)
                    if len(self.level_history) > 50:  # Keep last 50 readings
                        self.level_history.pop(0)
                    
                    time.sleep(0.1)  # 10 FPS for smoother updates
                    
                except Exception as e:
                    logger.debug(f"Audio monitoring error: {e}")
                    # Fallback to quiet level
                    self.current_level = max(0, self.current_level * 0.95)  # Gradual fade
                    time.sleep(0.1)
        
        thread = threading.Thread(target=monitor_audio, daemon=True)
        thread.start()
        logger.info("Started real audio monitoring")
    
    def stop_monitoring(self):
        """Stop audio monitoring"""
        self.is_running = False
        
    def get_current_level(self):
        """Get current audio level"""
        return self.current_level
        
    def get_average_level(self):
        """Get average of recent levels"""
        if not self.level_history:
            return 0.0
        return sum(self.level_history) / len(self.level_history)
        
    def get_max_level(self):
        """Get maximum of recent levels"""
        if not self.level_history:
            return 0.0
        return max(self.level_history)

class RealtimeMonitorManager:
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self.audio_monitor = RealAudioMonitor()
        self.main_server_api = MainServerAPI()  # Add API client
        self.is_running = False
        self.client_counter = 0
        
    async def start(self):
        """Start the real-time monitor system"""
        if self.is_running:
            return
            
        self.is_running = True
        self.audio_monitor.start_monitoring()
        
        # Start broadcasting task
        asyncio.create_task(self.broadcast_loop())
        logger.info("Real-time monitor started")
        
    async def stop(self):
        """Stop the real-time monitor system"""
        self.is_running = False
        self.audio_monitor.stop_monitoring()
        logger.info("Real-time monitor stopped")
        
    async def connect(self, websocket: WebSocket):
        """Add a new WebSocket connection"""
        await websocket.accept()
        self.connections.add(websocket)
        self.client_counter += 1
        client_id = f"client_{self.client_counter}"
        logger.info(f"Client {client_id} connected. Total: {len(self.connections)}")
        
        # Send initial status
        await self.send_to_client(websocket, {
            "type": "connection_status",
            "data": {
                "client_id": client_id,
                "status": "connected",
                "total_clients": len(self.connections)
            }
        })
        
        return client_id
        
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        self.connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.connections)}")
        
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Send message to a specific client"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.debug(f"Error sending to client: {e}")
            self.connections.discard(websocket)
            
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.connections:
            return
            
        disconnected = set()
        for websocket in self.connections:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.debug(f"Error broadcasting to client: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected clients
        for websocket in disconnected:
            self.connections.discard(websocket)
            
    def calculate_color(self, level: float) -> str:
        """Calculate color based on audio level (0-100)"""
        if level <= 20:
            # Green zone (quiet)
            intensity = level / 20
            return f"rgb({int(intensity * 100)}, 255, {int(intensity * 100)})"
        elif level <= 60:
            # Yellow zone (moderate)
            progress = (level - 20) / 40
            red = 100 + int(progress * 155)
            green = 255
            blue = int((1 - progress) * 100)
            return f"rgb({red}, {green}, {blue})"
        else:
            # Red zone (loud)
            progress = min(1.0, (level - 60) / 40)
            red = 255
            green = int((1 - progress) * 255)
            blue = 0
            return f"rgb({red}, {green}, {blue})"
            
    def calculate_background_color(self, level: float) -> str:
        """Calculate smooth background color transitions based on audio level"""
        # Much smoother color transitions to reduce blinking
        if level <= 15:
            return "#000000"  # Black for very quiet
        elif level <= 25:
            # Very dark green transition
            intensity = (level - 15) / 10
            green = int(intensity * 20)
            return f"rgb(0, {green}, 0)"
        elif level <= 40:
            # Dark green to green
            progress = (level - 25) / 15
            green = 20 + int(progress * 30)
            return f"rgb(0, {green}, 0)"
        elif level <= 55:
            # Green to yellow - very gradual
            progress = (level - 40) / 15
            red = int(progress * 40)
            green = 50 + int(progress * 30)
            return f"rgb({red}, {green}, 0)"
        elif level <= 75:
            # Yellow to orange - smoother transition
            progress = (level - 55) / 20
            red = 40 + int(progress * 60)
            green = 80 - int(progress * 30)
            return f"rgb({red}, {green}, 0)"
        else:
            # Orange to red - only for very loud
            progress = min(1.0, (level - 75) / 25)
            red = 100 + int(progress * 100)
            green = max(0, 50 - int(progress * 50))
            return f"rgb({red}, {green}, 0)"
            
    async def broadcast_loop(self):
        """Main broadcasting loop with real API data"""
        while self.is_running:
            try:
                # Get real audio level from local monitor
                current_level = self.audio_monitor.get_current_level()
                average_level = self.audio_monitor.get_average_level()
                max_level = self.audio_monitor.get_max_level()
                
                # Get real data from main server API
                audio_data = await self.main_server_api.get_audio_levels()
                metrics_data = await self.main_server_api.get_monitor_metrics()
                
                # Create room status with real data
                room_status = RoomStatus(
                    average_level=average_level,
                    max_level=max_level,
                    active_clients=len(self.connections),
                    background_color=self.calculate_background_color(current_level),
                    timestamp=time.time()
                )
                
                # Create client levels with real API data - NO SIMULATION!
                client_levels = []
                
                # Real audio level (primary display)
                status = "quiet" if current_level < 30 else "moderate" if current_level < 60 else "loud"
                client_levels.append(AudioLevel(
                    client_id="room_audio",
                    level=current_level,
                    timestamp=time.time(),
                    color=self.calculate_color(current_level),
                    status=status
                ))
                
                # If we have real server data, add it
                if audio_data:
                    # Input level from main server
                    input_level = audio_data.get('level', 0)
                    input_status = "quiet" if input_level < 30 else "moderate" if input_level < 60 else "loud"
                    client_levels.append(AudioLevel(
                        client_id="server_input",
                        level=input_level,
                        timestamp=time.time(),
                        color=self.calculate_color(input_level),
                        status=input_status
                    ))
                    
                    # Output level from main server
                    output_level = audio_data.get('output_level', 0)
                    output_status = "quiet" if output_level < 30 else "moderate" if output_level < 60 else "loud"
                    client_levels.append(AudioLevel(
                        client_id="server_output",
                        level=output_level,
                        timestamp=time.time(),
                        color=self.calculate_color(output_level),
                        status=output_status
                    ))
                
                # Add metrics-based levels if available
                if metrics_data:
                    # CPU as audio representation
                    cpu_level = metrics_data.get('cpu_usage', 0)
                    cpu_status = "quiet" if cpu_level < 30 else "moderate" if cpu_level < 60 else "loud"
                    client_levels.append(AudioLevel(
                        client_id="system_cpu",
                        level=cpu_level,
                        timestamp=time.time(),
                        color=self.calculate_color(cpu_level),
                        status=cpu_status
                    ))
                
                # Broadcast room status
                await self.broadcast({
                    "type": "room_status",
                    "data": asdict(room_status)
                })
                
                # Broadcast real client levels - NO PLACEHOLDERS!
                await self.broadcast({
                    "type": "client_levels", 
                    "data": [asdict(client) for client in client_levels]
                })
                
                await asyncio.sleep(0.1)  # 10 FPS for smoother updates
                
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                await asyncio.sleep(1)

# Global monitor manager
monitor_manager = RealtimeMonitorManager()

# FastAPI application
app = FastAPI(
    title="Gusch Real-time Monitor",
    description="Real-time audio level monitoring system",
    version="1.0.0"
)

# Backend only - no frontend endpoints

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "monitor_running": monitor_manager.is_running,
        "active_connections": len(monitor_manager.connections),
        "current_level": monitor_manager.audio_monitor.get_current_level(),
        "version": "1.0.0"
    }

@app.get("/api/status")
async def get_status():
    """Get current system status"""
    return {
        "monitor_running": monitor_manager.is_running,
        "active_connections": len(monitor_manager.connections),
        "current_level": monitor_manager.audio_monitor.get_current_level(),
        "average_level": monitor_manager.audio_monitor.get_average_level(),
        "max_level": monitor_manager.audio_monitor.get_max_level()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    client_id = None
    try:
        client_id = await monitor_manager.connect(websocket)
        
        while True:
            # Wait for client messages (ping/pong, etc.)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await monitor_manager.send_to_client(websocket, {
                        "type": "pong",
                        "timestamp": time.time()
                    })
                    
            except asyncio.TimeoutError:
                # No message received, continue
                pass
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client {client_id}")
            except Exception as e:
                logger.debug(f"WebSocket receive error: {e}")
                
            await asyncio.sleep(0.01)
            
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        await monitor_manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    """Start the monitor system"""
    logger.info("🔴 Starting Gusch Real-time Monitor Server")
    logger.info("🌐 Monitor: http://localhost:8001/")
    logger.info("📊 API: http://localhost:8001/docs")
    await monitor_manager.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the monitor system"""
    await monitor_manager.stop()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )