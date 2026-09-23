import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Proxies /api calls to the FastAPI backend during local dev,
// so the frontend can just call fetch("/api/...").
// Under docker compose the backend is another container, so the target is
// overridden with BACKEND_ORIGIN.
const backendOrigin = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": backendOrigin,
    },
  },
});
