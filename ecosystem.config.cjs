// PM2 Ecosystem Configuration for AAA
// Usage:
//   pm2 start ecosystem.config.cjs              # start all
//   pm2 start ecosystem.config.cjs --only aaa-backend   # backend only
//   pm2 start ecosystem.config.cjs --only aaa-frontend  # frontend only
//   pm2 restart aaa-backend                     # restart individual
//   pm2 logs aaa-backend                        # tail logs per app
//   pm2 monit                                    # real-time dashboard

module.exports = {
  apps: [
    {
      name: "aaa-backend",
      script: "bash",
      args: "scripts/run_backend.sh",
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        NODE_ENV: "production",
      },
      // Log rotation settings
      max_size: "10M",
      retain: 5,
      time: true,
      // Graceful shutdown
      kill_timeout: 10000,
      wait_ready: false,
    },
    {
      name: "aaa-frontend",
      script: "bash",
      args: "scripts/run_frontend.sh",
      cwd: __dirname,
      autorestart: true,
      watch: false,
      max_restarts: 5,
      restart_delay: 10000,
      env: {
        NODE_ENV: "production",
      },
      max_size: "10M",
      retain: 5,
      time: true,
      kill_timeout: 5000,
      wait_ready: false,
    },
  ],
};
