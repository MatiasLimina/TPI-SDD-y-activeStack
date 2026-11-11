import {
  fechaHoraCompleta,
  instanteALocal,
} from "../../shared/tiempo/zonaConsultorio";
import type { Nombres } from "../agenda/nombres";

export type AccionAuditoria = "crear" | "reprogramar" | "cancelar";

/** Estado de un turno dentro de un registro de auditoría (DD-25). */
export interface ValoresTurno {
  profesional_id: string;
  /** Nunca se muestra: el historial omite al paciente (DD-25 b). */
  paciente_id: string;
  prestacion_id: string;
  sillon_id: string | null;
  inicio: string;
  fin: string;
  duracion_min: number;
  estado: string;
  motivo_cancelacion: string | null;
}

export interface RegistroAuditoria {
  id: string;
  turno_id: string;
  accion: AccionAuditoria;
  /** Nunca se muestra: solo se compara con el usuario de la sesión (D10). */
  usuario_id: string | null;
  ocurrido_en: string;
  valores_previos: ValoresTurno | null;
  valores_nuevos: ValoresTurno | null;
}

const ETIQUETAS: Record<AccionAuditoria, string> = {
  crear: "Creación",
  reprogramar: "Reprogramación",
  cancelar: "Cancelación",
};

export function etiquetaAccion(accion: AccionAuditoria): string {
  return ETIQUETAS[accion];
}

/** `Vos` si el registro es del usuario de la sesión; la API no expone el nombre de nadie (D10). */
export function autorDe(
  usuarioId: string | null,
  usuarioSesion: string | null,
): "Vos" | "Otro usuario" {
  return usuarioSesion !== null && usuarioId === usuarioSesion
    ? "Vos"
    : "Otro usuario";
}

/** `DD/MM/AAAA HH:MM a HH:MM`: un turno nunca cruza la medianoche (DD-27 c y e). */
function textoHorario(valores: ValoresTurno): string {
  return `${fechaHoraCompleta(valores.inicio)} a ${instanteALocal(valores.fin).hora}`;
}

const textoDuracion = (valores: ValoresTurno) => `${valores.duracion_min} min`;

export interface DatoDeAuditoria {
  etiqueta: string;
  valor: string;
}

/** Valores iniciales de una creación, con los nombres de los catálogos de la agenda. */
export function datosDeCreacion(
  valores: ValoresTurno,
  nombres: Nombres,
): DatoDeAuditoria[] {
  return [
    { etiqueta: "Horario", valor: textoHorario(valores) },
    {
      etiqueta: "Profesional",
      valor: nombres.profesional(valores.profesional_id),
    },
    {
      etiqueta: "Prestación",
      valor: nombres.prestacion(valores.prestacion_id),
    },
    { etiqueta: "Sillón", valor: nombres.sillon(valores.sillon_id) },
    { etiqueta: "Duración", valor: textoDuracion(valores) },
  ];
}

function mismoInstante(a: string, b: string): boolean {
  return new Date(a).getTime() === new Date(b).getTime();
}

/** Solo lo que difiere entre antes y después, cada dato como `Etiqueta: antes → después`. */
export function cambiosDeReprogramacion(
  previos: ValoresTurno,
  nuevos: ValoresTurno,
  nombres: Nombres,
): string[] {
  const candidatos: Array<[string, string, string]> = [
    ["Horario", textoHorario(previos), textoHorario(nuevos)],
    [
      "Profesional",
      nombres.profesional(previos.profesional_id),
      nombres.profesional(nuevos.profesional_id),
    ],
    [
      "Sillón",
      nombres.sillon(previos.sillon_id),
      nombres.sillon(nuevos.sillon_id),
    ],
    ["Duración", textoDuracion(previos), textoDuracion(nuevos)],
  ];
  // Se compara por los datos crudos: dos ids distintos fuera del catálogo se verían iguales
  const cambio = [
    !mismoInstante(previos.inicio, nuevos.inicio) ||
      !mismoInstante(previos.fin, nuevos.fin),
    previos.profesional_id !== nuevos.profesional_id,
    previos.sillon_id !== nuevos.sillon_id,
    previos.duracion_min !== nuevos.duracion_min,
  ];
  return candidatos
    .filter((_, i) => cambio[i])
    .map(([etiqueta, antes, despues]) => `${etiqueta}: ${antes} → ${despues}`);
}

export function textoDeCancelacion(valores: ValoresTurno): string {
  return valores.motivo_cancelacion === null
    ? "Sin motivo"
    : `Motivo: ${valores.motivo_cancelacion}`;
}
