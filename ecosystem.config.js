module.exports = {
  apps: [
    // ==============================================
    // 🌐 WEB SERVERS
    // ==============================================
    {
      name: 'netcast-web-interface',
      script: 'servers/https_server.py',
      interpreter: 'python3',
      cwd: '/home/ochtii/virtual_mic',
      env: {
        NODE_ENV: 'production',
        PORT: 8443
      },
      error_file: '/home/ochtii/virtual_mic/logs/web-error.log',
      out_file: '/home/ochtii/virtual_mic/logs/web-out.log',
      log_file: '/home/ochtii/virtual_mic/logs/web-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    },
    
    // ==============================================
    // 🎵 AUDIO SERVERS  
    // ==============================================
    {
      name: 'netcast-https-audio',
      script: 'servers/https_audio_server.py',
      interpreter: 'python3',
      cwd: '/home/ochtii/virtual_mic',
      env: {
        NODE_ENV: 'production',
        PORT: 42069
      },
      error_file: '/home/ochtii/virtual_mic/logs/https-audio-error.log',
      out_file: '/home/ochtii/virtual_mic/logs/https-audio-out.log',
      log_file: '/home/ochtii/virtual_mic/logs/https-audio-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    },
    {
      name: 'netcast-http-audio',
      script: 'servers/http_audio_server.py',
      interpreter: 'python3',
      cwd: '/home/ochtii/virtual_mic',
      env: {
        NODE_ENV: 'production',
        PORT: 8080
      },
      error_file: '/home/ochtii/virtual_mic/logs/http-audio-error.log',
      out_file: '/home/ochtii/virtual_mic/logs/http-audio-out.log',
      log_file: '/home/ochtii/virtual_mic/logs/http-audio-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    },
    {
      name: 'netcast-websocket-audio',
      script: 'servers/websocket_audio_server.py',
      interpreter: 'python3',
      cwd: '/home/ochtii/virtual_mic',
      env: {
        NODE_ENV: 'production',
        PORT: 8765
      },
      error_file: '/home/ochtii/virtual_mic/logs/websocket-audio-error.log',
      out_file: '/home/ochtii/virtual_mic/logs/websocket-audio-out.log',
      log_file: '/home/ochtii/virtual_mic/logs/websocket-audio-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    },
    {
      name: 'netcast-web-audio',
      script: 'servers/audio_server.py',
      interpreter: 'python3',
      cwd: '/home/ochtii/virtual_mic',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      },
      error_file: '/home/ochtii/virtual_mic/logs/web-audio-error.log',
      out_file: '/home/ochtii/virtual_mic/logs/web-audio-out.log',
      log_file: '/home/ochtii/virtual_mic/logs/web-audio-combined.log',
      time: true,
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    }
  ]
};