import type { Rol } from "../sesion/claims";
import {
  diaYMes,
  etiquetaDiaCompleta,
  fechaCompleta,
  instanteALocal,
  lunesDeLaSemana,
  sumarDias,
} from "../../shared/tiempo/zonaConsultorio";

export type Vista = "dia" | "semana";
export type Columnas = "profesional" | "sillon";

/** Estado de la vista de `/agenda`, que vive en los parámetros de la URL (D6). */
export interface VistaAgenda {
  vista: Vista;
  /** `YYYY-MM-DD`. */
  fecha: string;
  profesionalId: string | null;
  sillonId: string | null;
  columnas: Columnas;
  cancelados: boolean;
}

export interface RangoFechas {
  desde: string;
  hasta: string;
}

const FORMATO_FECHA = /^(\d{4})-\d{2}-\d{2}$/;
const FORMATO_UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Formato, calendario real y año de 1000 a 9998: con otro, la API da 422 o `Date.UTC` se equivoca (P7). */
function esFechaValida(fecha: string | null): fecha is string {
  if (fecha === null) return false;
  const coincidencia = FORMATO_FECHA.exec(fecha);
  if (coincidencia === null) return false;
  const anio = Number(coincidencia[1]);
  if (anio < 1000 || anio > 9998) return false;
  // Una fecha que no existe (2026-02-30) se normaliza a otra al sumarle cero días
  return sumarDias(fecha, 0) === fecha;
}

function idOIgnorar(valor: string | null): string | null {
  return valor !== null && FORMATO_UUID.test(valor) ? valor : null;
}

/** Un valor inválido se ignora y toma el de por defecto; `hoy` es el día del consultorio. */
export function leerVista(
  parametros: URLSearchParams,
  rol: Rol,
  hoy: string,
): VistaAgenda {
  const fecha = parametros.get("fecha");
  const vista: Vista = parametros.get("vista") === "semana" ? "semana" : "dia";
  const esRecepcionista = rol === "recepcionista";
  return {
    vista,
    fecha: esFechaValida(fecha) ? fecha : hoy,
    profesionalId: esRecepcionista
      ? idOIgnorar(parametros.get("profesional"))
      : null,
    sillonId: idOIgnorar(parametros.get("sillon")),
    columnas:
      esRecepcionista &&
      vista === "dia" &&
      parametros.get("columnas") === "sillon"
        ? "sillon"
        : "profesional",
    cancelados: parametros.get("cancelados") === "1",
  };
}

/** Período que se pide a la API: un día, o la semana de lunes a domingo (D2). */
export function aRango(vista: VistaAgenda): RangoFechas {
  if (vista.vista === "dia") return { desde: vista.fecha, hasta: vista.fecha };
  const lunes = lunesDeLaSemana(vista.fecha);
  return { desde: lunes, hasta: sumarDias(lunes, 6) };
}

/** Parámetros de URL de una vista: solo lo que no es el valor por defecto, salvo vista y fecha. */
export function aParametros(vista: VistaAgenda): URLSearchParams {
  const parametros = new URLSearchParams();
  parametros.set("vista", vista.vista);
  parametros.set("fecha", vista.fecha);
  if (vista.profesionalId !== null)
    parametros.set("profesional", vista.profesionalId);
  if (vista.sillonId !== null) parametros.set("sillon", vista.sillonId);
  if (vista.columnas === "sillon") parametros.set("columnas", "sillon");
  if (vista.cancelados) parametros.set("cancelados", "1");
  return parametros;
}

/** Rótulo del período visible (D19): el día, o la semana con el año en ambas fechas si cruza de año. */
export function rotuloPeriodo(vista: VistaAgenda): string {
  if (vista.vista === "dia") return etiquetaDiaCompleta(vista.fecha);
  const { desde, hasta } = aRango(vista);
  const inicio =
    desde.slice(0, 4) === hasta.slice(0, 4)
      ? diaYMes(desde)
      : fechaCompleta(desde);
  return `Semana del ${inicio} al ${fechaCompleta(hasta)}`;
}

/**
 * Vista a la que ir tras guardar un turno (D20): la misma con la `fecha` del turno si su día en
 * la zona del consultorio cae fuera del período visible, o `null` si ya se ve.
 */
export function vistaTrasGuardar(
  vista: VistaAgenda,
  inicio: string,
): VistaAgenda | null {
  const { fecha } = instanteALocal(inicio);
  const { desde, hasta } = aRango(vista);
  return fecha >= desde && fecha <= hasta ? null : { ...vista, fecha };
}
