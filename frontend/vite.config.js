import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api and /thumbnails to the FastAPI backend during development so the
// frontend can use same-origin relative URLs (also how it works in Docker).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/thumbnails": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
