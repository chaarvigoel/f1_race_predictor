import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Local dev: base '/' so /data/sessions.json maps to public/data/ (no subpath confusion).
// Production build: GitHub Pages project site needs /f1_race_predictor/.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'serve' ? '/' : '/f1_race_predictor/',
}));
