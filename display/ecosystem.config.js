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
      script: 'python3',
      args: 'deploy_monitor.py',
      cwd: '/home/ochtii/pimic',
      autorestart: true,
      watch: false,
      max_memory_restart: '100M',
      env: {
        NODE_ENV: 'production',
        PATH: '/usr/bin:/home/ochtii/.npm-global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
      },
      log_file: '/home/ochtii/pimic/display/deploy-pm2.log',
      out_file: '/home/ochtii/pimic/display/deploy-pm2-out.log',
      error_file: '/home/ochtii/pimic/display/deploy-pm2-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z'
    },
    {
      name: 'pimic-webhook',
      script: 'python3',
      args: 'webhook_handler.py',
      cwd: '/home/ochtii/pimic',
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        NODE_ENV: 'production',
        GITHUB_WEBHOOK_SECRET: 'your-webhook-secret-change-me'
      },
      log_file: '/home/ochtii/pimic/display/webhook-pm2.log',
      out_file: '/home/ochtii/pimic/display/webhook-pm2-out.log',
      error_file: '/home/ochtii/pimic/display/webhook-pm2-error.log',
      log_date_format: 'YYYY-MM-DD HH:mm Z'
    }
  ]
}