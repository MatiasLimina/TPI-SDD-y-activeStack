import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    // El origen debe coincidir con CORS_ORIGINS de la API: otro puerto rompería el CORS sin aviso
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    // La limpieza automática de React Testing Library necesita un afterEach global
    globals: true,
    unstubGlobals: true,
    unstubEnvs: true,
  },
});
