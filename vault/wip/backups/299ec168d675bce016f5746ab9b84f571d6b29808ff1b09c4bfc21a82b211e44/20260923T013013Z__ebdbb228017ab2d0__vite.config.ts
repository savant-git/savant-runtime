import {
  defineConfig,
} from "vite";

import react from (
  "@vitejs/plugin-react"
);


const executionTarget =
  process.env
    .SAVANT_EXECUTION_TARGET
  ?? "http://127.0.0.1:8765";


export default defineConfig({
  plugins: [
    react(),
  ],

  server: {
    proxy: {
      "/api/execution": {
        target:
          executionTarget,

        changeOrigin:
          false,
      },
    },
  },

  preview: {
    proxy: {
      "/api/execution": {
        target:
          executionTarget,

        changeOrigin:
          false,
      },
    },
  },
});
