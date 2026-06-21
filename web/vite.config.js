import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// In dev the React app runs on :5173 and proxies the API calls to FastAPI on
// :8000 — same-origin paths, no CORS. In production FastAPI serves the built
// files, so these same relative paths resolve to the API directly.
const API = 'http://localhost:8000';

export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/health': API,
      '/diagnose': API,
      '/corpus': API,
      '/benchmark': API,
    },
  },
});
