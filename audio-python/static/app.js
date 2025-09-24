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
        
        // Client-side streaming
        this.localStreamServer = null;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        this.clientIP = null;
        this.streamPort = 9420;
        this.streamWebSocket = null;
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        this.setupAudioMeter();
        this.connectEventSource();
        await this.detectClientIP();
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
        
        // Stream URL Action Buttons
        document.getElementById('openStreamBtn').addEventListener('click', () => {
            this.openStreamUrl();
        });
        
        document.getElementById('copyStreamBtn').addEventListener('click', () => {
            this.copyStreamUrl();
        });
        
        document.getElementById('shareStreamBtn').addEventListener('click', () => {
            this.shareStreamUrl();
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
    
    async detectClientIP() {
        try {
            // Use RTCPeerConnection to detect client IP
            const pc = new RTCPeerConnection({
                iceServers: [{urls: 'stun:stun.l.google.com:19302'}]
            });
            
            pc.createDataChannel('');
            
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            
            return new Promise((resolve) => {
                pc.onicecandidate = (event) => {
                    if (event.candidate) {
                        const candidate = event.candidate.candidate;
                        const ipMatch = candidate.match(/([0-9]{1,3}\.){3}[0-9]{1,3}/);
                        if (ipMatch && !ipMatch[0].startsWith('169.254') && !ipMatch[0].startsWith('127.')) {
                            this.clientIP = ipMatch[0];
                            console.log('Detected client IP:', this.clientIP);
                            pc.close();
                            resolve(this.clientIP);
                        }
                    }
                };
                
                // Fallback: use window.location.hostname if available
                setTimeout(() => {
                    if (!this.clientIP) {
                        // Try to get IP from current connection
                        this.clientIP = window.location.hostname;
                        console.log('Using fallback IP from location:', this.clientIP);
                    }
                    pc.close();
                    resolve(this.clientIP);
                }, 2000);
            });
            
        } catch (error) {
            console.log('IP detection failed, using fallback');
            this.clientIP = window.location.hostname;
            return this.clientIP;
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
            
            // Start WebSocket connection to Pi for audio streaming
            await this.startAudioStreamToPi(streamPort, bitrate);
            
            // Register stream with Pi server (Pi will host the actual HTTP stream)
            const streamId = `client_stream_${Date.now()}_${this.clientIP?.replace(/\./g, '_') || 'unknown'}`;
            const piHost = window.location.hostname;
            const piPort = window.location.port || '6969';
            const protocol = window.location.protocol; // Use same protocol as current page
            const streamUrl = `${protocol}//${piHost}:${piPort}/client/${this.clientIP}/stream`;
            
            try {
                const response = await fetch('/api/stream/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        streamId: streamId,
                        clientIP: this.clientIP || window.location.hostname,
                        streamUrl: streamUrl,
                        audioSource: audioSource,
                        bitrate: bitrate,
                        port: streamPort,
                        name: `Client ${this.clientIP || window.location.hostname}`,
                        requiresProxy: true
                    })
                });
                
                const result = await response.json();
                console.log('Stream registration result:', result);
                if (result.streamUrl) {
                    streamUrl = result.streamUrl; // Use server-provided proxy URL
                }
            } catch (e) {
                console.log('Stream registration failed:', e.message);
            }
            
            this.currentStream = {
                id: streamId,
                port: streamPort,
                url: streamUrl,
                clientIP: this.clientIP || window.location.hostname
            };
            
            this.updateStreamControls();
            
            // Start audio monitoring
            this.startAudioMonitoring();
            
            console.log('Client stream started:', streamId, streamUrl);
            
        } catch (error) {
            console.error('Stream start error:', error);
            alert('Fehler beim Starten: ' + error.message);
            this.cleanup();
        }
    }
    
    async startAudioStreamToPi(port, bitrate) {
        try {
            // Create WebSocket connection to Pi for audio streaming
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/audio-stream`;
            
            console.log('Connecting to Pi WebSocket:', wsUrl);
            this.streamWebSocket = new WebSocket(wsUrl);
            
            this.streamWebSocket.onopen = () => {
                console.log('Audio stream WebSocket connected - State:', this.streamWebSocket.readyState);
                
                // Send stream configuration
                this.streamWebSocket.send(JSON.stringify({
                    type: 'stream-config',
                    clientIP: this.clientIP,
                    port: port,
                    bitrate: bitrate,
                    format: 'audio/webm;codecs=opus'
                }));
            };
            
            // Add connection state monitoring
            setTimeout(() => {
                console.log('WebSocket state after 1s:', this.streamWebSocket.readyState);
                if (this.streamWebSocket.readyState !== 1) {
                    console.error('WebSocket failed to connect within 1s, state:', this.streamWebSocket.readyState);
                }
            }, 1000);
            
            this.streamWebSocket.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            this.streamWebSocket.onclose = () => {
                console.log('Audio stream WebSocket closed');
            };
            
            // Setup MediaRecorder to send audio to Pi
            this.mediaRecorder = new MediaRecorder(this.mediaStream, {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: bitrate * 1000
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                console.log(`MediaRecorder data available: ${event.data.size} bytes, WebSocket state: ${this.streamWebSocket?.readyState}`);
                if (event.data.size > 0 && this.streamWebSocket?.readyState === WebSocket.OPEN) {
                    // Convert blob to array buffer and send to Pi
                    event.data.arrayBuffer().then(buffer => {
                        console.log(`Sending audio data to Pi: ${buffer.byteLength} bytes`);
                        this.streamWebSocket.send(buffer);
                    });
                } else {
                    console.warn(`Cannot send audio data: data size=${event.data.size}, WebSocket state=${this.streamWebSocket?.readyState}`);
                }
            };
            
            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
            };
            
            // Start recording in small chunks for live streaming
            this.mediaRecorder.start(100); // 100ms chunks
            
            console.log(`Audio stream to Pi started: ${bitrate}kbps, format: audio/webm`);
            console.log(`MediaRecorder state: ${this.mediaRecorder.state}, WebSocket state: ${this.streamWebSocket.readyState}`);
            
        } catch (error) {
            console.error('Failed to start audio stream to Pi:', error);
            throw error;
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
        
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.mediaRecorder = null;
        }
        
        if (this.streamWebSocket) {
            this.streamWebSocket.close();
            this.streamWebSocket = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        this.analyser = null;
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
        const settingsSection = document.querySelector('.controls');
        const streamUrlSection = document.getElementById('streamUrlSection');
        
        if (this.currentStream) {
            // Stream ist aktiv - zeige URL-Sektion, verstecke Settings
            btn.innerHTML = '<span>⏹️ Stream Stoppen</span>';
            btn.className = 'streaming';
            
            // Settings ausblenden
            settingsSection.style.display = 'none';
            
            // Stream URL Sektion anzeigen
            streamUrlSection.style.display = 'block';
            this.updateStreamUrlDisplay();
            
        } else {
            // Kein Stream - zeige Settings, verstecke URL-Sektion
            btn.innerHTML = '<span>▶️ Stream Starten</span>';
            btn.className = '';
            
            // Settings anzeigen
            settingsSection.style.display = 'grid';
            
            // Stream URL Sektion verstecken
            streamUrlSection.style.display = 'none';
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
    
    updateStreamUrlDisplay() {
        if (this.currentStream) {
            // Use Pi as proxy with client identifier in URL
            const streamUrl = this.currentStream.url || `http://${window.location.hostname}:${this.currentStream.port}/client/${this.currentStream.clientIP}/stream`;
            
            document.getElementById('streamUrl').value = streamUrl;
            document.getElementById('activeStreamId').textContent = this.currentStream.id;
            document.getElementById('activeStreamPort').textContent = this.currentStream.port;
        }
    }
    
    openStreamUrl() {
        if (this.currentStream) {
            const streamUrl = this.currentStream.url || `http://${window.location.hostname}:${this.currentStream.port}/client/${this.currentStream.clientIP}/stream`;
            window.open(streamUrl, '_blank');
        }
    }
    
    async copyStreamUrl() {
        if (this.currentStream) {
            const streamUrl = this.currentStream.url || `http://${window.location.hostname}:${this.currentStream.port}/client/${this.currentStream.clientIP}/stream`;
            try {
                await navigator.clipboard.writeText(streamUrl);
                
                // Visual feedback
                const btn = document.getElementById('copyStreamBtn');
                const originalText = btn.innerHTML;
                btn.innerHTML = '✅ Kopiert!';
                btn.style.background = 'linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%)';
                
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.background = '';
                }, 2000);
                
            } catch (error) {
                console.error('Copy failed:', error);
                alert('Kopieren fehlgeschlagen. URL: ' + streamUrl);
            }
        }
    }
    
    shareStreamUrl() {
        if (this.currentStream) {
            const streamUrl = this.currentStream.url || `http://${window.location.hostname}:${this.currentStream.port}/client/${this.currentStream.clientIP}/stream`;
            
            if (navigator.share) {
                // Native Web Share API
                navigator.share({
                    title: 'PIMIC Audio Stream',
                    text: 'Höre meinen Audio-Stream',
                    url: streamUrl
                }).catch(console.error);
            } else {
                // Fallback: Show share options
                const shareText = `Höre meinen Audio-Stream: ${streamUrl}`;
                
                // Create share modal
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0,0,0,0.5); display: flex; align-items: center;
                    justify-content: center; z-index: 1000;
                `;
                
                modal.innerHTML = `
                    <div style="background: white; padding: 30px; border-radius: 10px; max-width: 400px; text-align: center;">
                        <h3>🔗 Stream teilen</h3>
                        <p style="margin: 15px 0;">${shareText}</p>
                        <div style="display: flex; gap: 10px; justify-content: center; margin-top: 20px;">
                            <button onclick="window.open('https://wa.me/?text=${encodeURIComponent(shareText)}', '_blank')" 
                                    style="padding: 10px 15px; background: #25D366; color: white; border: none; border-radius: 5px;">
                                💬 WhatsApp
                            </button>
                            <button onclick="window.open('https://t.me/share/url?url=${encodeURIComponent(streamUrl)}&text=${encodeURIComponent('Höre meinen Audio-Stream')}', '_blank')" 
                                    style="padding: 10px 15px; background: #0088CC; color: white; border: none; border-radius: 5px;">
                                ✈️ Telegram
                            </button>
                            <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                                    style="padding: 10px 15px; background: #666; color: white; border: none; border-radius: 5px;">
                                Schließen
                            </button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
                modal.addEventListener('click', (e) => {
                    if (e.target === modal) modal.remove();
                });
            }
        }
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('🐍 PIMIC Audio Client (Pure Python) initializing...');
    console.log('✨ No external JavaScript dependencies required');
    window.pimicAudio = new PimicAudioClient();
});