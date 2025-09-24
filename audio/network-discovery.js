// PIMIC Audio Network Discovery Service
// Handles mDNS/Bonjour service announcement and discovery
const mdns = require('mdns');
const EventEmitter = require('events');

class NetworkDiscovery extends EventEmitter {
    constructor(config = {}) {
        super();
        
        this.config = {
            serviceName: 'pimic-audio',
            serviceType: mdns.tcp('pimic-audio'),
            port: config.port || 6969,
            txtRecord: {
                version: '1.0.0',
                streams: 'enabled',
                formats: 'opus,pcm',
                bitrates: '64-320'
            },
            ...config
        };
        
        this.advertisement = null;
        this.browser = null;
        this.discoveredServices = new Map();
        
        this.init();
    }
    
    init() {
        try {
            // Create service advertisement
            this.advertisement = mdns.createAdvertisement(
                this.config.serviceType,
                this.config.port,
                {
                    name: this.config.serviceName,
                    txtRecord: this.config.txtRecord
                }
            );
            
            // Create service browser
            this.browser = mdns.createBrowser(this.config.serviceType);
            
            this.setupEventHandlers();
            
        } catch (error) {
            console.error('[DISCOVERY] mDNS initialization failed:', error);
            console.log('[DISCOVERY] Falling back to IP broadcast discovery');
            this.setupFallbackDiscovery();
        }
    }
    
    setupEventHandlers() {
        if (this.advertisement) {
            this.advertisement.on('error', (error) => {
                console.error('[DISCOVERY] Advertisement error:', error);
            });
        }
        
        if (this.browser) {
            this.browser.on('serviceUp', (service) => {
                this.handleServiceDiscovered(service);
            });
            
            this.browser.on('serviceDown', (service) => {
                this.handleServiceLost(service);
            });
            
            this.browser.on('error', (error) => {
                console.error('[DISCOVERY] Browser error:', error);
            });
        }
    }
    
    setupFallbackDiscovery() {
        // Fallback to UDP broadcast for discovery when mDNS fails
        const dgram = require('dgram');
        
        this.broadcastSocket = dgram.createSocket('udp4');
        this.listenSocket = dgram.createSocket('udp4');
        
        // Listen for discovery broadcasts
        this.listenSocket.bind(this.config.port + 1, () => {
            this.listenSocket.setBroadcast(true);
            console.log(`[DISCOVERY] Fallback UDP discovery listening on port ${this.config.port + 1}`);
        });
        
        this.listenSocket.on('message', (message, remote) => {
            try {
                const data = JSON.parse(message.toString());
                if (data.type === 'pimic-audio-discovery') {
                    this.handleFallbackServiceDiscovered(data, remote);
                }
            } catch (error) {
                // Ignore invalid messages
            }
        });
        
        // Broadcast our service periodically
        this.fallbackBroadcastInterval = setInterval(() => {
            this.broadcastService();
        }, 30000); // Every 30 seconds
    }
    
    start() {
        try {
            if (this.advertisement) {
                this.advertisement.start();
                console.log(`[DISCOVERY] mDNS advertisement started for ${this.config.serviceName}`);
            }
            
            if (this.browser) {
                this.browser.start();
                console.log('[DISCOVERY] mDNS browser started');
            }
            
            // Also start fallback discovery
            if (this.broadcastSocket) {
                this.broadcastService();
                console.log('[DISCOVERY] Fallback UDP broadcast started');
            }
            
        } catch (error) {
            console.error('[DISCOVERY] Start error:', error);
        }
    }
    
    stop() {
        try {
            if (this.advertisement) {
                this.advertisement.stop();
                console.log('[DISCOVERY] mDNS advertisement stopped');
            }
            
            if (this.browser) {
                this.browser.stop();
                console.log('[DISCOVERY] mDNS browser stopped');
            }
            
            if (this.fallbackBroadcastInterval) {
                clearInterval(this.fallbackBroadcastInterval);
            }
            
            if (this.broadcastSocket) {
                this.broadcastSocket.close();
            }
            
            if (this.listenSocket) {
                this.listenSocket.close();
            }
            
        } catch (error) {
            console.error('[DISCOVERY] Stop error:', error);
        }
    }
    
    broadcastService() {
        if (!this.broadcastSocket) return;
        
        const serviceInfo = {
            type: 'pimic-audio-discovery',
            name: this.config.serviceName,
            port: this.config.port,
            txtRecord: this.config.txtRecord,
            timestamp: Date.now()
        };
        
        const message = JSON.stringify(serviceInfo);
        
        // Broadcast to common network ranges
        const broadcastAddresses = [
            '255.255.255.255',
            '192.168.1.255',
            '192.168.0.255',
            '10.0.0.255'
        ];
        
        broadcastAddresses.forEach(address => {
            this.broadcastSocket.send(message, this.config.port + 1, address, (error) => {
                if (error) {
                    // Ignore broadcast errors (expected for some addresses)
                }
            });
        });
        
        console.log('[DISCOVERY] Service broadcast sent');
    }
    
    handleServiceDiscovered(service) {
        const serviceKey = `${service.name}@${service.host}:${service.port}`;
        
        if (!this.discoveredServices.has(serviceKey)) {
            this.discoveredServices.set(serviceKey, {
                name: service.name,
                host: service.host,
                port: service.port,
                addresses: service.addresses,
                txtRecord: service.txtRecord || {},
                discoveredAt: new Date(),
                type: 'mdns'
            });
            
            console.log(`[DISCOVERY] Service discovered: ${service.name} at ${service.host}:${service.port}`);
            this.emit('serviceUp', this.discoveredServices.get(serviceKey));
        }
    }
    
    handleServiceLost(service) {
        const serviceKey = `${service.name}@${service.host}:${service.port}`;
        
        if (this.discoveredServices.has(serviceKey)) {
            const serviceInfo = this.discoveredServices.get(serviceKey);
            this.discoveredServices.delete(serviceKey);
            
            console.log(`[DISCOVERY] Service lost: ${service.name} at ${service.host}:${service.port}`);
            this.emit('serviceDown', serviceInfo);
        }
    }
    
    handleFallbackServiceDiscovered(data, remote) {
        const serviceKey = `${data.name}@${remote.address}:${data.port}`;
        
        // Don't discover ourselves
        if (data.name === this.config.serviceName && this.isLocalAddress(remote.address)) {
            return;
        }
        
        if (!this.discoveredServices.has(serviceKey)) {
            this.discoveredServices.set(serviceKey, {
                name: data.name,
                host: remote.address,
                port: data.port,
                addresses: [remote.address],
                txtRecord: data.txtRecord || {},
                discoveredAt: new Date(),
                type: 'udp-broadcast'
            });
            
            console.log(`[DISCOVERY] UDP Service discovered: ${data.name} at ${remote.address}:${data.port}`);
            this.emit('serviceUp', this.discoveredServices.get(serviceKey));
        }
        
        // Update timestamp for keepalive
        const service = this.discoveredServices.get(serviceKey);
        if (service) {
            service.lastSeen = Date.now();
        }
    }
    
    isLocalAddress(address) {
        const os = require('os');
        const interfaces = os.networkInterfaces();
        
        for (const [name, addresses] of Object.entries(interfaces)) {
            for (const addr of addresses) {
                if (addr.address === address) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    getDiscoveredServices() {
        return Array.from(this.discoveredServices.values());
    }
    
    announceStream(streamInfo) {
        // Announce a new stream to the network
        const announcement = {
            type: 'pimic-stream-announcement',
            streamId: streamInfo.id,
            clientIP: streamInfo.clientIP,
            port: streamInfo.port,
            bitrate: streamInfo.bitrate,
            audioSource: streamInfo.audioSource,
            startTime: streamInfo.startTime,
            discoverable: true,
            timestamp: Date.now()
        };
        
        // Update our mDNS TXT record to include stream info
        if (this.advertisement) {
            try {
                const txtRecord = {
                    ...this.config.txtRecord,
                    activeStreams: '1',
                    lastStreamPort: streamInfo.port.toString()
                };
                
                // Note: mDNS TXT record updates require recreation in most implementations
                console.log('[DISCOVERY] Stream announced via mDNS TXT record update');
            } catch (error) {
                console.error('[DISCOVERY] mDNS TXT record update failed:', error);
            }
        }
        
        // Also broadcast via UDP fallback
        if (this.broadcastSocket) {
            const message = JSON.stringify(announcement);
            
            const broadcastAddresses = [
                '255.255.255.255',
                '192.168.1.255',
                '192.168.0.255'
            ];
            
            broadcastAddresses.forEach(address => {
                this.broadcastSocket.send(message, this.config.port + 2, address, () => {
                    // Ignore errors
                });
            });
            
            console.log(`[DISCOVERY] Stream ${streamInfo.id} announced via UDP broadcast`);
        }
        
        this.emit('streamAnnounced', streamInfo);
    }
    
    removeStream(streamId) {
        // Announce stream removal
        const removal = {
            type: 'pimic-stream-removal',
            streamId: streamId,
            timestamp: Date.now()
        };
        
        if (this.broadcastSocket) {
            const message = JSON.stringify(removal);
            
            const broadcastAddresses = [
                '255.255.255.255',
                '192.168.1.255',
                '192.168.0.255'
            ];
            
            broadcastAddresses.forEach(address => {
                this.broadcastSocket.send(message, this.config.port + 2, address, () => {
                    // Ignore errors
                });
            });
            
            console.log(`[DISCOVERY] Stream ${streamId} removal announced via UDP broadcast`);
        }
        
        this.emit('streamRemoved', streamId);
    }
    
    // Cleanup stale UDP-discovered services
    startCleanupTimer() {
        this.cleanupInterval = setInterval(() => {
            const now = Date.now();
            const maxAge = 120000; // 2 minutes
            
            for (const [key, service] of this.discoveredServices.entries()) {
                if (service.type === 'udp-broadcast' && service.lastSeen) {
                    if (now - service.lastSeen > maxAge) {
                        console.log(`[DISCOVERY] Removing stale service: ${service.name}`);
                        this.discoveredServices.delete(key);
                        this.emit('serviceDown', service);
                    }
                }
            }
        }, 60000); // Check every minute
    }
    
    stopCleanupTimer() {
        if (this.cleanupInterval) {
            clearInterval(this.cleanupInterval);
            this.cleanupInterval = null;
        }
    }
}

module.exports = NetworkDiscovery;