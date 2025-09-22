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
# psutil wird dynamisch importiert wo benötigt

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
        """Sammle echte Systemmetriken mit nativen Linux-Tools"""
        metrics = {}
        
        try:
            # CPU Auslastung - erst mit psutil versuchen, dann native Linux-Tools
            try:
                import psutil
                cpu_percent = psutil.cpu_percent(interval=0.1)
                metrics['cpu'] = f"{cpu_percent:.1f}%"
            except ImportError:
                # Fallback mit /proc/stat für echte CPU-Werte
                try:
                    with open('/proc/stat', 'r') as f:
                        line = f.readline()
                        cpu_times = [int(x) for x in line.split()[1:]]
                        idle_time = cpu_times[3]
                        total_time = sum(cpu_times)
                        cpu_percent = 100.0 * (total_time - idle_time) / total_time
                        metrics['cpu'] = f"{cpu_percent:.1f}%"
                except:
                    # Fallback mit uptime command
                    try:
                        result = subprocess.run(['uptime'], capture_output=True, text=True, timeout=2)
                        if result.returncode == 0:
                            # Parse load average aus uptime
                            load_line = result.stdout.strip()
                            if 'load average:' in load_line:
                                load_avg = load_line.split('load average:')[1].split(',')[0].strip()
                                cpu_percent = min(float(load_avg) * 25, 100)  # Approximation
                                metrics['cpu'] = f"{cpu_percent:.1f}%"
                    except:
                        metrics['cpu'] = "N/A"
            
            # RAM Auslastung - erst mit psutil, dann /proc/meminfo
            try:
                import psutil
                ram = psutil.virtual_memory()
                metrics['ram'] = f"{ram.percent:.1f}%"
            except ImportError:
                try:
                    with open('/proc/meminfo', 'r') as f:
                        meminfo = {}
                        for line in f:
                            key, value = line.split(':')
                            meminfo[key.strip()] = int(value.split()[0]) * 1024  # Convert to bytes
                        
                        total = meminfo['MemTotal']
                        free = meminfo['MemFree'] + meminfo.get('Buffers', 0) + meminfo.get('Cached', 0)
                        used = total - free
                        ram_percent = (used / total) * 100
                        metrics['ram'] = f"{ram_percent:.1f}%"
                except:
                    # Fallback mit free command
                    try:
                        result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=2)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            if len(lines) > 1:
                                parts = lines[1].split()
                                if len(parts) >= 3:
                                    total = int(parts[1])
                                    used = int(parts[2])
                                    ram_percent = (used / total) * 100
                                    metrics['ram'] = f"{ram_percent:.1f}%"
                    except:
                        metrics['ram'] = "N/A"
            
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
                # Alternative: /sys/class/thermal für andere Linux-Systeme
                try:
                    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                        temp_millicelsius = int(f.read().strip())
                        temp_celsius = temp_millicelsius / 1000.0
                        metrics['cpu_temp'] = f"{temp_celsius:.1f}"
                except:
                    pass  # CPU-Temperatur nicht verfügbar
            
            # Festplattennutzung - erst mit psutil, dann mit df
            try:
                import psutil
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                metrics['disk_usage'] = f"{disk_percent:.1f}%"
            except ImportError:
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
            
            # Uptime - reale Systemzeit
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    days = int(uptime_seconds // 86400)
                    hours = int((uptime_seconds % 86400) // 3600)
                    minutes = int((uptime_seconds % 3600) // 60)
                    
                    if days > 0:
                        metrics['uptime'] = f"{days}d {hours}h {minutes}m"
                    elif hours > 0:
                        metrics['uptime'] = f"{hours}h {minutes}m"
                    else:
                        metrics['uptime'] = f"{minutes}m"
            except:
                # Fallback
                metrics['uptime'] = f"{int(time.time() - start_time)}s"
            
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            # Absoluter Fallback bei Fehlern
            metrics = {
                'cpu': "Error",
                'ram': "Error", 
                'uptime': "Error"
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
        """Sammle echte Netzwerk-Metriken mit nativen Linux-Tools"""
        
        # Initialisiere Network-Stats falls nicht vorhanden
        if not hasattr(self.__class__, '_network_stats'):
            self.__class__._network_stats = {
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
            current_time = time.time()
            
            # Echte Netzwerk-Statistiken - erst mit psutil, dann mit /proc/net/dev
            bytes_sent = 0
            bytes_recv = 0
            
            try:
                import psutil
                net_io = psutil.net_io_counters()
                bytes_sent = net_io.bytes_sent
                bytes_recv = net_io.bytes_recv
            except ImportError:
                # Fallback mit /proc/net/dev für echte Netzwerk-Statistiken
                try:
                    with open('/proc/net/dev', 'r') as f:
                        lines = f.readlines()
                        for line in lines[2:]:  # Skip headers
                            parts = line.split()
                            if len(parts) >= 10:
                                interface = parts[0].rstrip(':')
                                # Skip loopback
                                if interface != 'lo':
                                    bytes_recv += int(parts[1])    # RX bytes
                                    bytes_sent += int(parts[9])    # TX bytes
                except:
                    pass
            
            # Berechne Geschwindigkeiten
            time_diff = current_time - self.__class__._network_stats['last_time']
            
            if time_diff > 0 and self.__class__._network_stats['last_bytes_sent'] > 0:
                bytes_sent_diff = bytes_sent - self.__class__._network_stats['last_bytes_sent']
                bytes_recv_diff = bytes_recv - self.__class__._network_stats['last_bytes_recv']
                
                # Berechne Mbps (nur positive Werte)
                if bytes_sent_diff >= 0 and bytes_recv_diff >= 0:
                    download_mbps = (bytes_recv_diff * 8) / (time_diff * 1000000)  # Mbps
                    upload_mbps = (bytes_sent_diff * 8) / (time_diff * 1000000)    # Mbps
                    
                    # Aktualisiere Statistiken
                    self.__class__._network_stats['last_bytes_sent'] = bytes_sent
                    self.__class__._network_stats['last_bytes_recv'] = bytes_recv
                    self.__class__._network_stats['last_time'] = current_time
                    
                    # Prüfe auf neuen Tag
                    current_day = time.strftime('%Y-%m-%d')
                    if current_day != self.__class__._network_stats['last_reset_day']:
                        self.__class__._network_stats['max_download_today'] = 0
                        self.__class__._network_stats['max_upload_today'] = 0
                        self.__class__._network_stats['total_download_today'] = 0
                        self.__class__._network_stats['total_upload_today'] = 0
                        self.__class__._network_stats['last_reset_day'] = current_day
                    
                    # Aktualisiere Max-Werte
                    if download_mbps > self.__class__._network_stats['max_download_today']:
                        self.__class__._network_stats['max_download_today'] = download_mbps
                    if upload_mbps > self.__class__._network_stats['max_upload_today']:
                        self.__class__._network_stats['max_upload_today'] = upload_mbps
                    if download_mbps > self.__class__._network_stats['max_download_alltime']:
                        self.__class__._network_stats['max_download_alltime'] = download_mbps
                    if upload_mbps > self.__class__._network_stats['max_upload_alltime']:
                        self.__class__._network_stats['max_upload_alltime'] = upload_mbps
                    
                    # Aktualisiere Traffic-Counter
                    if bytes_recv_diff > 0:
                        self.__class__._network_stats['total_download_today'] += bytes_recv_diff
                        self.__class__._network_stats['total_download_alltime'] += bytes_recv_diff
                    if bytes_sent_diff > 0:
                        self.__class__._network_stats['total_upload_today'] += bytes_sent_diff
                        self.__class__._network_stats['total_upload_alltime'] += bytes_sent_diff
                    
                    # Formatiere Ausgabe
                    metrics['download'] = f"{download_mbps:.2f} Mbps"
                    metrics['upload'] = f"{upload_mbps:.2f} Mbps"
                    metrics['download_mbps'] = download_mbps
                    metrics['upload_mbps'] = upload_mbps
                    
                    # Max-Werte
                    if self.__class__._network_stats['max_download_today'] > 0:
                        metrics['max_download_today'] = f"{self.__class__._network_stats['max_download_today']:.2f} Mbps"
                    if self.__class__._network_stats['max_upload_today'] > 0:
                        metrics['max_upload_today'] = f"{self.__class__._network_stats['max_upload_today']:.2f} Mbps"
                    if self.__class__._network_stats['max_download_alltime'] > 0:
                        metrics['max_download_alltime'] = f"{self.__class__._network_stats['max_download_alltime']:.2f} Mbps"
                    if self.__class__._network_stats['max_upload_alltime'] > 0:
                        metrics['max_upload_alltime'] = f"{self.__class__._network_stats['max_upload_alltime']:.2f} Mbps"
                    
                    # Traffic-Counter (formatiert)
                    def format_bytes(bytes_val):
                        if bytes_val == 0:
                            return "0 B"
                        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                            if bytes_val < 1024:
                                return f"{bytes_val:.1f} {unit}"
                            bytes_val /= 1024
                        return f"{bytes_val:.1f} PB"
                    
                    if self.__class__._network_stats['total_download_today'] > 0:
                        metrics['total_download_today'] = format_bytes(self.__class__._network_stats['total_download_today'])
                    if self.__class__._network_stats['total_upload_today'] > 0:
                        metrics['total_upload_today'] = format_bytes(self.__class__._network_stats['total_upload_today'])
                    if self.__class__._network_stats['total_download_alltime'] > 0:
                        metrics['total_download_alltime'] = format_bytes(self.__class__._network_stats['total_download_alltime'])
                    if self.__class__._network_stats['total_upload_alltime'] > 0:
                        metrics['total_upload_alltime'] = format_bytes(self.__class__._network_stats['total_upload_alltime'])
                        
                else:
                    # Negative Differenz (Counter Reset) - initialisiere neu
                    self.__class__._network_stats['last_bytes_sent'] = bytes_sent
                    self.__class__._network_stats['last_bytes_recv'] = bytes_recv
                    self.__class__._network_stats['last_time'] = current_time
                    metrics['download'] = "0.00 Mbps"
                    metrics['upload'] = "0.00 Mbps"
                    metrics['download_mbps'] = 0
                    metrics['upload_mbps'] = 0
            else:
                # Erste Messung oder keine Zeit vergangen
                self.__class__._network_stats['last_bytes_sent'] = bytes_sent
                self.__class__._network_stats['last_bytes_recv'] = bytes_recv
                self.__class__._network_stats['last_time'] = current_time
                metrics['download'] = "0.00 Mbps"
                metrics['upload'] = "0.00 Mbps"
                metrics['download_mbps'] = 0
                metrics['upload_mbps'] = 0
                
        except Exception as e:
            print(f"Error getting network metrics: {e}")
            # Fallback bei Fehlern
            metrics = {
                'download': "Error",
                'upload': "Error",
                'download_mbps': 0,
                'upload_mbps': 0
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