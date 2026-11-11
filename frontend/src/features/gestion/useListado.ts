import { useEffect, useState } from "react";

import { comoErrorApi } from "../../shared/api/comoErrorApi";
import type { ErrorApi } from "../../shared/api/errorApi";
import { useClienteApi } from "../sesion/ProveedorSesion";

export interface Listado<T> {
  /** Datos de la ruta actual: nunca los de una ruta anterior. */
  datos: T | null;
  error: ErrorApi | null;
  cargando: boolean;
  /** Vuelve a pedir la misma ruta manteniendo a la vista los datos actuales. */
  recargar: () => void;
  /** Repite el pedido tras un error de carga. */
  reintentar: () => void;
}

/**
 * Listado de una pantalla de gestión (D4), sin caché global (DD-34 k). Los datos y el error se
 * guardan con su ruta y solo se muestran si coincide con la actual, y el efecto marca su pedido
 * como no vigente al limpiarse: una respuesta o un error tardío nunca pisa a uno más nuevo.
 * Con ruta `null` no pide nada.
 */
export function useListado<T>(ruta: string | null): Listado<T> {
  const cliente = useClienteApi();
  const [recibido, setRecibido] = useState<{ ruta: string; datos: T } | null>(
    null,
  );
  const [fallo, setFallo] = useState<{ ruta: string; error: ErrorApi } | null>(
    null,
  );
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (ruta === null) return;
    let vigente = true;
    cliente
      .pedir<T>("GET", ruta)
      .then((datos) => {
        if (!vigente) return;
        setRecibido({ ruta, datos });
        setFallo(null);
      })
      .catch((causa: unknown) => {
        if (vigente) setFallo({ ruta, error: comoErrorApi(causa) });
      });
    return () => {
      vigente = false;
    };
  }, [cliente, ruta, version]);

  const datos = recibido?.ruta === ruta ? recibido.datos : null;
  const error = fallo?.ruta === ruta ? fallo.error : null;
  const recargar = () => {
    setFallo(null);
    setVersion((anterior) => anterior + 1);
  };
  return {
    datos,
    error,
    cargando: ruta !== null && datos === null && error === null,
    recargar,
    reintentar: recargar,
  };
}
