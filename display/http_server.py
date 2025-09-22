#!/usr/bin/env python3
"""
Einfacher Python HTTP Server als Ersatz für Node.js/Express
Serviert statische Dateien aus dem public/ Verzeichnis
und stellt API-Endpunkte für System- und Netzwerk-Metriken bereit
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import random
import time
import threading

class APIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Wechsle zum public Verzeichnis für statische Dateien
        os.chdir(os.path.join(os.path.dirname(__file__), 'public'))
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        # Parse URL
        parsed_path = urllib.parse.urlparse(self.path)
        
        # API Endpunkte
        if parsed_path.path == '/api/system':
            self.handle_system_api()
        elif parsed_path.path == '/api/network':
            self.handle_network_api()
        else:
            # Statische Dateien servieren
            super().do_GET()
    
    def handle_system_api(self):
        """System Metrics API Endpunkt"""
        try:
            # Simuliere System-Metriken (wie im ursprünglichen Node.js Server)
            metrics = {
                'cpu': f"{random.randint(0, 100)}%",
                'ram': f"{random.randint(0, 100)}%", 
                'uptime': f"{int(time.time() - start_time)}s"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS für lokale Entwicklung
            self.end_headers()
            
            response = json.dumps(metrics).encode('utf-8')
            self.wfile.write(response)
            
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def handle_network_api(self):
        """Network Metrics API Endpunkt"""
        try:
            # Simuliere Netzwerk-Metriken (wie im ursprünglichen Node.js Server)
            metrics = {
                'download': f"{random.randint(0, 100)} Mbps",
                'upload': f"{random.randint(0, 100)} Mbps"
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS für lokale Entwicklung
            self.end_headers()
            
            response = json.dumps(metrics).encode('utf-8')
            self.wfile.write(response)
            
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def log_message(self, format, *args):
        """Überschreibe Log-Format für sauberere Ausgabe"""
        print(f"[{self.address_string()}] {format % args}")

def start_server(port=3000, host="0.0.0.0"):
    """Startet den HTTP Server"""
    global start_time
    start_time = time.time()
    
    # Gehe zum display Verzeichnis
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    with socketserver.TCPServer((host, port), APIHandler) as httpd:
        print(f"Display API running at http://{host}:{port}")
        print(f"External access: http://192.168.188.90:{port}")
        print(f"Serving static files from: {os.path.join(script_dir, 'public')}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer gestoppt durch Benutzer")
            httpd.shutdown()

if __name__ == "__main__":
    import sys
    
    # Port aus Kommandozeile oder Standard 3000
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    
    try:
        start_server(port)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"Fehler: Port {port} ist bereits in Verwendung!")
            print("Verwende einen anderen Port oder stoppe den anderen Prozess.")
        else:
            print(f"Fehler beim Starten des Servers: {e}")
        sys.exit(1)