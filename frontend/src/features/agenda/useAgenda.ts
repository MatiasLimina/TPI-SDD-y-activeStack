import { useEffect, useState } from "react";

import { useClienteApi } from "../sesion/ProveedorSesion";
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

/** Turnos y bloqueos del período, con `GET /turnos` (DD-32). */
export function useAgenda(consulta: ConsultaAgenda): {
  datos: RespuestaAgenda | null;
  cargando: boolean;
} {
  const cliente = useClienteApi();
  const ruta = rutaDeAgenda(consulta);
  const [datos, setDatos] = useState<RespuestaAgenda | null>(null);

  useEffect(() => {
    void cliente
      .pedir<RespuestaAgenda>("GET", ruta)
      .then((respuesta) => setDatos(respuesta));
  }, [cliente, ruta]);

  return { datos, cargando: datos === null };
}
