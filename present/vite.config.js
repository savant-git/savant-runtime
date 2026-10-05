import { defineConfig } from "/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/segue/exile_runtime/ui/node_modules/vite/dist/node/index.js";

export default defineConfig({
  root: "/root/savant-runtime/present",

  publicDir: false,

  server: {
    host: "0.0.0.0",
    port: 5174,
    strictPort: false
  },

  preview: {
    host: "0.0.0.0",
    port: 4174,
    strictPort: false
  },

  build: {
    outDir: "/root/savant-runtime/present/dist",
    emptyOutDir: true
  }
});
