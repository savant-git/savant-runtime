import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const executionTarget =
  process.env.SAVANT_EXECUTION_TARGET
  ?? "http://127.0.0.1:8765";

export default defineConfig({
  base: "/splyce/",

  plugins: [
    react(),
  ],

  server: {
    host: "127.0.0.1",
    port: 5180,
    strictPort: true,

    allowedHosts: [
      ".trycloudflare.com",
    ],

    proxy: {
      "/api/execution": {
        target: executionTarget,
        changeOrigin: false,
      },
    },
  },

  preview: {
    host: "127.0.0.1",
    port: 5180,
    strictPort: true,

    allowedHosts: [
      ".trycloudflare.com",
    ],

    proxy: {
      "/api/execution": {
        target: executionTarget,
        changeOrigin: false,
      },
    },
  },
});
