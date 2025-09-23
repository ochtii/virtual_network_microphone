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
    // Horizontal navigation items (jetzt direkt im Header)
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const view = item.dataset.view;
            showView(view);
        });
    });
    
    // Horizontal navigation arrows
    document.getElementById('navPrev').addEventListener('click', () => {
        navigateToView('prev');
    });
    
    document.getElementById('navNext').addEventListener('click', () => {
        navigateToView('next');
    });
    
    // Original side navigation arrows
    document.getElementById('navLeft').addEventListener('click', () => {
        navigateToView('prev');
    });
    
    document.getElementById('navRight').addEventListener('click', () => {
        navigateToView('next');
    });
    
    // Touch-friendly settings handlers
    setupTouchSettings();
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
    
    // Update horizontal navigation
    updateHorizontalNav();
    
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

// Update horizontal navigation display
function updateHorizontalNav() {
    const navItems = document.querySelectorAll('.nav-item');
    const currentIndex = currentViewIndex;
    
    navItems.forEach((item, index) => {
        item.classList.remove('current', 'adjacent', 'other');
        
        if (index === currentIndex) {
            item.classList.add('current');
        } else if (Math.abs(index - currentIndex) === 1) {
            item.classList.add('adjacent');
        } else {
            item.classList.add('other');
        }
    });
    
    // Update navigation arrow states
    const prevBtn = document.getElementById('navPrev');
    const nextBtn = document.getElementById('navNext');
    
    if (prevBtn) prevBtn.disabled = currentIndex === 0;
    if (nextBtn) nextBtn.disabled = currentIndex === views.length - 1;
}

// Setup touch-friendly settings
function setupTouchSettings() {
    let currentFontSize = 14;
    
    // Font size controls
    const minusBtn = document.getElementById('fontSizeMinus');
    const plusBtn = document.getElementById('fontSizePlus');
    
    if (minusBtn) {
        minusBtn.addEventListener('click', () => {
            if (currentFontSize > 10) {
                currentFontSize -= 1;
                updateFontSizeDisplay();
                applyFontSize();
            }
        });
    }
    
    if (plusBtn) {
        plusBtn.addEventListener('click', () => {
            if (currentFontSize < 35) {
                currentFontSize += 1;
                updateFontSizeDisplay();
                applyFontSize();
            }
        });
    }
    
    function updateFontSizeDisplay() {
        const display = document.getElementById('fontSizeDisplay');
        if (display) {
            display.textContent = currentFontSize + 'px';
        }
    }
    
    function applyFontSize() {
        // Wende Schriftgröße auf alle relevanten Elemente an
        document.body.style.fontSize = currentFontSize + 'px';
        
        // Zusätzlich für bessere Wirkung
        const elements = document.querySelectorAll('.metric-card, .metric-label, .metric-value, .nav-item, .menu-panel');
        elements.forEach(el => {
            el.style.fontSize = currentFontSize + 'px';
        });
    }
    
    // Theme toggle
    document.querySelectorAll('.theme-option').forEach(option => {
        option.addEventListener('click', () => {
            document.querySelectorAll('.theme-option').forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');
            
            // Entferne alle Theme-Klassen
            document.body.classList.remove('light-theme', 'dark-theme', 'weed-theme', 'acid-theme');
            
            const theme = option.dataset.theme;
            switch(theme) {
                case 'light':
                    document.body.classList.add('light-theme');
                    break;
                case 'dark':
                    document.body.classList.add('dark-theme');
                    break;
                case 'weed':
                    document.body.classList.add('weed-theme');
                    break;
                case 'acid':
                    document.body.classList.add('acid-theme');
                    break;
            }
        });
    });
    
    // Apply settings button
    const applyBtn = document.getElementById('applySettings');
    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            // Save to localStorage
            localStorage.setItem('fontSize', currentFontSize);
            const activeTheme = document.querySelector('.theme-option.active');
            if (activeTheme) {
                localStorage.setItem('theme', activeTheme.dataset.theme);
            }
            
            // Visual feedback
            const originalText = applyBtn.textContent;
            applyBtn.textContent = 'Gespeichert!';
            applyBtn.style.background = '#28a745';
            
            setTimeout(() => {
                applyBtn.textContent = originalText;
                applyBtn.style.background = '';
            }, 1500);
        });
    }
    
    // Reload button
    const reloadBtn = document.getElementById('reloadButton');
    if (reloadBtn) {
        reloadBtn.addEventListener('click', async () => {
            // Visual feedback
            const originalText = reloadBtn.textContent;
            reloadBtn.textContent = '⏳ Neustart läuft...';
            reloadBtn.disabled = true;
            
            try {
                const response = await fetch('/reload');
                if (response.ok) {
                    reloadBtn.textContent = '✅ Neustart erfolgreich!';
                    reloadBtn.style.background = '#28a745';
                    
                    // Reload page after short delay
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    throw new Error('Reload failed');
                }
            } catch (error) {
                reloadBtn.textContent = '❌ Fehler beim Neustart';
                reloadBtn.style.background = '#dc3545';
                
                setTimeout(() => {
                    reloadBtn.textContent = originalText;
                    reloadBtn.style.background = '';
                    reloadBtn.disabled = false;
                }, 3000);
            }
        });
    }
    
    // Load saved settings
    const savedFontSize = localStorage.getItem('fontSize');
    const savedTheme = localStorage.getItem('theme') || 'dark';
    
    if (savedFontSize) {
        currentFontSize = parseInt(savedFontSize);
        updateFontSizeDisplay();
        applyFontSize();
    }
    
    // Set theme
    document.querySelectorAll('.theme-option').forEach(opt => opt.classList.remove('active'));
    const themeOption = document.querySelector(`[data-theme="${savedTheme}"]`);
    if (themeOption) {
        themeOption.classList.add('active');
    }
    
    // Entferne alle Theme-Klassen und setze das gespeicherte Theme
    document.body.classList.remove('light-theme', 'dark-theme', 'weed-theme', 'acid-theme');
    switch(savedTheme) {
        case 'light':
            document.body.classList.add('light-theme');
            break;
        case 'dark':
            document.body.classList.add('dark-theme');
            break;
        case 'weed':
            document.body.classList.add('weed-theme');
            break;
        case 'acid':
            document.body.classList.add('acid-theme');
            break;
        default:
            document.body.classList.add('dark-theme');
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
        
        // Text in Balken mit kontrastierender Farbe
        const textElement = element.querySelector('.metric-bar-text');
        if (textElement) {
            // Bestimme Textfarbe basierend auf Hintergrundfarbe
            const rgb = hexToRgb(color);
            const brightness = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
            textElement.style.color = brightness > 128 ? '#000000' : '#ffffff';
        }
    }
}

// Helper-Funktion um Hex zu RGB zu konvertieren
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
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
                                <div class="metric-bar-fill cpu" id="cpu-bar" style="width: ${parseFloat(data.cpu)}%">
                                    <span class="metric-bar-text">${data.cpu}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <span class="metric-label">RAM Auslastung:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill ram" id="ram-bar" style="width: ${parseFloat(data.ram)}%">
                                    <span class="metric-bar-text">${data.ram}${data.ram_details ? ` (${data.ram_details})` : ''}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    ${data.cpu_temp ? `
                    <div class="metric-item">
                        <span class="metric-label">CPU Temperatur:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill temp" id="temp-bar" style="width: ${Math.min(parseFloat(data.cpu_temp), 100)}%">
                                    <span class="metric-bar-text">${data.cpu_temp}°C</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${data.disk_usage ? `
                    <div class="metric-item">
                        <span class="metric-label">Festplatte:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill disk" id="disk-bar" style="width: ${parseFloat(data.disk_usage)}%">
                                    <span class="metric-bar-text">${data.disk_usage}${data.disk_details ? ` (${data.disk_details})` : ''}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="metric-section compact">
                        <div class="metric-row">
                            <div class="metric-item compact">
                                <span class="metric-label">Uptime:</span>
                                <span class="metric-value uptime">${data.uptime_hours !== undefined ? data.uptime_hours + 'h ' + data.uptime_minutes + 'm' : data.uptime}</span>
                            </div>
                            <div class="metric-item compact">
                                <span class="metric-label">Services:</span>
                                <span class="metric-value online-check">${data.active_services || 0}</span>
                            </div>
                            <div class="metric-item compact">
                                <span class="metric-label">Geräte:</span>
                                <span class="metric-value online-check">${data.network_devices || 0}</span>
                            </div>
                        </div>
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
                                <div class="metric-bar-fill download" id="download-bar" style="width: ${Math.min((parseFloat(data.download_mbps) || 0) * 10, 100)}%">
                                    <span class="metric-bar-text">${data.download}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="metric-item">
                        <span class="metric-label">Upload:</span>
                        <div class="metric-bar-container">
                            <div class="metric-bar">
                                <div class="metric-bar-fill upload" id="upload-bar" style="width: ${Math.min((parseFloat(data.upload_mbps) || 0) * 10, 100)}%">
                                    <span class="metric-bar-text">${data.upload}</span>
                                </div>
                            </div>
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