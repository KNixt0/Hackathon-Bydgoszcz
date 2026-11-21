/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.VITE_BACKEND_URL || "http://localhost:8000";
  const proxy = {
    "/api": { target: backend, changeOrigin: true },
    "/socket.io": { target: backend, changeOrigin: true, ws: true },
  };
  return {
    plugins: [react()],
    server: { port: Number(env.FRONTEND_PORT) || 5173, proxy },
    preview: { port: Number(env.FRONTEND_PORT) || 4173, proxy },
    build: { sourcemap: false, chunkSizeWarningLimit: 1200 },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/**/*.test.{ts,tsx}"],
      css: false,
    },
  };
});
