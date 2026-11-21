/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backend = env.VITE_BACKEND_URL || "http://localhost:8000";
  return {
    plugins: [react()],
    server: {
      port: Number(env.FRONTEND_PORT) || 5173,
      proxy: {
        "/api": { target: backend, changeOrigin: true },
        "/socket.io": { target: backend, changeOrigin: true, ws: true },
      },
    },
    build: { sourcemap: false, chunkSizeWarningLimit: 900 },
    test: {
      globals: true,
      environment: "jsdom",
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/**/*.test.{ts,tsx}"],
      css: false,
    },
  };
});
