import { useCallback, useEffect, useState } from "react";

import type { ErrorApi } from "../../shared/api/errorApi";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { comoErrorApi } from "./errores";
import type { Prestacion, Profesional, Sillon } from "./tipos";

export interface Catalogos {
  profesionales: Profesional[];
  sillones: Sillon[];
  prestaciones: Prestacion[];
}

/**
 * Los tres catálogos, pedidos en paralelo al montar la página, sin caché global (D7). Incluyen
 * los recursos desactivados: hay turnos históricos que los referencian.
 */
export function useCatalogos(): {
  catalogos: Catalogos | null;
  /** Falla de la carga inicial: la pantalla ofrece `Reintentar`. */
  error: ErrorApi | null;
  reintentar: () => void;
  /**
   * Vuelve a pedir los tres catálogos tras un error que revela uno desactualizado (D7). Si falla,
   * conserva los anteriores y devuelve el error, para que lo muestre el formulario abierto.
   */
  recargar: () => Promise<ErrorApi | null>;
} {
  const cliente = useClienteApi();
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [version, setVersion] = useState(0);

  const recargar = useCallback(async (): Promise<ErrorApi | null> => {
    try {
      const [profesionales, sillones, prestaciones] = await Promise.all([
        cliente.pedir<Profesional[]>("GET", "/profesionales"),
        cliente.pedir<Sillon[]>("GET", "/sillones"),
        cliente.pedir<Prestacion[]>("GET", "/prestaciones"),
      ]);
      setCatalogos({ profesionales, sillones, prestaciones });
      return null;
    } catch (causa) {
      return comoErrorApi(causa);
    }
  }, [cliente]);

  useEffect(() => {
    let vigente = true;
    Promise.all([
      cliente.pedir<Profesional[]>("GET", "/profesionales"),
      cliente.pedir<Sillon[]>("GET", "/sillones"),
      cliente.pedir<Prestacion[]>("GET", "/prestaciones"),
    ])
      .then(([profesionales, sillones, prestaciones]) => {
        if (!vigente) return;
        setCatalogos({ profesionales, sillones, prestaciones });
        setError(null);
      })
      .catch((causa: unknown) => {
        if (vigente) setError(comoErrorApi(causa));
      });
    return () => {
      vigente = false;
    };
  }, [cliente, version]);

  return {
    catalogos,
    error,
    recargar,
    reintentar: () => {
      setError(null);
      setVersion((anterior) => anterior + 1);
    },
  };
}
