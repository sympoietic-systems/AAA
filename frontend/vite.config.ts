import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Load env file from the parent directory
  const env = loadEnv(mode, path.resolve(__dirname, '../'), 'AAA_')
  
  const backendHost = (env.AAA_SERVER_HOST && env.AAA_SERVER_HOST !== '0.0.0.0') ? env.AAA_SERVER_HOST : '127.0.0.1'
  const backendPort = env.AAA_SERVER_PORT || '8499'
  const frontendPort = parseInt(env.AAA_FRONTEND_PORT || process.env.PORT || '5174', 10)

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      port: frontendPort,
      strictPort: false,
      allowedHosts: true,
      proxy: {
        '/api': {
          target: `http://${backendHost}:${backendPort}`,
          changeOrigin: false,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: frontendPort,
      allowedHosts: true,
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (/\/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) {
                return 'vendor-react'
              }
              if (id.includes('katex')) {
                return 'vendor-katex'
              }
              if (
                id.includes('remark') ||
                id.includes('rehype') ||
                id.includes('unified') ||
                id.includes('micromark') ||
                id.includes('hast')
              ) {
                return 'vendor-markdown'
              }
            }
          },
        },
      },
      chunkSizeWarningLimit: 600,
    },
  }
})
