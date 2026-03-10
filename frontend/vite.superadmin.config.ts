import { defineConfig, Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

// superadmin.html'i index.html gibi sun (Vite'ın ÖNCESİNDE çalışır)
function superadminSpa(): Plugin {
  return {
    name: 'superadmin-spa',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || ''
        // Dosya uzantısı olan istekleri (js, css, svg vb.) atla
        if (url.includes('.') || url.startsWith('/@') || url.startsWith('/node_modules') || url.startsWith('/src')) {
          return next()
        }
        // Tüm sayfa navigasyonları için superadmin.html'i sun
        const htmlPath = path.resolve(__dirname, 'superadmin.html')
        let html = fs.readFileSync(htmlPath, 'utf-8')
        server.transformIndexHtml(url, html).then((transformed) => {
          res.setHeader('Content-Type', 'text/html')
          res.statusCode = 200
          res.end(transformed)
        }).catch(next)
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), superadminSpa()],
  appType: 'mpa', // index.html otomatik fallback'ini devre dışı bırak
  server: {
    host: '0.0.0.0',
    port: 8100,
    watch: {
      usePolling: true,
    },
  },
  build: {
    rollupOptions: {
      input: path.resolve(__dirname, 'superadmin.html'),
    },
    outDir: 'dist-superadmin',
  },
})
