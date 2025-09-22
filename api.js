const express = require('express');
const { exec } = require('child_process');
const app = express();
const PORT = 3000; // Port für das Dashboard/API

app.use(express.json());

// Helper-Funktion
function runScript(script, res) {
  exec(`bash scripts/${script}.sh`, (err, stdout, stderr) => {
    if (err) {
      console.error(err);
      return res.status(500).send(stderr || 'Fehler beim Ausführen');
    }
    res.send(stdout || 'OK');
  });
}

app.post('/display/start', (req, res) => runScript('start_display', res));
app.post('/display/stop', (req, res) => runScript('stop_display', res));
app.post('/display/restart', (req, res) => runScript('restart_display', res));

app.listen(PORT, () => {
  console.log(`Display API läuft auf http://localhost:${PORT}`);
});
