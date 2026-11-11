import { useEffect, useState } from "react";

import type { ErrorApi } from "../../shared/api/errorApi";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { comoErrorApi } from "../../shared/api/comoErrorApi";
import type { RespuestaAgenda } from "./tipos";

export interface ConsultaAgenda {
  desde: string;
  hasta: string;
  profesionalId: string | null;
  sillonId: string | null;
}

function rutaDeAgenda(consulta: ConsultaAgenda): string {
  const parametros = new URLSearchParams({
    desde: consulta.desde,
    hasta: consulta.hasta,
  });
  if (consulta.profesionalId !== null)
    parametros.set("profesional_id", consulta.profesionalId);
  if (consulta.sillonId !== null)
    parametros.set("sillon_id", consulta.sillonId);
  return `/turnos?${parametros.toString()}`;
}

/**
 * Turnos y bloqueos del período, con `GET /turnos` (DD-32). Solo escribe el estado el pedido
 * vigente: el efecto marca el suyo como no vigente al limpiarse (D13). Los datos y el error se
 * guardan con su clave (la ruta pedida) y solo se muestran si coincide con la actual, así que
 * nunca se ven datos de otro período y `cargando` se deriva sin escribir estado.
 */
export function useAgenda(consulta: ConsultaAgenda): {
  datos: RespuestaAgenda | null;
  error: ErrorApi | null;
  cargando: boolean;
  /** Vuelve a pedir el mismo período, manteniendo a la vista los datos actuales (D13). */
  recargar: () => void;
} {
  const cliente = useClienteApi();
  const clave = rutaDeAgenda(consulta);
  const [recibido, setRecibido] = useState<{
    clave: string;
    datos: RespuestaAgenda;
  } | null>(null);
  const [fallo, setFallo] = useState<{ clave: string; error: ErrorApi } | null>(
    null,
  );

  // Cambiar `version` repite el efecto con la misma clave: invalida el pedido en curso, así
  // una lectura vieja del mismo período no pisa al turno recién creado
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let vigente = true;
    cliente
      .pedir<RespuestaAgenda>("GET", clave)
      .then((datos) => {
        if (!vigente) return;
        setRecibido({ clave, datos });
        setFallo(null);
      })
      .catch((causa: unknown) => {
        if (vigente) setFallo({ clave, error: comoErrorApi(causa) });
      });
    return () => {
      vigente = false;
    };
  }, [cliente, clave, version]);

  const datos = recibido?.clave === clave ? recibido.datos : null;
  const error = fallo?.clave === clave ? fallo.error : null;
  return {
    datos,
    error,
    cargando: datos === null && error === null,
    recargar: () => {
      setFallo(null);
      setVersion((anterior) => anterior + 1);
    },
  };
}
