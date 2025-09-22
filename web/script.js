// NetCast Audio Pro - JavaScript Logic
class NetCastAudioPro {
    constructor() {
        this.isStreaming = false;
        this.isEmergencyMode = false;
        this.voiceActivationEnabled = false;
        this.threshold = -30;
        this.currentLevel = -Infinity;
        this.audioContext = null;
        this.mediaStream = null;
        this.analyser = null;
        this.microphone = null;
        this.port = 42069; // ORIGINAL PORT - NICHT ÄNDERN!
        this.serverIP = '192.168.188.90'; // Raspberry Pi
        this.connectionCount = 0;
        this.startTime = null;
        this.uptimeInterval = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.websocket = null;
        this.reconnectInterval = null;
        this.isConnected = false;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.createLimiterBar();
        this.detectLocalIP();
        this.updateStreamUrl();
        this.startLevelMeter();
    }

    setupEventListeners() {
        // Stream Toggle
        document.getElementById('streamToggle').addEventListener('click', () => {
            this.toggleStream();
        });

        // Emergency Mode
        document.getElementById('emergencyMode').addEventListener('click', () => {
            this.toggleEmergencyMode();
        });

        // Voice Activation
        document.getElementById('voiceActivation').addEventListener('change', (e) => {
            this.voiceActivationEnabled = e.target.checked;
            this.updateThresholdControl();
        });

        // Threshold Slider
        document.getElementById('thresholdSlider').addEventListener('input', (e) => {
            this.threshold = parseInt(e.target.value);
            document.getElementById('thresholdValue').textContent = `${this.threshold} dB`;
            this.updateThresholdMarker();
        });

        // Port Input
        document.getElementById('portInput').addEventListener('change', (e) => {
            this.port = parseInt(e.target.value);
            this.updateStreamUrl();
        });

        // Copy URL
        document.getElementById('copyUrl').addEventListener('click', () => {
            this.copyStreamUrl();
        });

        // Share URL
        document.getElementById('shareUrl').addEventListener('click', () => {
            this.shareStreamUrl();
        });

        // Settings
        document.getElementById('bitrate').addEventListener('change', () => {
            this.updateStreamSettings();
        });

        document.getElementById('quality').addEventListener('change', () => {
            this.updateStreamSettings();
        });

        document.getElementById('autoEnhancement').addEventListener('change', () => {
            this.updateStreamSettings();
        });
    }

    createLimiterBar() {
        const limiterBar = document.getElementById('limiterBar');
        const segmentCount = 40;
        
        for (let i = 0; i < segmentCount; i++) {
            const segment = document.createElement('div');
            segment.className = 'led-segment';
            
            // Color coding for different levels
            if (i < segmentCount * 0.6) {
                segment.classList.add('green');
            } else if (i < segmentCount * 0.8) {
                segment.classList.add('yellow');
            } else if (i < segmentCount * 0.9) {
                segment.classList.add('orange');
            } else {
                segment.classList.add('red');
            }
            
            limiterBar.appendChild(segment);
        }
        
        this.updateThresholdMarker();
    }

    updateThresholdMarker() {
        const marker = document.getElementById('thresholdMarker');
        const percentage = (this.threshold + 60) / 60; // -60dB to 0dB range
        marker.style.left = `${percentage * 100}%`;
    }

    updateThresholdControl() {
        const control = document.getElementById('thresholdControl');
        control.classList.toggle('active', this.voiceActivationEnabled);
    }

    async detectLocalIP() {
        try {
            // Use WebRTC to detect local IP
            const pc = new RTCPeerConnection({
                iceServers: [{urls: 'stun:stun.l.google.com:19302'}]
            });
            
            pc.createDataChannel('');
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            
            return new Promise((resolve) => {
                pc.onicecandidate = (event) => {
                    if (event.candidate) {
                        const ip = event.candidate.candidate.split(' ')[4];
                        if (ip && ip.startsWith('192.168.') || ip.startsWith('10.') || ip.startsWith('172.')) {
                            this.localIP = ip;
                            document.getElementById('localIP').textContent = ip;
                            this.updateStreamUrl();
                            pc.close();
                            resolve(ip);
                        }
                    }
                };
            });
        } catch (error) {
            console.error('IP detection failed:', error);
            this.localIP = 'localhost';
            document.getElementById('localIP').textContent = 'localhost';
            this.updateStreamUrl();
        }
    }

    updateStreamUrl() {
        const url = `https://${this.serverIP}:${this.port}/stream`;
        document.getElementById('streamUrl').value = url;
    }

    async toggleStream() {
        if (!this.isStreaming) {
            await this.startStream();
        } else {
            this.stopStream();
        }
    }

    async startStream() {
        try {
            // Check if we're on HTTPS or localhost
            if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
                this.showToast('❌ HTTPS erforderlich für Mikrofon-Zugriff!');
                return;
            }

            // Request microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    sampleRate: 44100
                }
            });

            // Setup audio context and analyser
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 512;
            this.analyser.smoothingTimeConstant = 0.3;

            this.microphone = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.microphone.connect(this.analyser);

            // Setup MediaRecorder for streaming
            const options = this.getRecorderOptions();
            this.mediaRecorder = new MediaRecorder(this.mediaStream, options);
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && this.isConnected) {
                    this.sendAudioDataBinary(event.data);
                }
            };

            this.mediaRecorder.start(50); // 50ms chunks für niedrige Latenz

            // Start WebSocket connection
            this.connectWebSocket();
            this.startTime = Date.now();
            this.updateUI();
            this.startUptime();
            this.showToast('🚀 WebSocket Audio Stream gestartet!');

        } catch (error) {
            console.error('Stream start failed:', error);
            if (error.name === 'NotAllowedError') {
                this.showToast('❌ Mikrofon-Berechtigung verweigert!');
            } else if (error.name === 'NotFoundError') {
                this.showToast('❌ Kein Mikrofon gefunden!');
            } else {
                this.showToast('❌ Fehler beim Starten des Streams: ' + error.message);
            }
        }
    }

    stopStream() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
        }

        if (this.audioContext) {
            this.audioContext.close();
        }

        this.disconnectWebSocket();

        this.isStreaming = false;
        this.mediaStream = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.mediaRecorder = null;
        
        this.updateUI();
        this.stopUptime();
        this.showToast('⏹️ Stream gestoppt');
    }

    getRecorderOptions() {
        const bitrate = parseInt(document.getElementById('bitrate').value) * 1000;
        const quality = document.getElementById('quality').value;
        
        let options = {
            mimeType: 'audio/webm;codecs=opus',
            audioBitsPerSecond: bitrate
        };

        // Fallback for browsers that don't support webm
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'audio/mp4';
        }

        return options;
    }

    connectWebSocket() {
        // WebSocket connection to Pi Audio Server
        const wsUrl = `wss://${this.serverIP}:${this.port}`;
        console.log(`🚀 Connecting to WebSocket: ${wsUrl}`);
        
        try {
            this.websocket = new WebSocket(wsUrl);
            this.websocket.binaryType = 'arraybuffer'; // Binäre Daten
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket verbunden - bereit für Audio!');
                this.isConnected = true;
                this.showToast('🔌 WebSocket verbunden');
                
                // Ping-Pong für Verbindungstest
                this.sendPing();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'pong') {
                        console.log(`🏓 Ping: ${Math.round(Date.now() - data.timestamp)}ms`);
                    }
                } catch (e) {
                    // Binäre Daten ignorieren
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.isConnected = false;
                this.showToast('❌ WebSocket Fehler!');
            };
            
            this.websocket.onclose = (event) => {
                console.log('� WebSocket geschlossen:', event.code, event.reason);
                this.isConnected = false;
                this.connectionCount = 0;
                document.getElementById('connectionCount').textContent = '0';
                
                // Auto-Reconnect wenn Stream aktiv
                if (this.isStreaming) {
                    console.log('🔄 Reconnecting in 2 seconds...');
                    this.reconnectInterval = setTimeout(() => {
                        this.connectWebSocket();
                    }, 2000);
                }
            };
            
        } catch (error) {
            console.error('❌ WebSocket creation failed:', error);
            this.showToast('❌ WebSocket Server nicht erreichbar!');
            this.isConnected = false;
        }
    }

    disconnectWebSocket() {
        console.log('🛑 WebSocket disconnecting...');
        this.isConnected = false;
        
        if (this.reconnectInterval) {
            clearTimeout(this.reconnectInterval);
            this.reconnectInterval = null;
        }
        
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.connectionCount = 0;
        document.getElementById('connectionCount').textContent = '0';
    }

    sendPing() {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'ping',
                timestamp: Date.now()
            }));
        }
    }

    async sendAudioDataBinary(audioBlob) {
        if (!this.websocket || !this.isConnected || this.websocket.readyState !== WebSocket.OPEN) {
            return;
        }

        try {
            // Convert Blob to ArrayBuffer für binäre Übertragung
            const arrayBuffer = await audioBlob.arrayBuffer();
            
            // Direkt binäre Daten senden - MAXIMALE GESCHWINDIGKEIT!
            this.websocket.send(arrayBuffer);
            
            // Connection Count simulieren (könnte vom Server kommen)
            this.connectionCount = 1; // Mindestens wir sind verbunden
            document.getElementById('connectionCount').textContent = this.connectionCount;
            
        } catch (error) {
            console.error('❌ Audio send error:', error);
            this.isConnected = false;
        }
    }

    startLevelMeter() {
        const updateLevel = () => {
            if (this.analyser) {
                const dataArray = new Float32Array(this.analyser.frequencyBinCount);
                this.analyser.getFloatFrequencyData(dataArray);
                
                // Calculate RMS level
                let sum = 0;
                for (let i = 0; i < dataArray.length; i++) {
                    sum += Math.pow(10, dataArray[i] / 10);
                }
                const rms = Math.sqrt(sum / dataArray.length);
                this.currentLevel = 20 * Math.log10(rms);
                
                // Clamp to reasonable range
                this.currentLevel = Math.max(-60, Math.min(0, this.currentLevel));
            } else {
                this.currentLevel = -60; // Silent when not streaming
            }
            
            this.updateLevelDisplay();
            requestAnimationFrame(updateLevel);
        };
        
        updateLevel();
    }

    updateLevelDisplay() {
        const dbValue = document.getElementById('dbValue');
        const segments = document.querySelectorAll('.led-segment');
        
        // Update dB display
        if (this.currentLevel === -Infinity || this.currentLevel < -60) {
            dbValue.textContent = '-∞ dB';
        } else {
            dbValue.textContent = `${this.currentLevel.toFixed(1)} dB`;
        }
        
        // Update LED segments
        const percentage = (this.currentLevel + 60) / 60; // -60dB to 0dB range
        const activeSegments = Math.floor(percentage * segments.length);
        
        segments.forEach((segment, index) => {
            segment.classList.toggle('active', index < activeSegments);
        });
        
        // Check voice activation
        if (this.voiceActivationEnabled && this.isStreaming) {
            const isAboveThreshold = this.currentLevel > this.threshold;
            // In a real implementation, this would control whether audio is actually transmitted
        }
    }

    toggleEmergencyMode() {
        this.isEmergencyMode = !this.isEmergencyMode;
        
        if (this.isEmergencyMode) {
            // Emergency mode: maximize quality and disable voice activation
            document.getElementById('bitrate').value = '320';
            document.getElementById('quality').value = 'high';
            document.getElementById('voiceActivation').checked = false;
            this.voiceActivationEnabled = false;
            this.updateThresholdControl();
            this.showToast('🆘 Notfall-Modus aktiviert!');
        } else {
            this.showToast('✅ Notfall-Modus deaktiviert');
        }
        
        this.updateStreamSettings();
    }

    updateStreamSettings() {
        if (this.isStreaming && this.mediaRecorder) {
            // In a real implementation, you might need to restart the MediaRecorder
            // with new settings
            this.showToast('⚙️ Einstellungen aktualisiert');
        }
    }

    updateUI() {
        const streamButton = document.getElementById('streamToggle');
        const statusIndicator = document.getElementById('statusIndicator');
        const statusText = document.getElementById('statusText');
        const statusLight = statusIndicator.querySelector('.status-light');
        
        if (this.isStreaming) {
            streamButton.textContent = '⏹️ Stream Stoppen';
            streamButton.classList.add('active');
            statusText.textContent = 'Streaming';
            statusLight.classList.add('active');
        } else {
            streamButton.innerHTML = '<span class="button-icon">🎙️</span><span class="button-text">Stream Starten</span>';
            streamButton.classList.remove('active');
            statusText.textContent = 'Bereit';
            statusLight.classList.remove('active');
        }
    }

    startUptime() {
        this.uptimeInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const hours = Math.floor(elapsed / 3600000);
            const minutes = Math.floor((elapsed % 3600000) / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            
            document.getElementById('uptime').textContent = 
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);
    }

    stopUptime() {
        if (this.uptimeInterval) {
            clearInterval(this.uptimeInterval);
            this.uptimeInterval = null;
        }
        document.getElementById('uptime').textContent = '00:00:00';
    }

    async copyStreamUrl() {
        const url = document.getElementById('streamUrl').value;
        try {
            await navigator.clipboard.writeText(url);
            this.showToast('📋 URL kopiert!');
        } catch (error) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showToast('📋 URL kopiert!');
        }
    }

    async shareStreamUrl() {
        const url = document.getElementById('streamUrl').value;
        
        if (navigator.share) {
            try {
                await navigator.share({
                    title: 'NetCast Audio Pro Stream',
                    text: 'Höre meinen Audio-Stream:',
                    url: url
                });
            } catch (error) {
                console.log('Share failed:', error);
            }
        } else {
            // Fallback: copy to clipboard
            this.copyStreamUrl();
        }
    }

    showToast(message) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new NetCastAudioPro();
});