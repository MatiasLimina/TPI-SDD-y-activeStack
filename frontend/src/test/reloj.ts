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

/**
 * Reloj fijo con avance manual (sin `shouldAdvanceTime`): para probar esperas como la de 300 ms
 * de la búsqueda de pacientes. React Testing Library solo adelanta los temporizadores si ve el
 * global `jest`; sin él, `userEvent` y `findBy*` esperan para siempre con relojes falsos de
 * Vitest. El global se desinstala solo (`unstubGlobals`).
 */
export function usarRelojManual(): void {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(AHORA_ISO);
    vi.stubGlobal("jest", {
      advanceTimersByTime: (ms: number) => vi.advanceTimersByTime(ms),
    });
  });
  afterEach(() => {
    vi.useRealTimers();
  });
}
