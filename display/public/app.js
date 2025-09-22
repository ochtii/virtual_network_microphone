// Tabs
document.querySelectorAll('.tab-button').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        document.querySelectorAll('.tab-button').forEach(b => b.classList.remove('active'));
        document.getElementById(btn.dataset.tab).classList.add('active');
        btn.classList.add('active');
    });
});

// Subtabs
document.querySelectorAll('.subtab-button').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.subtab-content').forEach(sc => sc.classList.remove('active'));
        document.querySelectorAll('.subtab-button').forEach(b => b.classList.remove('active'));
        document.getElementById(btn.dataset.subtab).classList.add('active');
        btn.classList.add('active');
        if(btn.dataset.subtab === 'system') fetchSystemMetrics();
        if(btn.dataset.subtab === 'network') fetchNetworkMetrics();
    });
});

// Default open
document.querySelector('.tab-button[data-tab="tab1"]').click();
document.querySelector('.subtab-button[data-subtab="system"]').click();

// Fetch Metrics
function fetchSystemMetrics() {
    fetch('/api/system')
        .then(r => r.json())
        .then(data => {
            document.getElementById('system').innerText = JSON.stringify(data, null, 2);
        });
}
function fetchNetworkMetrics() {
    fetch('/api/network')
        .then(r => r.json())
        .then(data => {
            document.getElementById('network').innerText = JSON.stringify(data, null, 2);
        });
}

// Settings
document.getElementById('applySettings').addEventListener('click', () => {
    document.body.style.fontSize = document.getElementById('fontSize').value + 'px';
    const theme = document.getElementById('themeSelect').value;
    document.body.style.background = theme === 'dark' ? '#111' : '#fff';
    document.body.style.color = theme === 'dark' ? '#eee' : '#000';
});
