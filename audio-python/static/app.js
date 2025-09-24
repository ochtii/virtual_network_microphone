// PIMIC Audio Streaming - Pure Python Version Client
class PimicAudioClient {
    constructor() {
        this.currentStream = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.analyser = null;
        this.animationId = null;
        this.canvas = null;
        this.ctx = null;
        this.eventSource = null;
        this.lastLevelSendTime = 0;
        this.levelSendInterval = 500; // 500ms = 2 requests per second max
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupAudioMeter();
        this.connectEventSource();
        this.loadData();
        this.updateConnectionStatus('🟢 Python Service Aktiv');
    }
    
    setupEventListeners() {
        const startStopBtn = document.getElementById('startStopBtn');
        startStopBtn.addEventListener('click', () => {
            if (this.currentStream) {
                this.stopStream();
            } else {
                this.startStream();
            }
        });
        
        // Refresh data periodically
        setInterval(() => this.loadData(), 5000);
    }
    
    setupAudioMeter() {
        this.canvas = document.getElementById('audioMeter');
        this.ctx = this.canvas.getContext('2d');
        this.drawEmptyMeter();
    }
    
    connectEventSource() {
        // Use Server-Sent Events instead of WebSocket for simplicity
        try {
            this.eventSource = new EventSource('/api/events');
            
            this.eventSource.onopen = () => {
                console.log('Event source connected');
            };
            
            this.eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleServerEvent(data);
                } catch (e) {
                    console.log('Non-JSON event received:', event.data);
                }
            };
            
            this.eventSource.onerror = () => {
                console.log('Event source error, reconnecting...');
                setTimeout(() => this.connectEventSource(), 3000);
            };
            
        } catch (error) {
            console.log('Event source not supported, using polling');
            setInterval(() => this.loadData(), 2000);
        }
    }
    
    handleServerEvent(data) {
        switch (data.type) {
            case 'config':
                this.handleConfig(data.config);
                break;
            case 'heartbeat':
                // Keep connection alive
                break;
        }
    }
    
    handleConfig(config) {
        document.getElementById('streamPort').value = config.default_stream_port;
        document.getElementById('serverInfo').textContent = 
            `Port ${config.web_port} | Streams: ${config.default_stream_port}+`;
    }
    
    async startStream() {
        try {
            // Check if running over HTTPS or in a secure context
            const isLocalNetwork = location.hostname === 'localhost' || 
                                   location.hostname === '127.0.0.1' ||
                                   location.hostname.startsWith('192.168.') ||
                                   location.hostname.startsWith('10.') ||
                                   location.hostname.startsWith('172.') ||
                                   location.hostname.endsWith('.local');
                                   
            const isSecureContext = location.protocol === 'https:' || isLocalNetwork;

            if (!isSecureContext) {
                throw new Error('HTTPS required: Modern browsers require HTTPS for microphone access. Please use HTTPS or access via localhost/local network.');
            }

            // Check if getUserMedia is available
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('getUserMedia not supported: Your browser does not support audio capture. Please use a modern browser with audio support.');
            }

            const audioSource = document.getElementById('audioSource').value;
            const bitrate = parseInt(document.getElementById('bitrate').value);
            const streamPort = parseInt(document.getElementById('streamPort').value);
            
            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 44100,
                    channelCount: 2
                }
            });
            
            // Setup Web Audio API
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            source.connect(this.analyser);
            
            // Start stream via HTTP API
            const response = await fetch('/api/stream/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    audioSource: audioSource,
                    bitrate: bitrate,
                    port: streamPort,
                    name: `Stream from ${location.hostname}`
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.currentStream = {
                    id: result.streamId,
                    port: result.port,
                    config: result.config
                };
                
                this.updateStreamControls();
                document.getElementById('currentStreamId').textContent = result.streamId;
                document.getElementById('currentStreamPort').textContent = result.port;
                document.getElementById('streamInfo').style.display = 'block';
                
                // Start audio monitoring
                this.startAudioMonitoring();
                
                console.log('Stream started:', result.streamId);
            } else {
                throw new Error(result.error || 'Stream start failed');
            }
            
        } catch (error) {
            console.error('Stream start error:', error);
            alert('Fehler beim Starten: ' + error.message);
            this.cleanup();
        }
    }
    
    async stopStream() {
        if (this.currentStream) {
            try {
                const response = await fetch('/api/stream/stop', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        streamId: this.currentStream.id
                    })
                });
                
                const result = await response.json();
                console.log('Stream stop result:', result);
                
            } catch (error) {
                console.error('Stream stop error:', error);
            }
        }
        
        this.cleanup();
    }
    
    cleanup() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        this.currentStream = null;
        this.updateStreamControls();
        this.drawEmptyMeter();
    }
    
    startAudioMonitoring() {
        if (!this.analyser) return;
        
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        
        const monitor = () => {
            if (!this.analyser) return;
            
            this.analyser.getByteFrequencyData(dataArray);
            
            // Calculate RMS level
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
                sum += dataArray[i] * dataArray[i];
            }
            const rms = Math.sqrt(sum / dataArray.length);
            const level = rms / 255.0;
            
            // Convert to dB
            const db = level > 0 ? 20 * Math.log10(level) : -Infinity;
            
            // Update meter
            this.drawAudioMeter(level, db);
            
            // Send level to server (throttled)
            if (this.currentStream) {
                const now = Date.now();
                if (now - this.lastLevelSendTime >= this.levelSendInterval) {
                    this.sendAudioLevel(level, db);
                    this.lastLevelSendTime = now;
                }
            }
            
            this.animationId = requestAnimationFrame(monitor);
        };
        
        monitor();
    }
    
    async sendAudioLevel(level, db) {
        try {
            await fetch('/api/audio/level', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    streamId: this.currentStream.id,
                    level: level,
                    db: db
                })
            });
        } catch (error) {
            console.debug('Audio level send error:', error);
        }
    }
    
    drawAudioMeter(level = 0, db = -Infinity) {
        const canvas = this.canvas;
        const ctx = this.ctx;
        const width = canvas.width;
        const height = canvas.height;
        
        // Clear canvas
        ctx.fillStyle = '#2d3748';
        ctx.fillRect(0, 0, width, height);
        
        // Draw background grid
        ctx.strokeStyle = '#4a5568';
        ctx.lineWidth = 1;
        
        // Draw dB markers
        const dbMarks = [-60, -40, -20, -6, 0];
        dbMarks.forEach(dbMark => {
            const x = this.dbToX(dbMark, width);
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, height);
            ctx.stroke();
            
            ctx.fillStyle = '#a0aec0';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(dbMark + 'dB', x, height - 5);
        });
        
        // Draw level bar
        if (level > 0) {
            const barWidth = this.dbToX(db, width);
            const barHeight = height * 0.6;
            const barY = (height - barHeight) / 2;
            
            // Color based on level (Python green theme)
            let color = '#4CAF50'; // Green
            if (db > -6) color = '#f56565';  // Red
            else if (db > -20) color = '#FF9800'; // Orange
            
            ctx.fillStyle = color;
            ctx.fillRect(0, barY, barWidth, barHeight);
            
            // Add glow effect
            ctx.shadowColor = color;
            ctx.shadowBlur = 10;
            ctx.fillRect(0, barY, barWidth, barHeight);
            ctx.shadowBlur = 0;
        }
        
        // Update dB display
        const dbDisplay = document.getElementById('dbValue');
        if (db === -Infinity) {
            dbDisplay.textContent = '-∞ dB';
            dbDisplay.style.color = '#a0aec0';
        } else {
            dbDisplay.textContent = db.toFixed(1) + ' dB';
            if (db > -6) dbDisplay.style.color = '#f56565';
            else if (db > -20) dbDisplay.style.color = '#FF9800';
            else dbDisplay.style.color = '#4CAF50';
        }
    }
    
    drawEmptyMeter() {
        this.drawAudioMeter(0, -Infinity);
    }
    
    dbToX(db, width) {
        if (db === -Infinity) return 0;
        const minDb = -60;
        const maxDb = 0;
        const normalized = Math.max(0, Math.min(1, (db - minDb) / (maxDb - minDb)));
        return normalized * width;
    }
    
    updateConnectionStatus(status) {
        document.getElementById('connectionStatus').textContent = status;
    }
    
    updateStreamControls() {
        const btn = document.getElementById('startStopBtn');
        if (this.currentStream) {
            btn.innerHTML = '<span>⏹️ Stream Stoppen</span>';
            btn.className = 'streaming';
        } else {
            btn.innerHTML = '<span>▶️ Stream Starten</span>';
            btn.className = '';
            document.getElementById('streamInfo').style.display = 'none';
        }
    }
    
    updateStreamsList(streams) {
        const container = document.getElementById('streamsList');
        
        if (streams.length === 0) {
            container.innerHTML = '<p>Keine aktiven Streams</p>';
            return;
        }
        
        container.innerHTML = streams.map(stream => `
            <div class="stream-card">
                <h3>🎵 ${stream.name || stream.id}</h3>
                <p><strong>IP:</strong> ${stream.client_ip}</p>
                <p><strong>Port:</strong> ${stream.port}</p>
                <p><strong>Bitrate:</strong> ${stream.bitrate} kbps</p>
                <p><strong>Quelle:</strong> ${this.getSourceLabel(stream.audio_source)}</p>
                <p><strong>Gestartet:</strong> ${new Date(stream.start_time).toLocaleTimeString()}</p>
                <p><strong>Python Service:</strong> ✅ Aktiv</p>
            </div>
        `).join('');
    }
    
    getSourceLabel(source) {
        switch (source) {
            case 'microphone': return '🎤 Mikrofon';
            case 'system': return '🔊 System';
            case 'both': return '🎵 Beide';
            default: return source;
        }
    }
    
    async loadData() {
        try {
            // Load streams
            const streamsResponse = await fetch('/api/streams');
            const streamsData = await streamsResponse.json();
            if (streamsData.success) {
                this.updateStreamsList(streamsData.streams);
            }
            
            // Load network info
            const networkResponse = await fetch('/api/network');
            const networkData = await networkResponse.json();
            if (networkData.success) {
                this.updateNetworkInfo(networkData.network);
            }
            
        } catch (error) {
            console.error('Data loading error:', error);
        }
    }
    
    updateNetworkInfo(networks) {
        const container = document.getElementById('networkInfo');
        
        if (networks.length === 0) {
            container.innerHTML = '<p>Keine Netzwerk-Informationen verfügbar</p>';
            return;
        }
        
        const hostname = window.location.hostname;
        
        container.innerHTML = networks.map(network => `
            <div class="network-card">
                <h4>🌐 ${network.interface}</h4>
                <p><strong>IP:</strong> ${network.address}</p>
                <p><strong>Familie:</strong> ${network.family}</p>
                <p><strong>Service URL:</strong> http://${network.address}:6969</p>
            </div>
        `).join('');
        
        // Add connection info
        container.innerHTML += `
            <div class="network-card" style="border: 2px solid #4CAF50;">
                <h4>🚀 Python Service</h4>
                <p><strong>Current URL:</strong> ${window.location.origin}</p>
                <p><strong>Status:</strong> ✅ Pure Python - No npm dependencies</p>
                <p><strong>Performance:</strong> ⚡ Lightweight & Pi-optimized</p>
            </div>
        `;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('🐍 PIMIC Audio Client (Pure Python) initializing...');
    console.log('✨ No external JavaScript dependencies required');
    window.pimicAudio = new PimicAudioClient();
});