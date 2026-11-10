import type { ErrorApi } from "../../shared/api/errorApi";

export type Operacion = "crear" | "reprogramar" | "cancelar";

/** Campos de los formularios de turno a los que puede ir un error. */
export type CampoTurno =
  | "profesional"
  | "paciente"
  | "prestacion"
  | "sillon"
  | "fecha"
  | "hora"
  | "duracion";

export interface ErrorTurnoInterpretado {
  /** Error del formulario entero, anunciado como alerta. */
  general: string | null;
  porCampo: Partial<Record<CampoTurno, string>>;
  /** El turno ya no admite la operación: el envío queda deshabilitado (DD-22, DD-23). */
  turnoObsoleto: boolean;
  /** El error revela un catálogo desactualizado (D7). */
  releerCatalogos: boolean;
  /** El error revela un cambio en la agenda (D13). */
  releerAgenda: boolean;
}

const TEXTO_REVISAR_CAMPO = "Revisá este campo.";
const TEXTO_REVISAR_DATOS = "Revisá los datos ingresados.";
const TEXTO_SIN_PERMISO = "No tenés permiso para esta operación.";

/** Orden fijo con el que se nombran los recursos en conflicto. */
const ORDEN_RECURSOS = ["profesional", "sillon", "paciente"] as const;
const NOMBRE_DEL_RECURSO: Record<(typeof ORDEN_RECURSOS)[number], string> = {
  profesional: "el profesional",
  sillon: "el sillón",
  paciente: "el paciente",
};

/** Campo de la API (`loc`) a campo del formulario. */
const CAMPO_DE_LA_API: Record<string, CampoTurno> = {
  profesional_id: "profesional",
  paciente_id: "paciente",
  prestacion_id: "prestacion",
  sillon_id: "sillon",
  inicio: "hora",
  duracion_min: "duracion",
};

const REFERENCIAS: Record<
  string,
  { campo: CampoTurno; sustantivo: string; femenino: boolean }
> = {
  profesional: {
    campo: "profesional",
    sustantivo: "profesional",
    femenino: false,
  },
  paciente: { campo: "paciente", sustantivo: "paciente", femenino: false },
  prestacion: { campo: "prestacion", sustantivo: "prestación", femenino: true },
  sillon: { campo: "sillon", sustantivo: "sillón", femenino: false },
};

function resultado(
  parcial: Partial<ErrorTurnoInterpretado>,
): ErrorTurnoInterpretado {
  return {
    general: null,
    porCampo: {},
    turnoObsoleto: false,
    releerCatalogos: false,
    releerAgenda: false,
    ...parcial,
  };
}

function textoDeSolapamiento(recursos: unknown): string {
  const presentes = Array.isArray(recursos) ? recursos : [];
  const nombres = ORDEN_RECURSOS.filter((r) => presentes.includes(r)).map(
    (r) => NOMBRE_DEL_RECURSO[r],
  );
  const lista =
    nombres.length <= 1
      ? nombres.join("")
      : `${nombres.slice(0, -1).join(", ")} y ${nombres[nombres.length - 1]}`;
  return `Ese horario ya está ocupado para ${lista}.`;
}

function interpretarReferencia(
  error: ErrorApi,
  operacion: Operacion,
): ErrorTurnoInterpretado {
  const referencia = REFERENCIAS[String(error.datos.referencia)];
  if (referencia === undefined)
    return resultado({ general: error.mensaje, releerCatalogos: true });
  const { campo, sustantivo, femenino } = referencia;
  const articulo = femenino ? "La" : "El";
  const estado =
    error.datos.motivo === "inexistente"
      ? "no existe"
      : femenino
        ? "está inactiva"
        : "está inactivo";
  const texto = `${articulo} ${sustantivo} ${estado}`;
  // Paciente y prestación no se pueden cambiar al reprogramar: solo queda cancelar (DD-26)
  if (
    operacion === "reprogramar" &&
    (campo === "paciente" || campo === "prestacion")
  )
    return resultado({
      general: `${texto}: este turno no se puede reprogramar, pero sí cancelar.`,
      releerCatalogos: true,
    });
  return resultado({
    porCampo: { [campo]: `${texto}.` },
    releerCatalogos: true,
  });
}

function interpretarValidacion(error: ErrorApi): ErrorTurnoInterpretado {
  const porCampo: Partial<Record<CampoTurno, string>> = {};
  let general: string | null = null;
  for (const { campo } of error.errores) {
    const destino = campo === null ? undefined : CAMPO_DE_LA_API[campo];
    if (destino === undefined) general = TEXTO_REVISAR_DATOS;
    else porCampo[destino] = TEXTO_REVISAR_CAMPO;
  }
  // El `msg` de la API no es apto para mostrar: solo se usan textos propios (spec frontend-cliente-http)
  return resultado({
    general: error.errores.length === 0 ? TEXTO_REVISAR_DATOS : general,
    porCampo,
  });
}

/**
 * Traduce un error de la API de turnos a lo que muestra el formulario (D12). Se traduce por
 * `codigo` porque `solapamiento` y `referencia_invalida` no traen `mensaje` y los demás están
 * escritos para desarrolladores.
 */
export function interpretarErrorTurno(
  error: ErrorApi,
  operacion: Operacion,
): ErrorTurnoInterpretado {
  switch (error.codigo) {
    case "solapamiento":
      return resultado({
        general: textoDeSolapamiento(error.datos.recursos),
        releerAgenda: true,
      });
    case "fuera_de_horario":
      return resultado({
        general:
          "El turno queda fuera del horario de atención del profesional.",
      });
    case "turno_en_bloqueo":
      return resultado({
        general:
          "El turno se superpone con un bloqueo de la agenda del profesional.",
        releerAgenda: true,
      });
    case "inicio_en_pasado":
      return resultado({
        porCampo: { hora: "El inicio no puede estar en el pasado." },
      });
    case "inicio_no_alineado":
      return resultado({
        porCampo: { hora: "El horario debe ser múltiplo de 5 minutos." },
      });
    case "duracion_invalida":
      return resultado({
        porCampo: {
          duracion: "La duración debe ser múltiplo de 5, de 5 a 480 minutos.",
        },
      });
    case "sillon_requerido":
      return resultado({
        porCampo: { sillon: "Esta prestación requiere un sillón." },
        releerCatalogos: true,
      });
    case "sillon_no_corresponde":
      return resultado({
        general: "Esta prestación no usa sillón.",
        releerCatalogos: true,
      });
    case "referencia_invalida":
      return interpretarReferencia(error, operacion);
    case "turno_ya_cancelado":
      return resultado({
        general: "Este turno ya fue cancelado.",
        turnoObsoleto: true,
        releerAgenda: true,
      });
    case "turno_ya_iniciado":
      return resultado({
        general: "Este turno ya inició: no se puede modificar.",
        turnoObsoleto: true,
        releerAgenda: true,
      });
    case "turno_inexistente":
      return resultado({
        general: "Este turno ya no existe.",
        turnoObsoleto: true,
        releerAgenda: true,
      });
    case "validacion":
      return interpretarValidacion(error);
    default:
      return resultado({
        general: error.status === 403 ? TEXTO_SIN_PERMISO : error.mensaje,
      });
  }
}
