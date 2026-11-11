import type { ReactNode } from "react";

import { TEXTO_SIN_PERMISO_LEER } from "./erroresGestion";
import type { Listado } from "./useListado";

interface PropsEstadoListado<T> {
  listado: Listado<T[]>;
  /** Mensaje propio de la pantalla para un listado vacío. */
  textoVacio: string;
  children: (datos: T[]) => ReactNode;
}

/** Carga, error con `Reintentar`, vacío o la tabla de una pantalla de gestión (D4). */
export function EstadoListado<T>({
  listado,
  textoVacio,
  children,
}: PropsEstadoListado<T>) {
  const { datos, error, cargando, reintentar } = listado;
  if (error !== null)
    return (
      <div role="alert">
        <p>{error.status === 403 ? TEXTO_SIN_PERMISO_LEER : error.mensaje}</p>
        <button type="button" onClick={reintentar}>
          Reintentar
        </button>
      </div>
    );
  if (cargando || datos === null) return <p role="status">Cargando…</p>;
  if (datos.length === 0) return <p>{textoVacio}</p>;
  return <>{children(datos)}</>;
}
