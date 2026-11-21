import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  root: "web",
  server: {
    host: "127.0.0.1",
    port: 3000,
    strictPort: true,
    fs: {
      allow: ["web", "contracts", "node_modules"].map((directory) =>
        fileURLToPath(new URL(directory, import.meta.url))),
    },
    proxy: {
      "/api/v1": { target: "http://127.0.0.1:8000", ws: true },
    },
  },
});
