module.exports = {
  apps: [
    {
      name: 'pimic-audio-streaming',
      script: 'server.js',
      cwd: '/home/ochtii/pimic/audio',
      instances: 1,
      exec_mode: 'fork',
      
      // Environment
      env: {
        NODE_ENV: 'production',
        PORT: 6969,
        STREAM_PORT: 420,
        MAX_BITRATE: 320,
        MIN_BITRATE: 64
      },
      
      // Logging
      log_file: '/home/ochtii/pimic/logs/audio-combined.log',
      out_file: '/home/ochtii/pimic/logs/audio-out.log',
      error_file: '/home/ochtii/pimic/logs/audio-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      
      // Process management
      watch: false,
      ignore_watch: ['node_modules', 'logs', '*.log'],
      max_memory_restart: '256M',
      restart_delay: 4000,
      max_restarts: 10,
      min_uptime: '10s',
      
      // Auto-restart
      autorestart: true,
      
      // Graceful shutdown
      kill_timeout: 5000,
      wait_ready: true,
      listen_timeout: 3000,
      
      // Health monitoring
      health_check_grace_period: 10000,
      health_check_fatal: true
    }
  ],

  // Deployment configuration
  deploy: {
    production: {
      user: 'ochtii',
      host: 'raspberrypi.local',
      ref: 'origin/master',
      repo: 'https://github.com/your-repo/pimic.git',
      path: '/home/ochtii/pimic',
      'post-deploy': 'cd audio && npm install --production && pm2 reload ecosystem.config.js --env production',
      'pre-setup': 'mkdir -p /home/ochtii/pimic/logs'
    }
  }
};