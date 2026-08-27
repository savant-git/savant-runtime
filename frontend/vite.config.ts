import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],

  preview: {
    allowedHosts: true,
  },

  build: {
    target: "es2022",
    sourcemap: true,
    chunkSizeWarningLimit: 500,

    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined;
          }

          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("/scheduler/")
          ) {
            return "react";
          }

          if (id.includes("/gsap/")) {
            return "motion";
          }

          if (id.includes("@react-three/fiber")) {
            return "r3f";
          }

          if (id.includes("@react-three/postprocessing")) {
            return "r3-post";
          }

          if (id.includes("/postprocessing/")) {
            return "postprocessing";
          }

          if (
            id.includes("/three/examples/") ||
            id.includes("/three/addons/")
          ) {
            return "three-extras";
          }

          if (id.includes("/three/")) {
            return "three-core";
          }

          return undefined;
        },
      },
    },
  },

  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: true,
  },
});
