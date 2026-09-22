import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    proxy: {
      "/api/attachment": {
        target: "http://127.0.0.1:8791",
        changeOrigin: false
      },
      "/api": {
        target: "http://127.0.0.1:8787",
        changeOrigin: false
      }
    }
  }
});
