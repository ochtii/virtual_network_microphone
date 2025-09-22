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

class SimpleAudioSimulator:
    """Simplified audio simulator that always works"""
    
    def __init__(self):
        self.is_running = False
        self.current_level = 0.0
        self.level_history = []
        
    def start_monitoring(self):
        """Start audio simulation"""
        if self.is_running:
            return
            
        self.is_running = True
        
        def simulate_audio():
            while self.is_running:
                # Simulate realistic audio levels
                base_level = 25 + random.random() * 30  # 25-55 base
                
                # Add some variation patterns
                time_factor = time.time() % 60  # 60 second cycle
                variation = 15 * abs(time_factor - 30) / 30  # Peak in middle
                
                # Add random noise
                noise = random.random() * 10 - 5  # ±5 noise
                
                # Calculate final level
                self.current_level = max(0, min(100, base_level + variation + noise))
                
                # Keep history for averaging
                self.level_history.append(self.current_level)
                if len(self.level_history) > 100:  # Keep last 100 readings
                    self.level_history.pop(0)
                
                time.sleep(0.05)  # 20 FPS
        
        thread = threading.Thread(target=simulate_audio, daemon=True)
        thread.start()
        logger.info("Started audio simulation mode")
    
    def stop_monitoring(self):
        """Stop audio simulation"""
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
        self.audio_monitor = SimpleAudioSimulator()
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
        """Calculate background color based on audio level"""
        if level <= 10:
            return "#000000"  # Black for very quiet
        elif level <= 30:
            # Dark green to green
            intensity = (level - 10) / 20
            green = int(intensity * 60)
            return f"rgb(0, {green}, 0)"
        elif level <= 70:
            # Green to yellow
            progress = (level - 30) / 40
            red = int(progress * 100)
            green = 60 + int(progress * 60)
            return f"rgb({red}, {green}, 0)"
        else:
            # Yellow to red
            progress = min(1.0, (level - 70) / 30)
            red = 100 + int(progress * 155)
            green = int((1 - progress) * 120)
            return f"rgb({red}, {green}, 0)"
            
    async def broadcast_loop(self):
        """Main broadcasting loop"""
        while self.is_running:
            try:
                current_level = self.audio_monitor.get_current_level()
                average_level = self.audio_monitor.get_average_level()
                max_level = self.audio_monitor.get_max_level()
                
                # Create room status
                room_status = RoomStatus(
                    average_level=average_level,
                    max_level=max_level,
                    active_clients=len(self.connections),
                    background_color=self.calculate_background_color(current_level),
                    timestamp=time.time()
                )
                
                # Create client levels (simulate multiple clients for demo)
                client_levels = []
                for i in range(min(5, max(1, len(self.connections)))):
                    # Simulate different client levels
                    client_level = current_level + random.random() * 20 - 10
                    client_level = max(0, min(100, client_level))
                    
                    status = "quiet" if client_level < 30 else "moderate" if client_level < 70 else "loud"
                    
                    client_levels.append(AudioLevel(
                        client_id=f"client_{i+1}",
                        level=client_level,
                        timestamp=time.time(),
                        color=self.calculate_color(client_level),
                        status=status
                    ))
                
                # Broadcast room status
                await self.broadcast({
                    "type": "room_status",
                    "data": asdict(room_status)
                })
                
                # Broadcast client levels
                await self.broadcast({
                    "type": "client_levels", 
                    "data": [asdict(client) for client in client_levels]
                })
                
                await asyncio.sleep(0.05)  # 20 FPS
                
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

# Health check endpoint only (no frontend)

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
        "main_simple:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )