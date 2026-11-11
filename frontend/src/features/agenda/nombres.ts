import {
  nombreProfesional,
  PROFESIONAL_NO_DISPONIBLE,
  SIN_SILLON,
  SILLON_NO_DISPONIBLE,
} from "./grilla";
import type { Catalogos } from "./useCatalogos";

export const PRESTACION_NO_DISPONIBLE = "Prestación no disponible";

export interface Nombres {
  profesional: (id: string) => string;
  /** `null` es un turno sin sillón. */
  sillon: (id: string | null) => string;
  prestacion: (id: string) => string;
}

/**
 * Ids a nombres, incluidos los recursos desactivados. Un id que no figura en el catálogo cargado
 * se ve con un texto genérico, sin mostrar el id (D7).
 */
export function crearNombres(catalogos: Catalogos): Nombres {
  return {
    profesional: (id) => {
      const p = catalogos.profesionales.find((c) => c.id === id);
      return p === undefined ? PROFESIONAL_NO_DISPONIBLE : nombreProfesional(p);
    },
    sillon: (id) => {
      if (id === null) return SIN_SILLON;
      return (
        catalogos.sillones.find((c) => c.id === id)?.nombre ??
        SILLON_NO_DISPONIBLE
      );
    },
    prestacion: (id) =>
      catalogos.prestaciones.find((c) => c.id === id)?.nombre ??
      PRESTACION_NO_DISPONIBLE,
  };
}
