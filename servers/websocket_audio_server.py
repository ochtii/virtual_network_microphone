#!/usr/bin/env python3
"""
Sadistic WebSocket Audio Server
Empfängt binäre Audio-Daten via WebSocket und stellt sie als HTTP Stream bereit
Port 42069 - OPTIMIERT FÜR NIEDRIGE LATENZ!
"""

import asyncio
import websockets
import ssl
import json
import time
import queue
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

class SadisticAudioBuffer:
    """Globaler Audio-Buffer für alle Streams"""
    def __init__(self):
        self.audio_queue = queue.Queue(maxsize=200)  # Reduziert für niedrige Latenz
        self.active_streams = []
        self.websocket_clients = set()
        
    def add_audio(self, audio_data):
        """Audio-Daten hinzufügen"""
        try:
            # Bei vollem Buffer - alte Daten wegwerfen (niedrige Latenz!)
            if self.audio_queue.full():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    pass
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            pass  # Buffer voll - Skip für niedrige Latenz
    
    def get_audio(self, timeout=0.1):  # Kurzer Timeout für niedrige Latenz
        """Audio-Daten holen"""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

# Globaler Buffer
audio_buffer = SadisticAudioBuffer()

class SadisticHTTPHandler(BaseHTTPRequestHandler):
    """HTTP Handler für Audio-Stream"""
    
    def log_message(self, format, *args):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] 🎵 HTTP: {format % args}")
    
    def do_GET(self):
        if self.path == '/stream':
            self.serve_audio_stream()
        elif self.path == '/':
            self.serve_status_page()
        else:
            self.send_error(404, "Nur /stream und / verfügbar!")
    
    def serve_audio_stream(self):
        """Audio-Stream für Linux Client"""
        self.send_response(200)
        self.send_header('Content-Type', 'audio/webm')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        print(f"🔊 Audio-Stream Client verbunden: {self.client_address}")
        audio_buffer.active_streams.append(self)
        
        try:
            while True:
                audio_data = audio_buffer.get_audio()
                if audio_data:
                    try:
                        self.wfile.write(audio_data)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        break
        except Exception as e:
            print(f"❌ Stream error: {e}")
        finally:
            if self in audio_buffer.active_streams:
                audio_buffer.active_streams.remove(self)
            print(f"🔇 Audio-Stream Client getrennt: {self.client_address}")
    
    def serve_status_page(self):
        """Status-Seite"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🚀 Sadistic WebSocket Audio Server</title>
            <meta charset="utf-8">
            <style>
                body {{ background: #1a1a1a; color: #00ff41; font-family: monospace; 
                       text-align: center; padding: 50px; }}
                .status {{ background: #2a2a2a; padding: 20px; margin: 20px auto; 
                         max-width: 500px; border-radius: 10px; border: 1px solid #00ff41; }}
                .latency {{ color: #ff6b6b; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🚀 SADISTIC WEBSOCKET AUDIO SERVER</h1>
            <div class="status">
                <h2>📊 Server Status</h2>
                <p><strong>Port:</strong> 42069 (WebSocket + HTTP)</p>
                <p><strong>WebSocket Clients:</strong> {len(audio_buffer.websocket_clients)}</p>
                <p><strong>HTTP Streams:</strong> {len(audio_buffer.active_streams)}</p>
                <p><strong>Audio Buffer:</strong> {audio_buffer.audio_queue.qsize()}/200</p>
                <p class="latency"><strong>Latenz-Optimiert:</strong> ~10-50ms</p>
                <p><strong>Zeit:</strong> {time.strftime('%H:%M:%S')}</p>
            </div>
            <div class="status">
                <h2>🎯 Endpoints</h2>
                <p><strong>WSS /</strong> - WebSocket Audio-Daten empfangen</p>
                <p><strong>GET /stream</strong> - HTTP Audio-Stream bereitstellen</p>
            </div>
            <h3>🎭 Binär-optimiert für sadistische Experimente!</h3>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

async def handle_websocket(websocket, path):
    """WebSocket Handler für Audio-Daten"""
    client_addr = websocket.remote_address
    print(f"🔌 WebSocket verbunden: {client_addr}")
    audio_buffer.websocket_clients.add(websocket)
    
    try:
        async for message in websocket:
            if isinstance(message, bytes):
                # Binäre Audio-Daten
                audio_buffer.add_audio(message)
                # print(f"📤 Audio empfangen: {len(message)} bytes")  # Zu viel Logging für Latenz
            else:
                # Text-Nachrichten (Control)
                try:
                    data = json.loads(message)
                    if data.get('type') == 'ping':
                        await websocket.send(json.dumps({'type': 'pong', 'timestamp': time.time()}))
                except json.JSONDecodeError:
                    pass
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        audio_buffer.websocket_clients.discard(websocket)
        print(f"🔌 WebSocket getrennt: {client_addr}")

def run_http_server():
    """HTTP Server für Audio-Streams"""
    print("🎵 Starting HTTP Audio Stream Server...")
    with socketserver.TCPServer(("0.0.0.0", 42069), SadisticHTTPHandler) as httpd:
        # SSL Context für HTTPS
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('/home/ochtii/virtual_mic/server.crt', '/home/ochtii/virtual_mic/server.key')
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        
        print("✅ HTTPS Audio Stream Server running on port 42069")
        httpd.serve_forever()

async def run_websocket_server():
    """WebSocket Server für Audio-Empfang"""
    print("🚀 Starting WebSocket Audio Server...")
    
    # SSL Context für WSS
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain('/home/ochtii/virtual_mic/server.crt', '/home/ochtii/virtual_mic/server.key')
    
    # WebSocket Server auf Port 42069 (gleicher Port wie HTTP)
    async with websockets.serve(handle_websocket, "0.0.0.0", 42069, ssl=ssl_context):
        print("✅ WebSocket Server running on wss://192.168.188.90:42069")
        await asyncio.Future()  # Run forever

def main():
    """Hauptfunktion"""
    print("🚀 SADISTIC WEBSOCKET AUDIO SERVER")
    print("=" * 60)
    print("🔥 Port: 42069 (WebSocket + HTTP)")
    print("📡 WSS: Binäre Audio-Daten empfangen")  
    print("🎵 HTTPS: Audio-Stream bereitstellen")
    print("⚡ Latenz-optimiert: ~10-50ms")
    print("🔒 SSL-verschlüsselt")
    print("=" * 60)
    
    # HTTP Server in separatem Thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # WebSocket Server in Async Loop
    try:
        asyncio.run(run_websocket_server())
    except KeyboardInterrupt:
        print("\n🛑 Server gestoppt")

if __name__ == '__main__':
    main()