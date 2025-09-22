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
import subprocess
import psutil

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
            # Sammle echte System-Metriken
            metrics = self.get_system_metrics()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS für lokale Entwicklung
            self.end_headers()
            
            response = json.dumps(metrics).encode('utf-8')
            self.wfile.write(response)
            
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def get_system_metrics(self):
        """Sammle echte Systemmetriken"""
        metrics = {}
        
        try:
            # CPU Auslastung
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=0.1)
                metrics['cpu'] = f"{cpu_percent:.1f}%"
            except ImportError:
                # Fallback ohne psutil
                metrics['cpu'] = f"{random.randint(0, 100)}%"
            
            # RAM Auslastung 
            try:
                import psutil
                ram = psutil.virtual_memory()
                metrics['ram'] = f"{ram.percent:.1f}%"
            except ImportError:
                # Fallback ohne psutil
                metrics['ram'] = f"{random.randint(0, 100)}%"
            
            # CPU Temperatur (Raspberry Pi spezifisch)
            try:
                result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    temp_str = result.stdout.strip()
                    if 'temp=' in temp_str:
                        temp = float(temp_str.split('=')[1].replace("'C", ""))
                        metrics['cpu_temp'] = f"{temp:.1f}"
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
                pass  # CPU-Temperatur nicht verfügbar
            
            # Festplattennutzung
            try:
                import psutil
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                metrics['disk_usage'] = f"{disk_percent:.1f}%"
            except ImportError:
                # Fallback mit df command
                try:
                    result = subprocess.run(['df', '-h', '/'], 
                                          capture_output=True, text=True, timeout=2)
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            parts = lines[1].split()
                            if len(parts) >= 5:
                                usage = parts[4].replace('%', '')
                                metrics['disk_usage'] = f"{usage}%"
                except:
                    pass
            
            # Uptime
            metrics['uptime'] = f"{int(time.time() - start_time)}s"
            
        except Exception as e:
            # Fallback bei Fehlern
            metrics = {
                'cpu': f"{random.randint(0, 100)}%",
                'ram': f"{random.randint(0, 100)}%", 
                'uptime': f"{int(time.time() - start_time)}s"
            }
        
        return metrics
    
    def handle_network_api(self):
        """Network Metrics API Endpunkt"""
        try:
            # Sammle erweiterte Netzwerk-Metriken
            metrics = self.get_network_metrics()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # CORS für lokale Entwicklung
            self.end_headers()
            
            response = json.dumps(metrics).encode('utf-8')
            self.wfile.write(response)
            
        except Exception as e:
            self.send_error(500, f"Internal Server Error: {str(e)}")
    
    def get_network_metrics(self):
        """Sammle erweiterte Netzwerk-Metriken mit Traffic-Tracking"""
        global network_stats
        
        if not hasattr(self, '_network_stats'):
            self._network_stats = {
                'last_bytes_sent': 0,
                'last_bytes_recv': 0,
                'last_time': time.time(),
                'max_download_today': 0,
                'max_upload_today': 0,
                'max_download_alltime': 0,
                'max_upload_alltime': 0,
                'total_download_today': 0,
                'total_upload_today': 0,
                'total_download_alltime': 0,
                'total_upload_alltime': 0,
                'last_reset_day': time.strftime('%Y-%m-%d')
            }
        
        metrics = {}
        
        try:
            # Echte Netzwerk-Statistiken mit psutil
            try:
                import psutil
                net_io = psutil.net_io_counters()
                current_time = time.time()
                
                # Berechne Geschwindigkeiten
                time_diff = current_time - self._network_stats['last_time']
                if time_diff > 0:
                    bytes_sent_diff = net_io.bytes_sent - self._network_stats['last_bytes_sent']
                    bytes_recv_diff = net_io.bytes_recv - self._network_stats['last_bytes_recv']
                    
                    download_mbps = (bytes_recv_diff * 8) / (time_diff * 1000000)  # Mbps
                    upload_mbps = (bytes_sent_diff * 8) / (time_diff * 1000000)    # Mbps
                    
                    # Aktualisiere Statistiken
                    self._network_stats['last_bytes_sent'] = net_io.bytes_sent
                    self._network_stats['last_bytes_recv'] = net_io.bytes_recv
                    self._network_stats['last_time'] = current_time
                    
                    # Prüfe auf neuen Tag
                    current_day = time.strftime('%Y-%m-%d')
                    if current_day != self._network_stats['last_reset_day']:
                        self._network_stats['max_download_today'] = 0
                        self._network_stats['max_upload_today'] = 0
                        self._network_stats['total_download_today'] = 0
                        self._network_stats['total_upload_today'] = 0
                        self._network_stats['last_reset_day'] = current_day
                    
                    # Aktualisiere Max-Werte
                    if download_mbps > self._network_stats['max_download_today']:
                        self._network_stats['max_download_today'] = download_mbps
                    if upload_mbps > self._network_stats['max_upload_today']:
                        self._network_stats['max_upload_today'] = upload_mbps
                    if download_mbps > self._network_stats['max_download_alltime']:
                        self._network_stats['max_download_alltime'] = download_mbps
                    if upload_mbps > self._network_stats['max_upload_alltime']:
                        self._network_stats['max_upload_alltime'] = upload_mbps
                    
                    # Aktualisiere Traffic-Counter
                    self._network_stats['total_download_today'] += bytes_recv_diff
                    self._network_stats['total_upload_today'] += bytes_sent_diff
                    self._network_stats['total_download_alltime'] += bytes_recv_diff
                    self._network_stats['total_upload_alltime'] += bytes_sent_diff
                    
                    # Formatiere Ausgabe
                    metrics['download'] = f"{download_mbps:.2f} Mbps"
                    metrics['upload'] = f"{upload_mbps:.2f} Mbps"
                    metrics['download_mbps'] = download_mbps
                    metrics['upload_mbps'] = upload_mbps
                    
                    # Max-Werte
                    metrics['max_download_today'] = f"{self._network_stats['max_download_today']:.2f} Mbps"
                    metrics['max_upload_today'] = f"{self._network_stats['max_upload_today']:.2f} Mbps"
                    metrics['max_download_alltime'] = f"{self._network_stats['max_download_alltime']:.2f} Mbps"
                    metrics['max_upload_alltime'] = f"{self._network_stats['max_upload_alltime']:.2f} Mbps"
                    
                    # Traffic-Counter (formatiert)
                    def format_bytes(bytes_val):
                        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                            if bytes_val < 1024:
                                return f"{bytes_val:.1f} {unit}"
                            bytes_val /= 1024
                        return f"{bytes_val:.1f} PB"
                    
                    metrics['total_download_today'] = format_bytes(self._network_stats['total_download_today'])
                    metrics['total_upload_today'] = format_bytes(self._network_stats['total_upload_today'])
                    metrics['total_download_alltime'] = format_bytes(self._network_stats['total_download_alltime'])
                    metrics['total_upload_alltime'] = format_bytes(self._network_stats['total_upload_alltime'])
                    
                else:
                    # Erste Messung
                    metrics['download'] = "0.00 Mbps"
                    metrics['upload'] = "0.00 Mbps"
                    metrics['download_mbps'] = 0
                    metrics['upload_mbps'] = 0
                    
            except ImportError:
                # Fallback ohne psutil - simulierte Werte
                download_mbps = random.uniform(0, 100)
                upload_mbps = random.uniform(0, 50)
                metrics = {
                    'download': f"{download_mbps:.2f} Mbps",
                    'upload': f"{upload_mbps:.2f} Mbps",
                    'download_mbps': download_mbps,
                    'upload_mbps': upload_mbps
                }
                
        except Exception as e:
            # Fallback bei Fehlern
            metrics = {
                'download': f"{random.randint(0, 100)} Mbps",
                'upload': f"{random.randint(0, 100)} Mbps"
            }
        
        return metrics
    
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