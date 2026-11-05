import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// DOCKER=1 cuando corre dentro del contenedor (lo inyecta docker-compose.yml).
// Dentro se expone el server y se usa polling: los bind mounts de Windows no
// propagan eventos de archivo a Linux y el HMR dejaría de dispararse.
const enDocker = !!process.env.DOCKER

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    open: !enDocker,
    ...(enDocker ? { watch: { usePolling: true } } : {}),
  }
})
