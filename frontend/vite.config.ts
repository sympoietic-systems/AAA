import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Load env file from the parent directory
  const env = loadEnv(mode, path.resolve(__dirname, '../'), 'AAA_')
  
  const host = env.AAA_SERVER_HOST || '127.0.0.1'
  const port = env.AAA_SERVER_PORT || '8499'

  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '0.0.0.0',
      allowedHosts: ['aaa.sokaris.link', '.sokaris.link', 'aaa.sympoietic.systems', '.sympoietic.systems'],
      proxy: {
        '/api': {
          target: `http://${host}:${port}`,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 5173,
      allowedHosts: ['aaa.sokaris.link', '.sokaris.link', 'aaa.sympoietic.systems', '.sympoietic.systems'],
    },
  }
})

