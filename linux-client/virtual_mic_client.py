#!/usr/bin/env python3
"""
Virtual Microphone Client - Linux/Raspberry Pi
Ein sadistisches Tool für experimentierfreudige Audio-Streaming-Enthusiasten 😈

Dieses Tool findet Audio-Streams im Netzwerk und erstellt virtuelle Mikrofone.
Jedes Mikrofon bekommt einen liebevollen Namen aus unserer sadistischen Liste.
"""

import sys
import os
import time
import threading
import socket
import subprocess
import requests
import json
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import signal

# Sadistische Mikrofon-Namen 😈
SADISTIC_MIC_NAMES = [
    'laber-lanze', 'brüllwürfel', 'goschn-ferrari', 'stimm-tornado',
    'schwafeltrichter', 'gschichtldrucker', 'gsichts-sirene', 'laber-heisl',
    'stimmband-techniker', 'ohren-vernichter'
]

@dataclass
class AudioStream:
    ip: str
    port: int
    id: str
    name: str
    active: bool = False
    process: Optional[subprocess.Popen] = None

class NetworkScanner:
    """Diabolischer Netzwerk-Scanner für Audio-Streams"""
    
    def __init__(self):
        self.found_streams: List[AudioStream] = []
        
    def get_local_network(self) -> str:
        """Ermittelt das lokale Netzwerk"""
        try:
            # Get default gateway
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Extract network from route
                parts = result.stdout.split()
                for i, part in enumerate(parts):
                    if part == 'src' and i + 1 < len(parts):
                        local_ip = parts[i + 1]
                        # Convert to network (assume /24)
                        ip_parts = local_ip.split('.')
                        return f"{'.'.join(ip_parts[:3])}.0/24"
        except Exception as e:
            print(f"❌ Fehler beim Ermitteln des Netzwerks: {e}")
        
        return "192.168.1.0/24"  # Fallback
    
    def check_audio_stream(self, ip: str, port: int) -> bool:
        """Überprüft ob auf IP:Port ein Audio-Stream läuft"""
        try:
            # Zuerst Socket-Test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result != 0:
                return False
                
            # Dann HTTP-Request für Audio-Stream
            response = requests.get(f"http://{ip}:{port}/audio", 
                                  timeout=3, stream=True)
            content_type = response.headers.get('content-type', '')
            
            # Check if it's an audio stream
            if 'audio' in content_type.lower() or response.status_code == 200:
                return True
                
        except Exception:
            pass
        
        return False
    
    def quick_scan(self) -> List[AudioStream]:
        """Schneller Scan - nur Port 42069 auf allen IPs"""
        print("🔍 Starte schnellen Scan (nur Port 42069)...")
        found = []
        network = self.get_local_network()
        
        # Extract base IP
        base_ip = network.split('.')[:-1]
        base = '.'.join(base_ip[:3])
        
        def check_ip(ip):
            if self.check_audio_stream(ip, 42069):
                stream_id = self.generate_stream_id()
                name = random.choice(SADISTIC_MIC_NAMES)
                stream = AudioStream(ip=ip, port=42069, id=stream_id, name=name)
                found.append(stream)
                print(f"🎯 Audio-Stream gefunden: {ip}:42069 -> '{name}'")
        
        threads = []
        for i in range(1, 255):
            ip = f"{base}.{i}"
            thread = threading.Thread(target=check_ip, args=(ip,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        return found
    
    def full_network_scan(self) -> List[AudioStream]:
        """Vollständiger Netzwerk-Scan - alle Ports"""
        print("⚠️  WARNUNG: Vollständiger Netzwerk-Scan kann sehr lange dauern!")
        confirm = input("Möchtest du trotzdem fortfahren? (j/N): ").lower()
        
        if confirm != 'j':
            return []
        
        print("🔍 Starte vollständigen Netzwerk-Scan...")
        found = []
        network = self.get_local_network()
        base_ip = network.split('.')[:-1]
        base = '.'.join(base_ip[:3])
        
        # Common ports to check
        ports_to_check = [42069, 8080, 8000, 3000, 5000, 9000]
        
        def check_ip_port(ip, port):
            if self.check_audio_stream(ip, port):
                stream_id = self.generate_stream_id()
                name = random.choice(SADISTIC_MIC_NAMES)
                stream = AudioStream(ip=ip, port=port, id=stream_id, name=name)
                found.append(stream)
                print(f"🎯 Audio-Stream gefunden: {ip}:{port} -> '{name}'")
        
        threads = []
        for i in range(1, 255):
            ip = f"{base}.{i}"
            for port in ports_to_check:
                thread = threading.Thread(target=check_ip_port, args=(ip, port))
                threads.append(thread)
                thread.start()
                
                # Limit concurrent threads
                if len(threads) >= 50:
                    for t in threads:
                        t.join()
                    threads = []
        
        # Wait for remaining threads
        for thread in threads:
            thread.join()
        
        return found
    
    def generate_stream_id(self) -> str:
        """Generiert eine eindeutige Stream-ID"""
        return f"stream_{random.randint(1000, 9999)}"

class VirtualMicrophoneManager:
    """Manager für virtuelle Mikrofone"""
    
    def __init__(self):
        self.active_mics: Dict[str, AudioStream] = {}
        self.max_mics = 10
        
    def create_virtual_mic(self, stream: AudioStream) -> bool:
        """Erstellt ein virtuelles Mikrofon für den Stream"""
        if len(self.active_mics) >= self.max_mics:
            print(f"❌ Maximum von {self.max_mics} Mikrofonen bereits erreicht!")
            return False
        
        try:
            print(f"🎤 Erstelle virtuelles Mikrofon: '{stream.name}' für {stream.ip}:{stream.port}")
            
            # Create PulseAudio null sink (virtual mic input)
            sink_name = f"virtual_mic_{stream.id}"
            cmd_sink = [
                'pactl', 'load-module', 'module-null-sink',
                f'sink_name={sink_name}',
                f'sink_properties=device.description="{stream.name}_sink"'
            ]
            
            result = subprocess.run(cmd_sink, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Fehler beim Erstellen des Sinks: {result.stderr}")
                return False
            
            # Create virtual source (microphone)
            source_name = f"virtual_source_{stream.id}"
            cmd_source = [
                'pactl', 'load-module', 'module-virtual-source',
                f'source_name={source_name}',
                f'master={sink_name}.monitor',
                f'source_properties=device.description="{stream.name}"'
            ]
            
            result = subprocess.run(cmd_source, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Fehler beim Erstellen der Source: {result.stderr}")
                return False
            
            # Start FFmpeg to receive stream and play to sink
            ffmpeg_cmd = [
                'ffmpeg', '-i', f'http://{stream.ip}:{stream.port}/audio',
                '-f', 'pulse', f'{sink_name}',
                '-loglevel', 'quiet'
            ]
            
            process = subprocess.Popen(ffmpeg_cmd)
            stream.process = process
            stream.active = True
            
            self.active_mics[stream.id] = stream
            print(f"✅ Virtuelles Mikrofon '{stream.name}' aktiv!")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Erstellen des virtuellen Mikrofons: {e}")
            return False
    
    def remove_virtual_mic(self, stream_id: str) -> bool:
        """Entfernt ein virtuelles Mikrofon"""
        if stream_id not in self.active_mics:
            return False
        
        stream = self.active_mics[stream_id]
        
        try:
            # Stop FFmpeg process
            if stream.process:
                stream.process.terminate()
                stream.process.wait(timeout=5)
            
            # Remove PulseAudio modules
            subprocess.run(['pactl', 'unload-module', f'module-virtual-source'], 
                         capture_output=True)
            subprocess.run(['pactl', 'unload-module', f'module-null-sink'], 
                         capture_output=True)
            
            del self.active_mics[stream_id]
            print(f"🗑️  Virtuelles Mikrofon '{stream.name}' entfernt")
            return True
            
        except Exception as e:
            print(f"❌ Fehler beim Entfernen des Mikrofons: {e}")
            return False
    
    def list_active_mics(self):
        """Zeigt alle aktiven virtuellen Mikrofone"""
        if not self.active_mics:
            print("📭 Keine aktiven virtuellen Mikrofone")
            return
        
        print("\n🎤 Aktive virtuelle Mikrofone:")
        print("-" * 50)
        for stream in self.active_mics.values():
            status = "🟢 AKTIV" if stream.active else "🔴 INAKTIV"
            print(f"  {stream.name} ({stream.ip}:{stream.port}) - {status}")
        print("-" * 50)

class SadisticAudioClient:
    """Hauptklasse für den sadistischen Audio-Client"""
    
    def __init__(self):
        self.scanner = NetworkScanner()
        self.mic_manager = VirtualMicrophoneManager()
        self.running = True
        
        # Signal handler für graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Behandelt Shutdown-Signale"""
        print("\n🛑 Shutdown wird eingeleitet...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Räumt alle virtuellen Mikrofone auf"""
        print("🧹 Räume auf...")
        for stream_id in list(self.mic_manager.active_mics.keys()):
            self.mic_manager.remove_virtual_mic(stream_id)
    
    def show_banner(self):
        """Zeigt das sadistische Banner"""
        banner = """
        ╔══════════════════════════════════════════════════════════════╗
        ║                    😈 SADISTIC AUDIO CLIENT 😈                ║
        ║                  Virtual Microphone Tool                     ║
        ║              Für experimentierfreudige Sadisten              ║
        ╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def show_menu(self):
        """Zeigt das Hauptmenü"""
        print("\n🎛️  HAUPTMENÜ")
        print("=" * 40)
        print("1. 🔍 Schnelle Suche (Port 42069)")
        print("2. 🕵️  Vollständiger Netzwerk-Scan")
        print("3. 🎯 Manuelle Verbindung (IP:Port)")
        print("4. 🎤 Aktive Mikrofone anzeigen")
        print("5. 🗑️  Mikrofon entfernen")
        print("6. 🚪 Beenden")
        print("=" * 40)
    
    def manual_connection(self):
        """Manuelle Verbindung zu einem Stream"""
        print("\n🎯 Manuelle Verbindung")
        print("-" * 30)
        
        try:
            ip_port = input("IP:Port eingeben (z.B. 192.168.1.100:42069): ").strip()
            
            if ':' not in ip_port:
                print("❌ Ungültiges Format! Verwende IP:Port")
                return
            
            ip, port_str = ip_port.split(':', 1)
            port = int(port_str)
            
            print(f"🔍 Überprüfe {ip}:{port}...")
            
            if self.scanner.check_audio_stream(ip, port):
                stream_id = self.scanner.generate_stream_id()
                name = random.choice(SADISTIC_MIC_NAMES)
                stream = AudioStream(ip=ip, port=port, id=stream_id, name=name)
                
                if self.mic_manager.create_virtual_mic(stream):
                    print(f"✅ Erfolgreich verbunden mit '{name}'!")
                else:
                    print("❌ Fehler beim Erstellen des virtuellen Mikrofons")
            else:
                print("❌ Kein Audio-Stream unter dieser Adresse gefunden")
                
        except ValueError:
            print("❌ Ungültiger Port!")
        except Exception as e:
            print(f"❌ Fehler: {e}")
    
    def remove_microphone(self):
        """Entfernt ein virtuelles Mikrofon"""
        if not self.mic_manager.active_mics:
            print("📭 Keine aktiven Mikrofone zum Entfernen")
            return
        
        print("\n🗑️  Mikrofon entfernen")
        print("-" * 30)
        
        # Show active mics
        mics = list(self.mic_manager.active_mics.values())
        for i, stream in enumerate(mics, 1):
            print(f"{i}. {stream.name} ({stream.ip}:{stream.port})")
        
        try:
            choice = int(input("Welches Mikrofon entfernen? (Nummer): ")) - 1
            
            if 0 <= choice < len(mics):
                stream = mics[choice]
                if self.mic_manager.remove_virtual_mic(stream.id):
                    print(f"✅ '{stream.name}' erfolgreich entfernt")
                else:
                    print(f"❌ Fehler beim Entfernen von '{stream.name}'")
            else:
                print("❌ Ungültige Auswahl")
                
        except ValueError:
            print("❌ Ungültige Eingabe")
    
    def auto_discover_and_connect(self, full_scan: bool = False):
        """Automatische Erkennung und Verbindung zu Streams"""
        if full_scan:
            streams = self.scanner.full_network_scan()
        else:
            streams = self.scanner.quick_scan()
        
        if not streams:
            print("📭 Keine Audio-Streams gefunden")
            return
        
        print(f"\n🎯 {len(streams)} Audio-Stream(s) gefunden:")
        print("-" * 40)
        
        for i, stream in enumerate(streams, 1):
            print(f"{i}. {stream.ip}:{stream.port} -> '{stream.name}'")
        
        print(f"{len(streams) + 1}. Alle verbinden")
        print("0. Zurück zum Menü")
        
        try:
            choice = int(input("Auswahl: "))
            
            if choice == 0:
                return
            elif choice == len(streams) + 1:
                # Connect to all
                for stream in streams:
                    self.mic_manager.create_virtual_mic(stream)
                    time.sleep(0.5)  # Short delay between connections
            elif 1 <= choice <= len(streams):
                # Connect to selected stream
                stream = streams[choice - 1]
                self.mic_manager.create_virtual_mic(stream)
            else:
                print("❌ Ungültige Auswahl")
                
        except ValueError:
            print("❌ Ungültige Eingabe")
    
    def run(self):
        """Hauptschleife des Clients"""
        self.show_banner()
        
        # Check dependencies
        if not self.check_dependencies():
            return
        
        print("🚀 Client gestartet! Bereit für sadistische Audio-Experimente...")
        
        while self.running:
            try:
                self.show_menu()
                choice = input("Auswahl: ").strip()
                
                if choice == '1':
                    self.auto_discover_and_connect(full_scan=False)
                elif choice == '2':
                    self.auto_discover_and_connect(full_scan=True)
                elif choice == '3':
                    self.manual_connection()
                elif choice == '4':
                    self.mic_manager.list_active_mics()
                elif choice == '5':
                    self.remove_microphone()
                elif choice == '6':
                    print("👋 Auf Wiedersehen, sadistischer Audio-Enthusiast!")
                    break
                else:
                    print("❌ Ungültige Auswahl")
                
                if choice != '6':
                    input("\nDrücke Enter um fortzufahren...")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Unerwarteter Fehler: {e}")
        
        self.cleanup()
    
    def check_dependencies(self) -> bool:
        """Überprüft ob alle benötigten Tools installiert sind"""
        required_tools = ['pactl', 'ffmpeg']
        missing_tools = []
        
        for tool in required_tools:
            try:
                subprocess.run([tool, '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_tools.append(tool)
        
        if missing_tools:
            print("❌ Fehlende Abhängigkeiten:")
            for tool in missing_tools:
                print(f"   - {tool}")
            print("\nInstallation (Debian/Ubuntu):")
            print("   sudo apt update")
            print("   sudo apt install pulseaudio-utils ffmpeg")
            return False
        
        return True

def main():
    """Hauptfunktion"""
    client = SadisticAudioClient()
    client.run()

if __name__ == "__main__":
    main()