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
    env: {
      // Zona distinta de la del consultorio (y de la de esta máquina): cualquier uso accidental
      // de la zona local falla. `zonaDePrueba.test.ts` verifica que el mecanismo funciona (D15)
      TZ: "Asia/Tokyo",
    },
  },
});
