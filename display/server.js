const express = require('express');
const path = require('path');

const app = express();
const port = 3000;

// statische Dateien
app.use(express.static(path.join(__dirname, 'public')));

// API-Beispiel: System Metrics
app.get('/api/system', (req, res) => {
    const metrics = {
        cpu: Math.floor(Math.random() * 100) + '%',
        ram: Math.floor(Math.random() * 100) + '%',
        uptime: process.uptime().toFixed(0) + 's'
    };
    res.json(metrics);
});

// API-Beispiel: Network Metrics
app.get('/api/network', (req, res) => {
    const metrics = {
        download: Math.floor(Math.random() * 100) + ' Mbps',
        upload: Math.floor(Math.random() * 100) + ' Mbps'
    };
    res.json(metrics);
});

app.listen(port, () => {
    console.log(`Display API running at http://localhost:${port}`);
});
