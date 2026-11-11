import { aInstanteConDesfasaje } from "../../shared/tiempo/zonaConsultorio";

export interface DatosBloqueo {
  /** `null` para el odontólogo: la API toma su profesional del token (RN-AU-02). */
  profesionalId: string | null;
  fechaDesde: string;
  horaDesde: string;
  fechaHasta: string;
  horaHasta: string;
  motivo: string;
}

export interface CuerpoBloqueo {
  profesional_id?: string;
  inicio: string;
  fin: string;
  motivo: string;
}

/** Cuerpo del alta: `inicio` y `fin` con el desfasaje de la zona del consultorio (D8). */
export function armarCuerpoBloqueo(datos: DatosBloqueo): CuerpoBloqueo {
  const cuerpo: CuerpoBloqueo = {
    inicio: aInstanteConDesfasaje(datos.fechaDesde, datos.horaDesde),
    fin: aInstanteConDesfasaje(datos.fechaHasta, datos.horaHasta),
    motivo: datos.motivo.trim(),
  };
  if (datos.profesionalId !== null) cuerpo.profesional_id = datos.profesionalId;
  return cuerpo;
}

/** Un bloqueo cuyo `fin` es menor o igual al reloj ya terminó (D8): con `[)`, el fin no cuenta. */
export function terminado(fin: string, ahora: Date): boolean {
  return new Date(fin).getTime() <= ahora.getTime();
}

/** Vista diaria de la agenda de una fecha, con el profesional si hace falta (RN-HB-03). */
export function enlaceAgenda(
  fecha: string,
  profesionalId: string | null,
): string {
  const parametros = new URLSearchParams({ fecha });
  if (profesionalId !== null) parametros.set("profesional", profesionalId);
  return `/agenda?${parametros.toString()}`;
}
