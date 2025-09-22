module.exports = {
  apps: [
    {
      name: 'pimic-display',
      script: 'python3',
      args: 'http_server.py',
      cwd: '/home/ochtii/pimic/display',
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      },
      log_file: '/home/ochtii/pimic/display/pm2.log',
      out_file: '/home/ochtii/pimic/display/pm2-out.log',
      error_file: '/home/ochtii/pimic/display/pm2-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z'
    },
    {
      name: 'pimic-deploy',
      script: '/home/ochtii/pimic/deploy.sh',
      cwd: '/home/ochtii/pimic',
      autorestart: true,
      watch: false,
      cron_restart: '*/5 * * * *', // Alle 5 Minuten auf Updates prüfen
      max_memory_restart: '100M',
      env: {
        NODE_ENV: 'production'
      },
      log_file: '/home/ochtii/pimic/display/deploy-pm2.log',
      out_file: '/home/ochtii/pimic/display/deploy-pm2-out.log',
      error_file: '/home/ochtii/pimic/display/deploy-pm2-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z'
    }
  ]
}