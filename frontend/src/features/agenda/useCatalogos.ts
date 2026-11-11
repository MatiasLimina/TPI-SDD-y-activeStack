import { useCallback, useEffect, useRef, useState } from "react";

import type { ErrorApi } from "../../shared/api/errorApi";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { comoErrorApi } from "../../shared/api/comoErrorApi";
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
   * Si una carga más nueva la reemplazó, descarta su resultado y devuelve `null`.
   */
  recargar: () => Promise<ErrorApi | null>;
} {
  const cliente = useClienteApi();
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);
  const [error, setError] = useState<ErrorApi | null>(null);
  const [version, setVersion] = useState(0);

  // Cada carga (inicial, reintento o recarga) toma un número; solo escribe la última pedida,
  // así una respuesta tardía nunca pisa a una más nueva
  const ultimaCarga = useRef(0);

  const pedirTodos = useCallback(
    () =>
      Promise.all([
        cliente.pedir<Profesional[]>("GET", "/profesionales"),
        cliente.pedir<Sillon[]>("GET", "/sillones"),
        cliente.pedir<Prestacion[]>("GET", "/prestaciones"),
      ]),
    [cliente],
  );

  const recargar = useCallback(async (): Promise<ErrorApi | null> => {
    ultimaCarga.current += 1;
    const mia = ultimaCarga.current;
    try {
      const [profesionales, sillones, prestaciones] = await pedirTodos();
      if (mia === ultimaCarga.current)
        setCatalogos({ profesionales, sillones, prestaciones });
      return null;
    } catch (causa) {
      return mia === ultimaCarga.current ? comoErrorApi(causa) : null;
    }
  }, [pedirTodos]);

  useEffect(() => {
    let vigente = true;
    ultimaCarga.current += 1;
    const mia = ultimaCarga.current;
    pedirTodos()
      .then(([profesionales, sillones, prestaciones]) => {
        if (!vigente || mia !== ultimaCarga.current) return;
        setCatalogos({ profesionales, sillones, prestaciones });
        setError(null);
      })
      .catch((causa: unknown) => {
        if (vigente && mia === ultimaCarga.current)
          setError(comoErrorApi(causa));
      });
    return () => {
      vigente = false;
    };
  }, [pedirTodos, version]);

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
