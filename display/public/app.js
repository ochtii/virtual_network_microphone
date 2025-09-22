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
                                <div class="metric-bar-fill cpu" style="width: ${parseFloat(data.cpu)}%"></div>
                            </div>
                            <span class="metric-value">${data.cpu}</span>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <span class="metric-label">RAM Auslastung:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill ram" style="width: ${parseFloat(data.ram)}%"></div>
                            </div>
                            <span class="metric-value">${data.ram}</span>
                        </div>
                    </div>
                    
                    ${data.cpu_temp ? `
                    <div class="metric-item">
                        <span class="metric-label">CPU Temperatur:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill temp" style="width: ${Math.min(parseFloat(data.cpu_temp), 100)}%"></div>
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
                                <div class="metric-bar-fill disk" style="width: ${parseFloat(data.disk_usage)}%"></div>
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
                    <h3>Netzwerk Metriken <span class="live-indicator">🔴 LIVE</span></h3>
                    <div class="last-update">Letzte Aktualisierung: ${timestamp}</div>
                    
                    <div class="metric-item">
                        <span class="metric-label">Download Speed:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill download" style="width: ${Math.min((parseFloat(data.download_mbps) || 0) * 10, 100)}%"></div>
                            </div>
                            <span class="metric-value">${data.download}</span>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <span class="metric-label">Upload Speed:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill upload" style="width: ${Math.min((parseFloat(data.upload_mbps) || 0) * 10, 100)}%"></div>
                            </div>
                            <span class="metric-value">${data.upload}</span>
                        </div>
                    </div>
                    
                    ${data.max_download_today || data.max_upload_today ? `
                    <div class="metric-section">
                        <h4>Heute Maximum:</h4>
                        <div class="metric-item small">
                            <span class="metric-label">Max Down:</span>
                            <span class="metric-value">${data.max_download_today || 'N/A'}</span>
                        </div>
                        <div class="metric-item small">
                            <span class="metric-label">Max Up:</span>
                            <span class="metric-value">${data.max_upload_today || 'N/A'}</span>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.max_download_alltime || data.max_upload_alltime ? `
                    <div class="metric-section">
                        <h4>All-Time Maximum:</h4>
                        <div class="metric-item small">
                            <span class="metric-label">Max Down:</span>
                            <span class="metric-value">${data.max_download_alltime || 'N/A'}</span>
                        </div>
                        <div class="metric-item small">
                            <span class="metric-label">Max Up:</span>
                            <span class="metric-value">${data.max_upload_alltime || 'N/A'}</span>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.total_download_today || data.total_upload_today ? `
                    <div class="metric-section">
                        <h4>Traffic Heute:</h4>
                        <div class="metric-item small">
                            <span class="metric-label">Download:</span>
                            <span class="metric-value">${data.total_download_today || 'N/A'}</span>
                        </div>
                        <div class="metric-item small">
                            <span class="metric-label">Upload:</span>
                            <span class="metric-value">${data.total_upload_today || 'N/A'}</span>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.total_download_alltime || data.total_upload_alltime ? `
                    <div class="metric-section">
                        <h4>Traffic Gesamt:</h4>
                        <div class="metric-item small">
                            <span class="metric-label">Download:</span>
                            <span class="metric-value">${data.total_download_alltime || 'N/A'}</span>
                        </div>
                        <div class="metric-item small">
                            <span class="metric-label">Upload:</span>
                            <span class="metric-value">${data.total_upload_alltime || 'N/A'}</span>
                        </div>
                    </div>
                    ` : ''}
                </div>
            `;
        })
        .catch(err => {
            document.getElementById('network').innerHTML = '<div class="error">Fehler beim Laden der Netzwerk-Metriken</div>';
        });
}

// Live Updates
let updateInterval = null;
let currentTab = 'system';

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
