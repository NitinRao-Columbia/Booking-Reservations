import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5002,
    proxy: {
      '/bills': {
        target: 'http://10.206.104.164:8000',
        changeOrigin: true,
      },
    },
  },
});
