// Global variables
let updateInterval = null;
let currentView = 'system';
let views = ['system', 'network', 'settings', 'placeholder'];
let currentViewIndex = 0;

// Initialize navigation
document.addEventListener('DOMContentLoaded', function() {
    setupNavigation();
    showView('system');
    startLiveUpdates();
});

// Setup new navigation system
function setupNavigation() {
    // Menu toggle
    const menuToggle = document.getElementById('menuToggle');
    const menuPanel = document.getElementById('menuPanel');
    
    menuToggle.addEventListener('click', () => {
        menuPanel.classList.toggle('open');
    });
    
    // Menu items
    document.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', () => {
            const view = item.dataset.view;
            showView(view);
            menuPanel.classList.remove('open');
        });
    });
    
    // Navigation arrows
    document.getElementById('navLeft').addEventListener('click', () => {
        navigateToView('prev');
    });
    
    document.getElementById('navRight').addEventListener('click', () => {
        navigateToView('next');
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!menuToggle.contains(e.target) && !menuPanel.contains(e.target)) {
            menuPanel.classList.remove('open');
        }
    });
    
    // Settings handler
    document.addEventListener('click', (e) => {
        if (e.target && e.target.id === 'applySettings') {
            applySettings();
        }
    });
}

// Navigate between views with arrows
function navigateToView(direction) {
    if (direction === 'next') {
        currentViewIndex = (currentViewIndex + 1) % views.length;
    } else {
        currentViewIndex = (currentViewIndex - 1 + views.length) % views.length;
    }
    showView(views[currentViewIndex]);
}

// Show specific view
function showView(viewName) {
    // Update view index
    currentViewIndex = views.indexOf(viewName);
    
    // Hide all views
    document.querySelectorAll('.view-content').forEach(view => {
        view.classList.remove('active');
    });
    
    // Show target view
    const targetView = document.getElementById(viewName);
    if (targetView) {
        targetView.classList.add('active');
    }
    
    // Update current view indicator
    const viewNames = {
        'system': 'System Metrics',
        'network': 'Network Metrics', 
        'settings': 'Einstellungen',
        'placeholder': 'Platzhalter'
    };
    document.getElementById('currentView').textContent = viewNames[viewName];
    
    // Update menu active states
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.view === viewName) {
            item.classList.add('active');
        }
    });
    
    // Handle live updates
    stopLiveUpdates();
    currentView = viewName;
    if (viewName === 'system' || viewName === 'network') {
        startLiveUpdates();
    }
}

// Live Updates
function startLiveUpdates() {
    if (updateInterval) clearInterval(updateInterval);
    
    // Initial fetch
    if (currentView === 'system') {
        fetchSystemMetrics();
    } else if (currentView === 'network') {
        fetchNetworkMetrics();
    }
    
    // Set interval for updates
    updateInterval = setInterval(() => {
        if (currentView === 'system') {
            fetchSystemMetrics();
        } else if (currentView === 'network') {
            fetchNetworkMetrics();
        }
    }, 300); // 300ms updates
}

function stopLiveUpdates() {
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

// Color interpolation helper
function interpolateColor(color1, color2, factor) {
    const hex2rgb = (hex) => {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return [r, g, b];
    };
    
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

// Dynamic color determination for metric bars
function getMetricColor(value, type) {
    const val = parseFloat(value);
    
    switch(type) {
        case 'cpu':
        case 'ram':
        case 'disk':
            if (val <= 50) {
                const factor = val / 50;
                return interpolateColor('#28a745', '#ffc107', factor);
            } else {
                const factor = (val - 50) / 50;
                return interpolateColor('#ffc107', '#dc3545', factor);
            }
            
        case 'temp':
            if (val <= 40) {
                const factor = val / 40;
                return interpolateColor('#007bff', '#28a745', factor);
            } else if (val <= 60) {
                const factor = (val - 40) / 20;
                return interpolateColor('#28a745', '#ffc107', factor);
            } else if (val <= 80) {
                const factor = (val - 60) / 20;
                return interpolateColor('#ffc107', '#dc3545', factor);
            } else {
                return '#dc3545';
            }
            
        case 'network':
            if (val <= 1) {
                const factor = val / 1;
                return interpolateColor('#28a745', '#17a2b8', factor);
            } else if (val <= 10) {
                const factor = (val - 1) / 9;
                return interpolateColor('#17a2b8', '#6f42c1', factor);
            } else {
                return '#6f42c1';
            }
            
        default:
            return '#6c757d';
    }
}

// Set bar color and animation
function setBarColor(element, value, type) {
    if (element) {
        const color = getMetricColor(value, type);
        element.style.backgroundColor = color;
        element.style.boxShadow = `0 0 10px ${color}40`;
    }
}

// Fetch System Metrics
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
            
            // Set dynamic colors for all bars
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

// Fetch Network Metrics
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
                </div>
            `;
            
            // Set dynamic colors
            const downloadMbps = parseFloat(data.download_mbps) || 0;
            const uploadMbps = parseFloat(data.upload_mbps) || 0;
            setBarColor(document.getElementById('download-bar'), downloadMbps, 'network');
            setBarColor(document.getElementById('upload-bar'), uploadMbps, 'network');
        })
        .catch(err => {
            document.getElementById('network').innerHTML = '<div class="error">Fehler beim Laden der Netzwerk-Metriken</div>';
        });
}

// Settings handler
function applySettings() {
    const fontSize = document.getElementById('fontSize').value;
    const theme = document.getElementById('themeSelect').value;
    
    document.body.style.fontSize = fontSize + 'px';
    
    if (theme === 'dark') {
        document.body.classList.add('dark-theme');
        document.body.classList.remove('light-theme');
    } else {
        document.body.classList.add('light-theme');
        document.body.classList.remove('dark-theme');
    }
    
    // Save settings to localStorage
    localStorage.setItem('fontSize', fontSize);
    localStorage.setItem('theme', theme);
}

// Load saved settings
function loadSettings() {
    const savedFontSize = localStorage.getItem('fontSize');
    const savedTheme = localStorage.getItem('theme') || 'dark';
    
    if (savedFontSize) {
        document.getElementById('fontSize').value = savedFontSize;
        document.body.style.fontSize = savedFontSize + 'px';
    }
    
    document.getElementById('themeSelect').value = savedTheme;
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.add('light-theme');
    }
}

// Load settings on page load
document.addEventListener('DOMContentLoaded', loadSettings);