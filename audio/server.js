const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const NetworkDiscovery = require('./network-discovery');

// PIMIC Audio Streaming Server
// Port 6969 für Web-Interface
// Konfigurierbare Stream-Ports (Standard 420)
class PimicAudioServer {
    constructor() {
        this.app = express();
        this.server = http.createServer(this.app);
        this.io = socketIo(this.server, {
            cors: {
                origin: "*",
                methods: ["GET", "POST"]
            }
        });
        
        this.config = {
            webPort: 6969,
            defaultStreamPort: 420,
            maxBitrate: 320, // kbps
            minBitrate: 64,  // kbps
            sampleRate: 44100,
            channels: 2
        };
        
        this.activeStreams = new Map(); // Store active client streams
        this.audioLevels = new Map();   // Store audio level data
        
        // Initialize network discovery
        this.networkDiscovery = new NetworkDiscovery({
            port: this.config.webPort,
            serviceName: 'pimic-audio-' + require('os').hostname()
        });
        
        this.setupMiddleware();
        this.setupRoutes();
        this.setupSocketHandlers();
        this.setupNetworkDiscovery();
    }
    
    setupNetworkDiscovery() {
        // Handle network discovery events
        this.networkDiscovery.on('serviceUp', (service) => {
            console.log(`[DISCOVERY] Service discovered: ${service.name} at ${service.host}:${service.port}`);
            
            // Broadcast to all connected clients
            this.io.emit('service-discovered', service);
        });
        
        this.networkDiscovery.on('serviceDown', (service) => {
            console.log(`[DISCOVERY] Service lost: ${service.name} at ${service.host}:${service.port}`);
            
            // Broadcast to all connected clients
            this.io.emit('service-lost', service);
        });
        
        this.networkDiscovery.on('streamAnnounced', (streamInfo) => {
            console.log(`[DISCOVERY] Stream announced: ${streamInfo.id}`);
        });
        
        this.networkDiscovery.on('streamRemoved', (streamId) => {
            console.log(`[DISCOVERY] Stream removed: ${streamId}`);
        });
        
        // Start discovery
        this.networkDiscovery.start();
        this.networkDiscovery.startCleanupTimer();
    }
    
    setupMiddleware() {
        this.app.use(cors());
        this.app.use(express.json());
        this.app.use(express.static(path.join(__dirname, 'public')));
        
        // Request logging
        this.app.use((req, res, next) => {
            console.log(`[${new Date().toISOString()}] ${req.method} ${req.url} - ${req.ip}`);
            next();
        });
    }
    
    setupRoutes() {
        // Main audio streaming interface
        this.app.get('/', (req, res) => {
            res.sendFile(path.join(__dirname, 'public', 'index.html'));
        });
        
        // API: Get current active streams
        this.app.get('/api/streams', (req, res) => {
            const streams = Array.from(this.activeStreams.values()).map(stream => ({
                id: stream.id,
                clientIP: stream.clientIP,
                port: stream.port,
                bitrate: stream.bitrate,
                audioSource: stream.audioSource,
                startTime: stream.startTime,
                isActive: stream.isActive
            }));
            
            res.json({
                success: true,
                streams: streams,
                totalStreams: streams.length
            });
        });
        
        // API: Get server configuration
        this.app.get('/api/config', (req, res) => {
            res.json({
                success: true,
                config: {
                    webPort: this.config.webPort,
                    defaultStreamPort: this.config.defaultStreamPort,
                    maxBitrate: this.config.maxBitrate,
                    minBitrate: this.config.minBitrate,
                    sampleRate: this.config.sampleRate,
                    channels: this.config.channels
                }
            });
        });
        
        // API: Get network discovery info
        this.app.get('/api/network', (req, res) => {
            const networkInfo = this.getNetworkInfo();
            res.json({
                success: true,
                network: networkInfo
            });
        });
        
        // Health check endpoint
        this.app.get('/health', (req, res) => {
            res.json({
                status: 'healthy',
                service: 'pimic-audio-streaming',
                uptime: process.uptime(),
                activeStreams: this.activeStreams.size,
                timestamp: new Date().toISOString()
            });
        });
    }
    
    setupSocketHandlers() {
        this.io.on('connection', (socket) => {
            const clientIP = socket.handshake.address || socket.conn.remoteAddress;
            console.log(`[AUDIO] Client connected: ${socket.id} from ${clientIP}`);
            
            // Send current configuration to client
            socket.emit('config', this.config);
            
            // Handle stream start request
            socket.on('start-stream', (data) => {
                this.handleStreamStart(socket, data);
            });
            
            // Handle stream stop request
            socket.on('stop-stream', (streamId) => {
                this.handleStreamStop(socket, streamId);
            });
            
            // Handle audio data chunks
            socket.on('audio-data', (data) => {
                this.handleAudioData(socket, data);
            });
            
            // Handle audio level updates
            socket.on('audio-level', (data) => {
                this.handleAudioLevel(socket, data);
            });
            
            // Handle configuration updates
            socket.on('update-config', (data) => {
                this.handleConfigUpdate(socket, data);
            });
            
            // Handle client disconnect
            socket.on('disconnect', () => {
                this.handleClientDisconnect(socket);
                console.log(`[AUDIO] Client disconnected: ${socket.id}`);
            });
        });
    }
    
    handleStreamStart(socket, data) {
        const clientIP = socket.handshake.address || socket.conn.remoteAddress;
        const streamId = this.generateStreamId();
        const streamPort = data.port || this.getNextAvailablePort();
        
        const streamConfig = {
            id: streamId,
            clientId: socket.id,
            clientIP: clientIP,
            port: streamPort,
            bitrate: this.validateBitrate(data.bitrate || 128),
            audioSource: data.audioSource || 'microphone',
            startTime: new Date().toISOString(),
            isActive: true,
            socket: socket
        };
        
        this.activeStreams.set(streamId, streamConfig);
        
        // Announce stream to network (mDNS would go here)
        this.announceStream(streamConfig);
        
        socket.emit('stream-started', {
            streamId: streamId,
            port: streamPort,
            config: streamConfig
        });
        
        // Broadcast to all clients about new stream
        this.io.emit('stream-list-updated', {
            streams: Array.from(this.activeStreams.values()).map(s => ({
                id: s.id,
                clientIP: s.clientIP,
                port: s.port,
                bitrate: s.bitrate,
                audioSource: s.audioSource,
                startTime: s.startTime
            }))
        });
        
        console.log(`[AUDIO] Stream started: ${streamId} on port ${streamPort} from ${clientIP}`);
    }
    
    handleStreamStop(socket, streamId) {
        const stream = this.activeStreams.get(streamId);
        if (stream && stream.clientId === socket.id) {
            stream.isActive = false;
            this.activeStreams.delete(streamId);
            
            // Remove stream from network discovery
            this.networkDiscovery.removeStream(streamId);
            
            socket.emit('stream-stopped', { streamId });
            
            // Update all clients
            this.io.emit('stream-list-updated', {
                streams: Array.from(this.activeStreams.values()).map(s => ({
                    id: s.id,
                    clientIP: s.clientIP,
                    port: s.port,
                    bitrate: s.bitrate,
                    audioSource: s.audioSource,
                    startTime: s.startTime
                }))
            });
            
            console.log(`[AUDIO] Stream stopped: ${streamId}`);
        }
    }
    
    handleAudioData(socket, data) {
        const { streamId, audioBuffer, sampleRate, channels } = data;
        const stream = this.activeStreams.get(streamId);
        
        if (stream && stream.clientId === socket.id) {
            // Process and broadcast audio data to network
            this.broadcastAudioData(streamId, audioBuffer, sampleRate, channels);
        }
    }
    
    handleAudioLevel(socket, data) {
        const { streamId, level, db } = data;
        const stream = this.activeStreams.get(streamId);
        
        if (stream && stream.clientId === socket.id) {
            this.audioLevels.set(streamId, {
                level: level,      // 0.0 - 1.0
                db: db,           // dB value
                timestamp: Date.now()
            });
            
            // Broadcast level to all clients for monitoring
            this.io.emit('audio-level-update', {
                streamId: streamId,
                level: level,
                db: db
            });
        }
    }
    
    handleConfigUpdate(socket, data) {
        // Validate and update configuration
        const updates = {};
        
        if (data.defaultStreamPort && data.defaultStreamPort >= 1024 && data.defaultStreamPort <= 65535) {
            this.config.defaultStreamPort = data.defaultStreamPort;
            updates.defaultStreamPort = data.defaultStreamPort;
        }
        
        if (data.maxBitrate && data.maxBitrate >= 64 && data.maxBitrate <= 320) {
            this.config.maxBitrate = data.maxBitrate;
            updates.maxBitrate = data.maxBitrate;
        }
        
        socket.emit('config-updated', updates);
        console.log(`[CONFIG] Updated configuration:`, updates);
    }
    
    handleClientDisconnect(socket) {
        // Clean up any streams from this client
        for (const [streamId, stream] of this.activeStreams.entries()) {
            if (stream.clientId === socket.id) {
                this.activeStreams.delete(streamId);
                console.log(`[CLEANUP] Removed stream ${streamId} from disconnected client`);
            }
        }
        
        // Update stream list for remaining clients
        this.io.emit('stream-list-updated', {
            streams: Array.from(this.activeStreams.values()).map(s => ({
                id: s.id,
                clientIP: s.clientIP,
                port: s.port,
                bitrate: s.bitrate,
                audioSource: s.audioSource,
                startTime: s.startTime
            }))
        });
    }
    
    generateStreamId() {
        return 'stream_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    getNextAvailablePort() {
        let port = this.config.defaultStreamPort;
        const usedPorts = new Set(Array.from(this.activeStreams.values()).map(s => s.port));
        
        while (usedPorts.has(port)) {
            port++;
            if (port > 65535) port = 1024; // Wrap around
        }
        
        return port;
    }
    
    validateBitrate(bitrate) {
        return Math.max(this.config.minBitrate, Math.min(this.config.maxBitrate, bitrate));
    }
    
    announceStream(streamConfig) {
        // Announce stream via network discovery
        this.networkDiscovery.announceStream(streamConfig);
        console.log(`[DISCOVERY] Stream ${streamConfig.id} announced to network`);
    }
    
    broadcastAudioData(streamId, audioBuffer, sampleRate, channels) {
        // Process and broadcast audio data to network listeners
        // This would involve WebRTC or direct UDP streaming
        console.log(`[STREAM] Broadcasting audio data for ${streamId} - ${audioBuffer.length} bytes`);
    }
    
    getNetworkInfo() {
        const os = require('os');
        const interfaces = os.networkInterfaces();
        const networkInfo = [];
        
        for (const [name, addresses] of Object.entries(interfaces)) {
            for (const addr of addresses) {
                if (addr.family === 'IPv4' && !addr.internal) {
                    networkInfo.push({
                        interface: name,
                        address: addr.address,
                        netmask: addr.netmask,
                        mac: addr.mac
                    });
                }
            }
        }
        
        return networkInfo;
    }
    
    start() {
        this.server.listen(this.config.webPort, '0.0.0.0', () => {
            console.log(`
🎵 PIMIC Audio Streaming Server Started 🎵
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Web Interface:  http://localhost:${this.config.webPort}
🎧 Stream Ports:   ${this.config.defaultStreamPort}+
🔊 Bitrate Range:  ${this.config.minBitrate}-${this.config.maxBitrate} kbps
🌐 Network:        All interfaces (0.0.0.0)
🔍 Discovery:      mDNS + UDP Broadcast
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            `);
        });
    }
    
    stop() {
        console.log('[SHUTDOWN] Stopping PIMIC Audio Server...');
        
        // Stop network discovery
        if (this.networkDiscovery) {
            this.networkDiscovery.stop();
            this.networkDiscovery.stopCleanupTimer();
        }
        
        // Close all active streams
        for (const [streamId, stream] of this.activeStreams.entries()) {
            if (stream.socket) {
                stream.socket.emit('server-shutdown');
            }
        }
        this.activeStreams.clear();
        
        // Close server
        if (this.server) {
            this.server.close();
        }
        
        console.log('[SHUTDOWN] PIMIC Audio Server stopped');
    }
}

// Start the server
if (require.main === module) {
    const server = new PimicAudioServer();
    server.start();
    
    // Graceful shutdown
    process.on('SIGINT', () => {
        console.log('\n[SHUTDOWN] Stopping PIMIC Audio Server...');
        server.stop();
        process.exit(0);
    });
    
    process.on('SIGTERM', () => {
        console.log('\n[SHUTDOWN] SIGTERM received - stopping server...');
        server.stop();
        process.exit(0);
    });
}

module.exports = PimicAudioServer;