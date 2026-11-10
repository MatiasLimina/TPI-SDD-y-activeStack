import { diasEntre, instanteALocal } from "../../shared/tiempo/zonaConsultorio";

const MINUTOS_POR_FILA = 5;
const MINUTOS_POR_DIA = 24 * 60;

/** Todo lo que ocupa tiempo en la agenda: un turno o un bloqueo. */
export interface Intervalo {
  inicio: string;
  fin: string;
}

/** Tramo de un elemento dentro de un día local, con minutos recortados a `[0, 1440]` (D4). */
export interface Segmento {
  /** `YYYY-MM-DD` del día local. */
  fecha: string;
  /** Minutos reales dentro del día, para mostrar la hora sin redondear. */
  desdeMin: number;
  hastaMin: number;
  /** Fila de 5 minutos desde 0: inicio redondeado hacia abajo. */
  fila: number;
  /** Cantidad de filas: el fin se redondea hacia arriba. */
  filas: number;
  continuaAntes: boolean;
  continuaDespues: boolean;
}

/** Minutos de un instante respecto de la medianoche de `dia`, en la zona del consultorio. */
function minutosDesde(dia: string, instante: string): number {
  const local = instanteALocal(instante);
  return diasEntre(dia, local.fecha) * MINUTOS_POR_DIA + local.minutosDelDia;
}

/**
 * Un segmento por cada día visible que toca el elemento. Con `[)` (RN-AG-03), un fin exacto a
 * las 00:00 no genera un segmento de 0 minutos en el día siguiente.
 */
export function segmentosPorDia(
  elemento: Intervalo,
  dias: string[],
): Segmento[] {
  const segmentos: Segmento[] = [];
  for (const fecha of dias) {
    const inicio = minutosDesde(fecha, elemento.inicio);
    const fin = minutosDesde(fecha, elemento.fin);
    if (fin <= 0 || inicio >= MINUTOS_POR_DIA) continue;
    const desdeMin = Math.max(inicio, 0);
    const hastaMin = Math.min(fin, MINUTOS_POR_DIA);
    const fila = Math.floor(desdeMin / MINUTOS_POR_FILA);
    segmentos.push({
      fecha,
      desdeMin,
      hastaMin,
      fila,
      filas: Math.ceil(hastaMin / MINUTOS_POR_FILA) - fila,
      continuaAntes: inicio < 0,
      continuaDespues: fin > MINUTOS_POR_DIA,
    });
  }
  return segmentos;
}
