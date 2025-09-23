// Global variables
let updateInterval = null;
let currentTab = 'system';

// Tabs
document.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        document.getElementById(btn.dataset.tab).classList.add('active');
        btn.classList.add('active');
        
        // Stop live updates when switching away from metrics tab
        if (btn.dataset.tab !== 'tab1') {
            stopLiveUpdates();
        } else {
            // Restart live updates for the active subtab
            const activeSubtab = document.querySelector('.subtab-button.active');
            if (activeSubtab) {
                currentTab = activeSubtab.dataset.subtab;
                if (currentTab === 'system' || currentTab === 'network') {
                    startLiveUpdates();
                }
            }
        }
    });
});

// Subtabs
document.querySelectorAll('.subtab-button').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.subtab-content').forEach(sc => sc.classList.remove('active'));
        document.querySelectorAll('.subtab-button').forEach(b => b.classList.remove('active'));
        document.getElementById(btn.dataset.subtab).classList.add('active');
        btn.classList.add('active');
        
        // Stop previous updates and start new ones
        stopLiveUpdates();
        currentTab = btn.dataset.subtab;
        if(btn.dataset.subtab === 'system' || btn.dataset.subtab === 'network') {
            startLiveUpdates();
        }
    });
});

// Default open
document.querySelector('.tab-button[data-tab="tab1"]').click();
document.querySelector('.subtab-button[data-subtab="system"]').click();

// Hilfsfunktion für Farb-Interpolation
function interpolateColor(color1, color2, factor) {
    // Konvertiere Hex zu RGB
    const hex2rgb = (hex) => {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return [r, g, b];
    };
    
    // Konvertiere RGB zu Hex
    const rgb2hex = (r, g, b) => {
        return "#" + ((1 << 24) + (Math.round(r) << 16) + (Math.round(g) << 8) + Math.round(b)).toString(16).slice(1);
    };
    
    const [r1, g1, b1] = hex2rgb(color1);
    const [r2, g2, b2] = hex2rgb(color2);
    
    const r = r1 + (r2 - r1) * factor;
    const g = g1 + (g2 - g1) * factor;
    const b = b1 + (b2 - b1) * factor;
    
    return rgb2hex(r, g, b);
}

// Dynamische Farbbestimmung für Metriken-Balken (fließend)
function getMetricColor(value, type) {
    const val = parseFloat(value);
    
    switch(type) {
        case 'cpu':
        case 'ram':
        case 'disk':
            // CPU/RAM/Disk: Fließender Übergang Grün -> Gelb -> Rot
            if (val <= 50) {
                // 0-50%: Grün -> Gelb
                const factor = val / 50;
                return interpolateColor('#28a745', '#ffc107', factor);
            } else {
                // 50-100%: Gelb -> Rot
                const factor = (val - 50) / 50;
                return interpolateColor('#ffc107', '#dc3545', factor);
            }
            
        case 'temp':
            // Temperatur: Fließender Übergang Blau -> Grün -> Gelb -> Rot
            if (val <= 40) {
                // 0-40°C: Blau -> Grün
                const factor = val / 40;
                return interpolateColor('#007bff', '#28a745', factor);
            } else if (val <= 60) {
                // 40-60°C: Grün -> Gelb
                const factor = (val - 40) / 20;
                return interpolateColor('#28a745', '#ffc107', factor);
            } else if (val <= 80) {
                // 60-80°C: Gelb -> Rot
                const factor = (val - 60) / 20;
                return interpolateColor('#ffc107', '#dc3545', factor);
            } else {
                // 80+°C: Rot bleiben
                return '#dc3545';
            }
            
        case 'network':
            // Netzwerk: Fließender Übergang Grün -> Cyan -> Lila
            if (val <= 1) {
                // 0-1 Mbps: Grün -> Cyan
                const factor = val / 1;
                return interpolateColor('#28a745', '#17a2b8', factor);
            } else if (val <= 10) {
                // 1-10 Mbps: Cyan -> Lila
                const factor = (val - 1) / 9;
                return interpolateColor('#17a2b8', '#6f42c1', factor);
            } else {
                // 10+ Mbps: Lila bleiben
                return '#6f42c1';
            }
            
        default:
            return '#6c757d'; // Grau als Fallback
    }
}

// Funktion zum Setzen der Balkenfarbe und Animation
function setBarColor(element, value, type) {
    if (element) {
        const color = getMetricColor(value, type);
        element.style.backgroundColor = color;
        element.style.boxShadow = `0 0 10px ${color}40`; // Leichter Glow-Effekt
    }
}

// Fetch Metrics
function fetchSystemMetrics() {
    const timestamp = new Date().toLocaleTimeString();
    fetch('/api/system')
        .then(r => r.json())
        .then(data => {
            document.getElementById('system').innerHTML = `
                <div class="metric-card">
                    <h3>System Metriken <span class="live-indicator">🔴 LIVE</span></h3>
                    <div class="last-update">Letzte Aktualisierung: ${timestamp}</div>
                    
                    <div class="metric-item">
                        <span class="metric-label">CPU Auslastung:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill cpu" id="cpu-bar" style="width: ${parseFloat(data.cpu)}%"></div>
                            </div>
                            <span class="metric-value">${data.cpu}</span>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <span class="metric-label">RAM Auslastung:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill ram" id="ram-bar" style="width: ${parseFloat(data.ram)}%"></div>
                            </div>
                            <span class="metric-value">${data.ram}</span>
                        </div>
                    </div>
                    
                    ${data.cpu_temp ? `
                    <div class="metric-item">
                        <span class="metric-label">CPU Temperatur:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill temp" id="temp-bar" style="width: ${Math.min(parseFloat(data.cpu_temp), 100)}%"></div>
                            </div>
                            <span class="metric-value">${data.cpu_temp}°C</span>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.disk_usage ? `
                    <div class="metric-item">
                        <span class="metric-label">Festplatte:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill disk" id="disk-bar" style="width: ${parseFloat(data.disk_usage)}%"></div>
                            </div>
                            <span class="metric-value">${data.disk_usage}</span>
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="metric-item">
                        <span class="metric-label">Uptime:</span>
                        <span class="metric-value uptime">${data.uptime}</span>
                    </div>
                </div>
            `;
            
            // Setze dynamische Farben für alle Balken
            setBarColor(document.getElementById('cpu-bar'), data.cpu, 'cpu');
            setBarColor(document.getElementById('ram-bar'), data.ram, 'ram');
            if (data.cpu_temp) {
                setBarColor(document.getElementById('temp-bar'), data.cpu_temp, 'temp');
            }
            if (data.disk_usage) {
                setBarColor(document.getElementById('disk-bar'), data.disk_usage, 'disk');
            }
        })
        .catch(err => {
            document.getElementById('system').innerHTML = '<div class="error">Fehler beim Laden der System-Metriken</div>';
        });
}
function fetchNetworkMetrics() {
    const timestamp = new Date().toLocaleTimeString();
    fetch('/api/network')
        .then(r => r.json())
        .then(data => {
            document.getElementById('network').innerHTML = `
                <div class="metric-card">
                    <h3>Netzwerk <span class="live-indicator">🔴 LIVE</span></h3>
                    <div class="last-update">Letzte Aktualisierung: ${timestamp}</div>
                    
                    <div class="metric-item">
                        <span class="metric-label">Download:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill download" id="download-bar" style="width: ${Math.min((parseFloat(data.download_mbps) || 0) * 10, 100)}%"></div>
                            </div>
                            <span class="metric-value">${data.download}</span>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <span class="metric-label">Upload:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill upload" id="upload-bar" style="width: ${Math.min((parseFloat(data.upload_mbps) || 0) * 10, 100)}%"></div>
                            </div>
                            <span class="metric-value">${data.upload}</span>
                        </div>
                    </div>
                    
                    ${data.max_download_today || data.max_upload_today ? `
                    <div class="metric-section compact">
                        <h4>Max Heute:</h4>
                        <div class="metric-row">
                            <div class="metric-item compact">
                                <span class="metric-label">Down:</span>
                                <span class="metric-value">${data.max_download_today || 'N/A'}</span>
                            </div>
                            <div class="metric-item compact">
                                <span class="metric-label">Up:</span>
                                <span class="metric-value">${data.max_upload_today || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.max_download_alltime || data.max_upload_alltime ? `
                    <div class="metric-section compact">
                        <h4>Max Gesamt:</h4>
                        <div class="metric-row">
                            <div class="metric-item compact">
                                <span class="metric-label">Down:</span>
                                <span class="metric-value">${data.max_download_alltime || 'N/A'}</span>
                            </div>
                            <div class="metric-item compact">
                                <span class="metric-label">Up:</span>
                                <span class="metric-value">${data.max_upload_alltime || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.total_download_today || data.total_upload_today ? `
                    <div class="metric-section compact">
                        <h4>Traffic Heute:</h4>
                        <div class="metric-row">
                            <div class="metric-item compact">
                                <span class="metric-label">Down:</span>
                                <span class="metric-value">${data.total_download_today || 'N/A'}</span>
                            </div>
                            <div class="metric-item compact">
                                <span class="metric-label">Up:</span>
                                <span class="metric-value">${data.total_upload_today || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.total_download_alltime || data.total_upload_alltime ? `
                    <div class="metric-section compact">
                        <h4>Traffic Gesamt:</h4>
                        <div class="metric-row">
                            <div class="metric-item compact">
                                <span class="metric-label">Down:</span>
                                <span class="metric-value">${data.total_download_alltime || 'N/A'}</span>
                            </div>
                            <div class="metric-item compact">
                                <span class="metric-label">Up:</span>
                                <span class="metric-value">${data.total_upload_alltime || 'N/A'}</span>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                </div>
            `;
            
            // Setze dynamische Farben für Netzwerk-Balken
            setBarColor(document.getElementById('download-bar'), data.download_mbps || 0, 'network');
            setBarColor(document.getElementById('upload-bar'), data.upload_mbps || 0, 'network');
        })
        .catch(err => {
            document.getElementById('network').innerHTML = '<div class="error">Fehler beim Laden der Netzwerk-Metriken</div>';
        });
}

// Live Updates
function startLiveUpdates() {
    // Stop any existing interval first
    stopLiveUpdates();
    
    // Update immediately
    if (currentTab === 'system') {
        fetchSystemMetrics();
    } else if (currentTab === 'network') {
        fetchNetworkMetrics();
    }
    
    // Then update every 300ms for smooth experience
    updateInterval = setInterval(() => {
        if (currentTab === 'system') {
            fetchSystemMetrics();
        } else if (currentTab === 'network') {
            fetchNetworkMetrics();
        }
    }, 300);
}

function stopLiveUpdates() {
    if (updateInterval !== null) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

// Settings
document.getElementById('applySettings').addEventListener('click', () => {
    document.body.style.fontSize = document.getElementById('fontSize').value + 'px';
    const theme = document.getElementById('themeSelect').value;
    document.body.style.background = theme === 'dark' ? '#111' : '#fff';
    document.body.style.color = theme === 'dark' ? '#eee' : '#000';
});
