import { AHORA_ISO } from "./tokens";

/**
 * Instala el reloj fijo de los specs (2026-11-09T12:00:00Z) en cada test.
 * `shouldAdvanceTime` deja correr los temporizadores de Testing Library (`findBy*`,
 * `waitFor`), que si no se colgarían; el reloj de `Date` queda fijo salvo lo que avancen
 * los milisegundos reales del test, sin cruzar nunca el segundo que separa los casos.
 */
export function usarRelojFijo(): void {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(AHORA_ISO);
  });
  afterEach(() => {
    vi.useRealTimers();
  });
}
