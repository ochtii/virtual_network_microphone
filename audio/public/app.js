// PIMIC Audio Streaming - Client JavaScript
class PimicAudioStreaming {
    constructor() {
        this.socket = null;
        this.currentStream = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.analyser = null;
        this.dataArray = null;
        this.animationId = null;
        
        this.config = {
            webPort: 6969,
            defaultStreamPort: 420,
            maxBitrate: 320,
            minBitrate: 64,
            sampleRate: 44100,
            channels: 2
        };
        
        this.init();
    }
    
    init() {
        this.connectSocket();
        this.setupEventListeners();
        this.setupAudioMeter();
        this.loadNetworkInfo();
    }
    
    connectSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('[PIMIC] Connected to server');
            this.updateConnectionStatus('🟢 Verbunden', true);
        });
        
        this.socket.on('disconnect', () => {
            console.log('[PIMIC] Disconnected from server');
            this.updateConnectionStatus('🔴 Verbindung getrennt', false);
            this.stopStream();
        });
        
        this.socket.on('config', (config) => {
            this.config = { ...this.config, ...config };
            this.updateServerInfo();
            this.populatePortField();
        });
        
        this.socket.on('stream-started', (data) => {
            this.handleStreamStarted(data);
        });
        
        this.socket.on('stream-stopped', (data) => {
            this.handleStreamStopped(data);
        });
        
        this.socket.on('stream-list-updated', (data) => {
            this.updateStreamsList(data.streams);
        });
        
        this.socket.on('audio-level-update', (data) => {
            this.handleAudioLevelUpdate(data);
        });
        
        this.socket.on('error', (error) => {
            console.error('[PIMIC] Socket error:', error);
            this.showNotification('Verbindungsfehler: ' + error.message, 'error');
        });
    }
    
    setupEventListeners() {
        const startStopBtn = document.getElementById('startStopBtn');
        const refreshStreamsBtn = document.getElementById('refreshStreams');
        const meterEnabledCheckbox = document.getElementById('meterEnabled');
        
        startStopBtn.addEventListener('click', () => {
            if (this.currentStream) {
                this.stopStream();
            } else {
                this.startStream();
            }
        });
        
        refreshStreamsBtn.addEventListener('click', () => {
            this.loadStreamsList();
        });
        
        meterEnabledCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAudioMeter();
            } else {
                this.stopAudioMeter();
            }
        });
        
        // Auto-refresh streams every 10 seconds
        setInterval(() => {
            if (this.socket && this.socket.connected) {
                this.loadStreamsList();
            }
        }, 10000);
    }
    
    setupAudioMeter() {
        this.canvas = document.getElementById('audioMeterCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.dbValueElement = document.getElementById('dbValue');
        
        // Set canvas size
        this.canvas.width = 400;
        this.canvas.height = 100;
        
        // Start with empty meter
        this.drawAudioMeter(0, -Infinity);
    }
    
    async startStream() {
        try {
            const audioSource = document.getElementById('audioSource').value;
            const bitrate = parseInt(document.getElementById('bitrate').value);
            const streamPort = parseInt(document.getElementById('streamPort').value);
            const streamName = document.getElementById('streamName').value || 'Unbenannter Stream';
            
            // Request microphone access
            const constraints = this.getAudioConstraints(audioSource);
            this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // Setup Web Audio API
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;
            
            source.connect(this.analyser);
            
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            // Start audio level monitoring
            this.startAudioLevelMonitoring();
            
            // Send stream start request to server
            this.socket.emit('start-stream', {
                audioSource: audioSource,
                bitrate: bitrate,
                port: streamPort,
                name: streamName
            });
            
            this.showNotification('Stream wird gestartet...', 'info');
            
        } catch (error) {
            console.error('[PIMIC] Stream start error:', error);
            this.showNotification('Fehler beim Starten: ' + error.message, 'error');
            this.enableControls();
        }
    }
    
    stopStream() {
        if (this.currentStream) {
            this.socket.emit('stop-stream', this.currentStream.id);
        }
        
        this.cleanup();
        this.showNotification('Stream gestoppt', 'success');
    }
    
    cleanup() {
        // Stop audio level monitoring
        this.stopAudioLevelMonitoring();
        
        // Clean up Web Audio API
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        // Stop media stream
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        // Reset UI
        this.currentStream = null;
        this.updateStreamControls();
        this.enableControls();
        
        // Clear audio meter
        this.drawAudioMeter(0, -Infinity);
    }
    
    getAudioConstraints(audioSource) {
        switch (audioSource) {
            case 'microphone':
                return { 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: this.config.sampleRate
                    } 
                };
            case 'system':
                return { 
                    audio: {
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: false,
                        sampleRate: this.config.sampleRate
                    } 
                };
            case 'both':
                // This would require more complex setup - for now use microphone
                return { 
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: false,
                        autoGainControl: true,
                        sampleRate: this.config.sampleRate
                    } 
                };
            default:
                return { audio: true };
        }
    }
    
    startAudioLevelMonitoring() {
        if (!this.analyser) return;
        
        const monitor = () => {
            if (!this.analyser) return;
            
            this.analyser.getByteFrequencyData(this.dataArray);
            
            // Calculate RMS level
            let sum = 0;
            for (let i = 0; i < this.dataArray.length; i++) {
                sum += this.dataArray[i] * this.dataArray[i];
            }
            const rms = Math.sqrt(sum / this.dataArray.length);
            const level = rms / 255.0; // Normalize to 0-1
            
            // Convert to dB
            const db = level > 0 ? 20 * Math.log10(level) : -Infinity;
            
            // Update meter display
            this.drawAudioMeter(level, db);
            
            // Send level to server
            if (this.currentStream && this.socket) {
                this.socket.emit('audio-level', {
                    streamId: this.currentStream.id,
                    level: level,
                    db: db
                });
            }
            
            this.animationId = requestAnimationFrame(monitor);
        };
        
        monitor();
    }
    
    stopAudioLevelMonitoring() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
    
    drawAudioMeter(level, db) {
        if (!this.ctx) return;
        
        const canvas = this.canvas;
        const ctx = this.ctx;
        const width = canvas.width;
        const height = canvas.height;
        
        // Clear canvas
        ctx.fillStyle = '#2a2a2a';
        ctx.fillRect(0, 0, width, height);
        
        // Draw background grid
        ctx.strokeStyle = '#404040';
        ctx.lineWidth = 1;
        
        // Vertical lines (dB markers)
        const dbMarks = [-60, -50, -40, -30, -20, -10, -6, -3, 0];
        dbMarks.forEach(dbMark => {
            const x = this.dbToX(dbMark, width);
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
            
            // dB labels
            ctx.fillStyle = '#888';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(dbMark + 'dB', x, height - 5);
        });
        
        // Horizontal center line
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
        
        // Draw level bar
        if (level > 0) {
            const barWidth = this.dbToX(db, width);
            const barHeight = height * 0.6;
            const barY = (height - barHeight) / 2;
            
            // Color based on level
            let color = '#4caf50'; // Green
            if (db > -6) color = '#f44336';  // Red (danger)
            else if (db > -20) color = '#ff9800'; // Yellow (warning)
            
            // Draw gradient bar
            const gradient = ctx.createLinearGradient(0, 0, barWidth, 0);
            gradient.addColorStop(0, color);
            gradient.addColorStop(1, color + '80');
            
            ctx.fillStyle = gradient;
            ctx.fillRect(0, barY, barWidth, barHeight);
            
            // Draw peak hold
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(barWidth - 2, barY, 2, barHeight);
        }
        
        // Update dB display
        if (this.dbValueElement) {
            if (db === -Infinity) {
                this.dbValueElement.textContent = '-∞ dB';
                this.dbValueElement.style.color = '#666';
            } else {
                this.dbValueElement.textContent = db.toFixed(1) + ' dB';
                
                // Color based on level
                if (db > -6) this.dbValueElement.style.color = '#f44336';
                else if (db > -20) this.dbValueElement.style.color = '#ff9800';
                else this.dbValueElement.style.color = '#4caf50';
            }
        }
    }
    
    dbToX(db, width) {
        // Convert dB to X position (-60dB = 0, 0dB = width)
        if (db === -Infinity) return 0;
        const minDb = -60;
        const maxDb = 0;
        const normalized = Math.max(0, Math.min(1, (db - minDb) / (maxDb - minDb)));
        return normalized * width;
    }
    
    startAudioMeter() {
        const checkbox = document.getElementById('meterEnabled');
        if (checkbox.checked && !this.animationId) {
            this.startAudioLevelMonitoring();
        }
    }
    
    stopAudioMeter() {
        this.stopAudioLevelMonitoring();
        this.drawAudioMeter(0, -Infinity);
    }
    
    handleStreamStarted(data) {
        this.currentStream = {
            id: data.streamId,
            port: data.port,
            config: data.config,
            startTime: new Date()
        };
        
        this.updateStreamControls();
        this.disableControls();
        
        this.showNotification(`Stream gestartet auf Port ${data.port}`, 'success');
        this.loadStreamsList();
    }
    
    handleStreamStopped(data) {
        if (this.currentStream && this.currentStream.id === data.streamId) {
            this.cleanup();
        }
    }
    
    handleAudioLevelUpdate(data) {
        // Handle audio level updates from other clients
        // This could be used to show levels from other active streams
        console.log(`[PIMIC] Audio level from ${data.streamId}: ${data.db.toFixed(1)} dB`);
    }
    
    updateConnectionStatus(status, connected) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = 'status-indicator ' + (connected ? 'connected' : 'disconnected');
        }
        
        const startStopBtn = document.getElementById('startStopBtn');
        if (startStopBtn && !this.currentStream) {
            startStopBtn.disabled = !connected;
        }
    }
    
    updateServerInfo() {
        const serverInfoElement = document.getElementById('serverInfo');
        if (serverInfoElement && this.config) {
            serverInfoElement.textContent = `Port ${this.config.webPort} | Streams: ${this.config.defaultStreamPort}+`;
        }
    }
    
    populatePortField() {
        const portField = document.getElementById('streamPort');
        if (portField && this.config.defaultStreamPort) {
            portField.value = this.config.defaultStreamPort;
        }
    }
    
    updateStreamControls() {
        const startStopBtn = document.getElementById('startStopBtn');
        const streamInfo = document.getElementById('streamInfo');
        
        if (this.currentStream) {
            startStopBtn.innerHTML = '<span class="btn-icon">⏹️</span><span class="btn-text">Stream Stoppen</span>';
            startStopBtn.className = 'btn-primary streaming';
            
            streamInfo.style.display = 'block';
            document.getElementById('currentStreamId').textContent = this.currentStream.id;
            document.getElementById('currentStreamPort').textContent = this.currentStream.port;
            document.getElementById('currentStreamTime').textContent = this.currentStream.startTime.toLocaleTimeString();
        } else {
            startStopBtn.innerHTML = '<span class="btn-icon">▶️</span><span class="btn-text">Stream Starten</span>';
            startStopBtn.className = 'btn-primary';
            
            streamInfo.style.display = 'none';
        }
    }
    
    disableControls() {
        const controls = ['audioSource', 'bitrate', 'streamPort', 'streamName'];
        controls.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.disabled = true;
        });
    }
    
    enableControls() {
        const controls = ['audioSource', 'bitrate', 'streamPort', 'streamName'];
        controls.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.disabled = false;
        });
        
        const startStopBtn = document.getElementById('startStopBtn');
        if (startStopBtn && this.socket && this.socket.connected) {
            startStopBtn.disabled = false;
        }
    }
    
    loadStreamsList() {
        if (this.socket && this.socket.connected) {
            fetch('/api/streams')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        this.updateStreamsList(data.streams);
                    }
                })
                .catch(error => {
                    console.error('[PIMIC] Error loading streams:', error);
                });
        }
    }
    
    updateStreamsList(streams) {
        const streamsList = document.getElementById('streamsList');
        
        if (streams.length === 0) {
            streamsList.innerHTML = `
                <div class="no-streams">
                    <p>Keine aktiven Streams</p>
                    <small>Starte einen Stream um ihn hier zu sehen</small>
                </div>
            `;
            return;
        }
        
        streamsList.innerHTML = streams.map(stream => `
            <div class="stream-card fade-in">
                <div class="stream-status"></div>
                <h3>🎵 ${stream.id.split('_')[2] || 'Audio Stream'}</h3>
                <div class="stream-details">
                    <div><strong>IP:</strong> ${stream.clientIP}</div>
                    <div><strong>Port:</strong> ${stream.port}</div>
                    <div><strong>Bitrate:</strong> ${stream.bitrate} kbps</div>
                    <div><strong>Quelle:</strong> ${this.getAudioSourceLabel(stream.audioSource)}</div>
                    <div><strong>Gestartet:</strong> ${new Date(stream.startTime).toLocaleTimeString()}</div>
                </div>
            </div>
        `).join('');
    }
    
    loadNetworkInfo() {
        fetch('/api/network')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.updateNetworkInfo(data.network);
                }
            })
            .catch(error => {
                console.error('[PIMIC] Error loading network info:', error);
                document.getElementById('networkList').innerHTML = `
                    <div class="error">Fehler beim Laden der Netzwerk-Informationen</div>
                `;
            });
    }
    
    updateNetworkInfo(networkInterfaces) {
        const networkList = document.getElementById('networkList');
        
        if (networkInterfaces.length === 0) {
            networkList.innerHTML = '<div class="no-network">Keine Netzwerk-Interfaces gefunden</div>';
            return;
        }
        
        networkList.innerHTML = networkInterfaces.map(iface => `
            <div class="network-card">
                <h4>🌐 ${iface.interface}</h4>
                <div class="network-details-list">
                    <div><strong>IP-Adresse:</strong> ${iface.address}</div>
                    <div><strong>Netzmaske:</strong> ${iface.netmask}</div>
                    <div><strong>MAC-Adresse:</strong> ${iface.mac}</div>
                </div>
            </div>
        `).join('');
    }
    
    getAudioSourceLabel(audioSource) {
        switch (audioSource) {
            case 'microphone': return '🎤 Mikrofon';
            case 'system': return '🔊 System Audio';
            case 'both': return '🎵 Mikrofon + System';
            default: return audioSource;
        }
    }
    
    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '12px 20px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '600',
            zIndex: '9999',
            minWidth: '300px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)'
        });
        
        // Color based on type
        switch (type) {
            case 'success':
                notification.style.background = '#4caf50';
                break;
            case 'error':
                notification.style.background = '#f44336';
                break;
            case 'warning':
                notification.style.background = '#ff9800';
                break;
            default:
                notification.style.background = '#2196f3';
        }
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('[PIMIC] Initializing Audio Streaming Client...');
    window.pimicAudio = new PimicAudioStreaming();
});