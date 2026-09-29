import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8027",
      "/health": "http://127.0.0.1:8027",
      "/ready": "http://127.0.0.1:8027",
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          charts: [
            "echarts/core",
            "echarts/charts",
            "echarts/components",
            "echarts/renderers",
          ],
          react: ["react", "react-dom"],
        },
      },
    },
  },
});
