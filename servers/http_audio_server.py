#!/usr/bin/env python3
"""
Sadistic HTTP Audio Server
Empfängt Audio-Daten via POST und stellt sie als HTTP Stream bereit
Port 42069 - genau wie die Android App
"""

import asyncio
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import queue
import io

class SadisticAudioServer(BaseHTTPRequestHandler):
    # Globaler Audio-Buffer für alle Clients
    audio_buffer = queue.Queue(maxsize=1000)
    active_streams = []
    
    def log_message(self, format, *args):
        """Custom logging mit sadistic flair"""
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] 🎤 SADISTIC AUDIO: {format % args}")
    
    def do_GET(self):
        """GET /stream - Audio Stream für Linux Client"""
        if self.path == '/stream':
            self.serve_audio_stream()
        elif self.path == '/':
            self.serve_status_page()
        else:
            self.send_error(404, "Nur /stream und / verfügbar, du Sadist!")
    
    def do_POST(self):
        """POST /audio - Audio-Daten von Web App empfangen"""
        if self.path == '/audio':
            self.receive_audio_data()
        else:
            self.send_error(404, "Nur /audio für POST, du Laber-Lanze!")
    
    def serve_audio_stream(self):
        """Streaming Audio für Linux Client"""
        self.send_response(200)
        self.send_header('Content-Type', 'audio/wav')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        self.log_message("🔊 Neuer Audio-Stream Client verbunden")
        SadisticAudioServer.active_streams.append(self)
        
        try:
            while True:
                try:
                    # Audio-Daten aus dem Buffer holen
                    audio_data = SadisticAudioServer.audio_buffer.get(timeout=1.0)
                    self.wfile.write(audio_data)
                    self.wfile.flush()
                except queue.Empty:
                    # Heartbeat senden wenn keine Daten
                    continue
                except (BrokenPipeError, ConnectionResetError):
                    break
        except:
            pass
        finally:
            if self in SadisticAudioServer.active_streams:
                SadisticAudioServer.active_streams.remove(self)
            self.log_message("🔇 Audio-Stream Client getrennt")
    
    def receive_audio_data(self):
        """Audio-Daten von Web App empfangen"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "Keine Audio-Daten, Brüllwürfel!")
                return
            
            # Audio-Daten lesen
            audio_data = self.rfile.read(content_length)
            
            # In Buffer für Stream-Clients einreihen
            try:
                SadisticAudioServer.audio_buffer.put_nowait(audio_data)
            except queue.Full:
                # Buffer voll - alte Daten wegwerfen
                try:
                    SadisticAudioServer.audio_buffer.get_nowait()
                    SadisticAudioServer.audio_buffer.put_nowait(audio_data)
                except queue.Empty:
                    pass
            
            # Erfolg zurückmelden
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'success',
                'message': 'Audio empfangen, du Sadist!',
                'bytes': len(audio_data),
                'active_streams': len(SadisticAudioServer.active_streams)
            }
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.log_message(f"❌ Fehler beim Audio-Empfang: {e}")
            self.send_error(500, f"Audio-Fehler: {e}")
    
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
            <title>🎤 Sadistic Audio Server</title>
            <meta charset="utf-8">
            <style>
                body {{ background: #1a1a1a; color: #ff6b6b; font-family: monospace; 
                       text-align: center; padding: 50px; }}
                .status {{ background: #2a2a2a; padding: 20px; margin: 20px auto; 
                         max-width: 500px; border-radius: 10px; }}
            </style>
        </head>
        <body>
            <h1>🎤 SADISTIC AUDIO SERVER</h1>
            <div class="status">
                <h2>📊 Server Status</h2>
                <p><strong>Port:</strong> 42069</p>
                <p><strong>Aktive Streams:</strong> {len(SadisticAudioServer.active_streams)}</p>
                <p><strong>Buffer Größe:</strong> {SadisticAudioServer.audio_buffer.qsize()}</p>
                <p><strong>Zeit:</strong> {time.strftime('%H:%M:%S')}</p>
            </div>
            <div class="status">
                <h2>🎯 Endpoints</h2>
                <p><strong>POST /audio</strong> - Audio-Daten senden</p>
                <p><strong>GET /stream</strong> - Audio-Stream empfangen</p>
            </div>
            <h3>Bereit für sadistische Audio-Experimente! 🎭</h3>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def do_OPTIONS(self):
        """CORS Support für Web App"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_server():
    """Server starten"""
    print("🎤 SADISTIC HTTP AUDIO SERVER")
    print("=" * 50)
    print("🔥 Starting auf Port 42069...")
    print("📡 POST /audio - Audio-Daten empfangen")  
    print("🎵 GET /stream - Audio-Stream bereitstellen")
    print("🌐 GET / - Status-Seite")
    print("=" * 50)
    
    server = HTTPServer(('0.0.0.0', 42069), SadisticAudioServer)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server gestoppt")
        server.shutdown()

if __name__ == '__main__':
    run_server()