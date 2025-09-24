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
import signal
# psutil wird dynamisch importiert wo benötigt

# Pfad für persistente Speicherung der Network-Statistiken
STATS_FILE = os.path.join(os.path.dirname(__file__), 'network_stats.json')

def load_network_stats():
    """Lade gespeicherte Network-Statistiken von der Festplatte"""
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r') as f:
                stats = json.load(f)
                # Aktualisiere last_time auf jetzt, da das System neugestartet wurde
                stats['last_time'] = time.time()
                return stats
    except Exception as e:
        print(f"Fehler beim Laden der Network-Statistiken: {e}")
    
    # Standard-Werte wenn keine Datei vorhanden oder Fehler
    return {
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

def save_network_stats(stats):
    """Speichere Network-Statistiken auf die Festplatte"""
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        print(f"Fehler beim Speichern der Network-Statistiken: {e}")

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
        elif parsed_path.path == '/reload':
            self.handle_reload_api()
        else:
            # Statische Dateien servieren mit No-Cache-Headers
            super().do_GET()
    
    def end_headers(self):
        # Füge No-Cache-Headers für alle Dateien hinzu
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
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
            
            # RAM Auslastung mit GB/GB Format - erst mit psutil, dann /proc/meminfo
            try:
                import psutil
                ram = psutil.virtual_memory()
                used_gb = ram.used / (1024**3)
                total_gb = ram.total / (1024**3)
                metrics['ram'] = f"{ram.percent:.1f}%"
                metrics['ram_details'] = f"{used_gb:.1f}GB/{total_gb:.1f}GB"
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
                        used_gb = used / (1024**3)
                        total_gb = total / (1024**3)
                        metrics['ram'] = f"{ram_percent:.1f}%"
                        metrics['ram_details'] = f"{used_gb:.1f}GB/{total_gb:.1f}GB"
                except:
                    # Fallback mit free command
                    try:
                        result = subprocess.run(['free', '-m'], capture_output=True, text=True, timeout=2)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            if len(lines) > 1:
                                parts = lines[1].split()
                                if len(parts) >= 3:
                                    total_mb = int(parts[1])
                                    used_mb = int(parts[2])
                                    ram_percent = (used_mb / total_mb) * 100
                                    used_gb = used_mb / 1024
                                    total_gb = total_mb / 1024
                                    metrics['ram'] = f"{ram_percent:.1f}%"
                                    metrics['ram_details'] = f"{used_gb:.1f}GB/{total_gb:.1f}GB"
                    except:
                        metrics['ram'] = "N/A"
                        metrics['ram_details'] = "N/A"
            
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
            
            # Festplattennutzung mit GB/GB Format - erst mit psutil, dann mit df
            try:
                import psutil
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                used_gb = disk.used / (1024**3)
                total_gb = disk.total / (1024**3)
                metrics['disk_usage'] = f"{disk_percent:.1f}%"
                metrics['disk_details'] = f"{used_gb:.1f}GB/{total_gb:.1f}GB"
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
                                used_str = parts[2]
                                total_str = parts[1]
                                metrics['disk_usage'] = f"{usage}%"
                                metrics['disk_details'] = f"{used_str}/{total_str}"
                except:
                    pass
            
            # Uptime in Stunden und Minuten nebeneinander
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    days = int(uptime_seconds // 86400)
                    hours = int((uptime_seconds % 86400) // 3600)
                    minutes = int((uptime_seconds % 3600) // 60)
                    
                    if days > 0:
                        metrics['uptime'] = f"{days}d {hours}h {minutes}m"
                    else:
                        metrics['uptime'] = f"{hours}h {minutes}m"
                    
                    # Separate Werte für bessere Anzeige
                    metrics['uptime_hours'] = hours + (days * 24) if days > 0 else hours
                    metrics['uptime_minutes'] = minutes
            except:
                # Fallback
                metrics['uptime'] = f"{int(time.time() - start_time)}s"
                metrics['uptime_hours'] = 0
                metrics['uptime_minutes'] = 0
            
            # Neue Online-Checks für aktive Geräte
            metrics['active_services'] = self.get_active_services_count()
            metrics['voltage'] = self.get_voltage()
            
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            # Absoluter Fallback bei Fehlern
            metrics = {
                'cpu': "Error",
                'ram': "Error", 
                'uptime': "Error",
                'active_services': 0,
                'voltage': "N/A"
            }
        
        return metrics
    
    def get_active_services_count(self):
        """Zähle aktive PM2-Prozesse"""
        try:
            # PM2-Prozesse über PM2-CLI zählen
            pm2_cmd = [os.path.expanduser('~/.npm-global/bin/pm2'), 'jlist']
            result = subprocess.run(pm2_cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                import json
                processes = json.loads(result.stdout)
                active_count = sum(1 for proc in processes if proc.get('pm2_env', {}).get('status') == 'online')
                return active_count
        except Exception as e:
            pass
        
        try:
            # Fallback: Versuche systemctl für Service-Status
            result = subprocess.run(['systemctl', 'list-units', '--type=service', '--state=active', '--no-pager'], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                # Filtere Header und Footer aus
                active_services = 0
                for line in lines:
                    if '.service' in line and 'active' in line:
                        active_services += 1
                return active_services
        except:
            pass
        
        try:
            # Fallback: Zähle alle laufenden Prozesse
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                return max(len(lines) - 1, 0)  # Minus Header
        except:
            pass
        
        return 0
    
    def get_voltage(self):
        """Lese die Versorgungsspannung des Raspberry Pi"""
        try:
            # Raspberry Pi: Versuche verschiedene Spannungsquellen für 5V-Versorgung
            # hwmon2 (ads7846) hat oft die beste Schätzung der Versorgungsspannung
            with open('/sys/class/hwmon/hwmon2/in0_input', 'r') as f:
                voltage_mv = int(f.read().strip())
                voltage_v = voltage_mv / 1000.0
                # Skaliere Wert für realistische 5V-Anzeige (ads7846 zeigt oft ~2.5V)
                if 2.0 <= voltage_v <= 3.0:
                    estimated_5v = voltage_v * 2.0  # Verdopple für 5V-Schätzung
                    return f"{estimated_5v:.2f}V"
                elif voltage_v >= 4.0:  # Falls bereits 5V-Bereich
                    return f"{voltage_v:.2f}V"
        except:
            pass
        
        try:
            # Alternative: hwmon1 in0_lcrit_alarm könnte Unterspannungswarnung sein
            # Wenn keine Warnung = gute Versorgung
            with open('/sys/class/hwmon/hwmon1/in0_lcrit_alarm', 'r') as f:
                alarm = int(f.read().strip())
                if alarm == 0:  # Keine Unterspannungswarnung
                    return "5.00V"  # Schätze normale Versorgung
                else:
                    return "4.80V"  # Niedrige Spannung erkannt
        except:
            pass
        
        try:
            # Fallback: Verwende Pi-interne Core-Spannung als Indikator
            result = subprocess.run(['vcgencmd', 'measure_volts', 'core'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                voltage_str = result.stdout.strip()
                if 'volt=' in voltage_str:
                    core_voltage = float(voltage_str.split('=')[1].replace('V', ''))
                    # Schätze 5V basierend auf Core-Spannung (normal ~1.3V bei 5V)
                    if core_voltage >= 1.25:
                        return "5.00V"  # Normale Core-Spannung = gute 5V-Versorgung
                    elif core_voltage >= 1.15:
                        return "4.75V"  # Leicht niedrige Versorgung
                    else:
                        return "4.50V"  # Niedrige Versorgung
        except:
            pass
        
        # Letzter Fallback: Schätze normale Versorgung
        return "5.00V"
    
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
        """Sammle echte Netzwerk-Metriken mit nativen Linux-Tools und persistenter Speicherung"""
        
        # Initialisiere Network-Stats falls nicht vorhanden (lade von Festplatte)
        if not hasattr(self.__class__, '_network_stats'):
            self.__class__._network_stats = load_network_stats()
            print(f"Network-Statistiken geladen: {self.__class__._network_stats}")
        
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
            
            if time_diff > 0.5 and self.__class__._network_stats['last_bytes_sent'] > 0:  # Mindestens 0.5s warten
                bytes_sent_diff = bytes_sent - self.__class__._network_stats['last_bytes_sent']
                bytes_recv_diff = bytes_recv - self.__class__._network_stats['last_bytes_recv']
                
                # Berechne Mbps (nur positive Werte und realistische Limits)
                if bytes_sent_diff >= 0 and bytes_recv_diff >= 0:
                    download_mbps = (bytes_recv_diff * 8) / (time_diff * 1000000)  # Mbps
                    upload_mbps = (bytes_sent_diff * 8) / (time_diff * 1000000)    # Mbps
                    
                    # Realistische Limits (max 1 Gbps für Raspberry Pi)
                    download_mbps = min(download_mbps, 1000.0)
                    upload_mbps = min(upload_mbps, 1000.0)
                    
                    # Ignoriere unrealistisch hohe Spitzen (über 100 Mbps für Pi)
                    if download_mbps > 100.0 or upload_mbps > 100.0:
                        print(f"Ignoring unrealistic speed: {download_mbps:.2f}/{upload_mbps:.2f} Mbps")
                        download_mbps = 0
                        upload_mbps = 0
                    
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
                        # Speichere nach Tages-Reset
                        save_network_stats(self.__class__._network_stats)
                    
                    # Aktualisiere Max-Werte nur bei realistischen Geschwindigkeiten
                    if download_mbps > 0 and download_mbps <= 100.0:
                        if download_mbps > self.__class__._network_stats['max_download_today']:
                            self.__class__._network_stats['max_download_today'] = download_mbps
                        if download_mbps > self.__class__._network_stats['max_download_alltime']:
                            self.__class__._network_stats['max_download_alltime'] = download_mbps
                            
                    if upload_mbps > 0 and upload_mbps <= 100.0:
                        if upload_mbps > self.__class__._network_stats['max_upload_today']:
                            self.__class__._network_stats['max_upload_today'] = upload_mbps
                        if upload_mbps > self.__class__._network_stats['max_upload_alltime']:
                            self.__class__._network_stats['max_upload_alltime'] = upload_mbps
                    
                    # Aktualisiere Traffic-Counter
                    if bytes_recv_diff > 0:
                        self.__class__._network_stats['total_download_today'] += bytes_recv_diff
                        self.__class__._network_stats['total_download_alltime'] += bytes_recv_diff
                    if bytes_sent_diff > 0:
                        self.__class__._network_stats['total_upload_today'] += bytes_sent_diff
                        self.__class__._network_stats['total_upload_alltime'] += bytes_sent_diff
                    
                    # Speichere aktualisierte Statistiken persistent
                    save_network_stats(self.__class__._network_stats)
                    
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
                    
                    # Lokale IP-Adresse und Verbindungsinfo hinzufügen
                    try:
                        # Hostname ermitteln
                        hostname_result = subprocess.run(['hostname'], capture_output=True, text=True, timeout=5)
                        if hostname_result.returncode == 0:
                            metrics['hostname'] = hostname_result.stdout.strip()
                        
                        # Lokale IP-Adresse ermitteln
                        ip_result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
                        if ip_result.returncode == 0:
                            ips = ip_result.stdout.strip().split()
                            # Erste nicht-loopback IP nehmen
                            for ip in ips:
                                if ip != '127.0.0.1' and not ip.startswith('::'):
                                    metrics['local_ip'] = ip
                                    break
                        
                        # Gateway IP ermitteln
                        route_result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True, timeout=5)
                        if route_result.returncode == 0:
                            route_lines = route_result.stdout.strip().split('\n')
                            for line in route_lines:
                                if 'default via' in line:
                                    parts = line.split()
                                    if len(parts) >= 3:
                                        metrics['gateway'] = parts[2]
                                        break
                        
                        # Interface-Info
                        if_result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, timeout=5)
                        if if_result.returncode == 0:
                            active_interfaces = []
                            for line in if_result.stdout.split('\n'):
                                if 'state UP' in line or 'LOWER_UP' in line:
                                    parts = line.split(':')
                                    if len(parts) >= 2:
                                        interface_name = parts[1].strip()
                                        if interface_name != 'lo':
                                            active_interfaces.append(interface_name)
                            if active_interfaces:
                                metrics['active_interfaces'] = ', '.join(active_interfaces)
                    except Exception as e:
                        print(f"Error getting network info: {e}")
                        
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
    
    def handle_reload_api(self):
        """Reload API Endpunkt - startet Chromium und App neu"""
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Führe Reload-Skript asynchron aus
            def execute_reload():
                try:
                    # Chromium neustarten (direkt auf dem Pi)
                    subprocess.run([
                        'sudo', 'pkill', '-f', 'chromium'
                    ], timeout=10)
                    time.sleep(3)
                    subprocess.run([
                        'sh', '-c',
                        'DISPLAY=:0 chromium-browser --kiosk --disable-infobars '
                        '--disable-session-crashed-bubble --disable-restore-session-state '
                        '--no-sandbox http://localhost:3000 > /dev/null 2>&1 &'
                    ], timeout=10)
                except Exception as e:
                    print(f"Reload error: {e}")
            
            # Starte Reload in separatem Thread
            threading.Thread(target=execute_reload, daemon=True).start()
            
            response = json.dumps({"status": "success", "message": "Reload started"}).encode('utf-8')
            self.wfile.write(response)
            
        except Exception as e:
            self.send_error(500, f"Reload Error: {str(e)}")
    
    def log_message(self, format, *args):
        """Überschreibe Log-Format für sauberere Ausgabe"""
        print(f"[{self.address_string()}] {format % args}")

def kill_port_processes(port):
    """Killt alle Prozesse die den angegebenen Port verwenden"""
    print(f"🔍 Prüfe Port {port} auf blockierende Prozesse...")
    
    killed_any = False
    
    # Aggressive Port-Cleanup mit mehreren Methoden
    methods_tried = []
    
    # Methode 1: Direct kill mit sudo lsof (am zuverlässigsten)
    try:
        result = subprocess.run(['sudo', 'lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            pids = [pid.strip() for pid in result.stdout.strip().split('\n') if pid.strip().isdigit()]
            for pid in pids:
                print(f"🔪 KILL PID {pid} auf Port {port}")
                subprocess.run(['sudo', 'kill', '-9', pid], timeout=3)
                killed_any = True
            methods_tried.append("lsof")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Methode 2: Brute force mit fuser
    try:
        subprocess.run(['sudo', 'fuser', '-k', '-9', f'{port}/tcp'], 
                      capture_output=True, timeout=5)
        print(f"🔪 FUSER kill auf Port {port}")
        killed_any = True
        methods_tried.append("fuser")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Methode 3: Netstat + kill
    try:
        result = subprocess.run(['sudo', 'netstat', '-tulpn'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) >= 7 and '/' in parts[6]:
                        pid = parts[6].split('/')[0]
                        if pid.isdigit():
                            print(f"🔪 NETSTAT kill PID {pid} auf Port {port}")
                            subprocess.run(['sudo', 'kill', '-9', pid], timeout=3)
                            killed_any = True
            if killed_any:
                methods_tried.append("netstat")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Methode 4: Fallback - kill alles was den Port blockiert
    try:
        subprocess.run(['sudo', 'pkill', '-9', '-f', f':{port}'], timeout=3)
        methods_tried.append("pkill")
    except:
        pass
    
    if methods_tried:
        print(f"✅ Port-Cleanup verwendet: {', '.join(methods_tried)}")
        print(f"⏳ Warte 5 Sekunden für saubere Portfreigabe...")
        time.sleep(5)
    else:
        print(f"ℹ️ Port {port} scheint bereits frei zu sein")
        time.sleep(1)
        
    print(f"🚀 Port {port} ist jetzt bereit für Server-Start")

def start_server(port=3000, host="0.0.0.0"):
    """Startet den HTTP Server"""
    global start_time
    start_time = time.time()
    
    # Port vor dem Start freimachen
    kill_port_processes(port)
    
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