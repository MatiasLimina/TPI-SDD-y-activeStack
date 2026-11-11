import type { ErrorApi } from "../../shared/api/errorApi";

export const TEXTO_REVISAR_CAMPO = "Revisá este campo.";
export const TEXTO_REVISAR_DATOS = "Revisá los datos ingresados.";
export const TEXTO_SIN_PERMISO_ESCRIBIR =
  "No tenés permiso para esta operación.";
export const TEXTO_SIN_PERMISO_LEER =
  "No tenés permiso para ver esta información.";
export const TEXTO_REGISTRO_INEXISTENTE = "Este registro ya no existe.";
export const TEXTO_COMPLETAR = "Completá este campo.";

/** Destino de un código propio de la pantalla: un campo del formulario, o el error general. */
export interface DestinoCodigo {
  campo?: string;
  texto: string;
}

export interface ConfigErrores {
  /** Campo de la API (el último tramo de `loc`) a campo del formulario. */
  campos: Readonly<Record<string, string>>;
  /** `recurso_duplicado`: texto por el `campo` que informa la API (se marca ese campo). */
  duplicado?: Readonly<Record<string, string>>;
  /** Otros códigos de la pantalla, con su destino y su texto literal (D11). */
  codigos?: Readonly<Record<string, DestinoCodigo>>;
}

export interface ErrorInterpretado {
  /** Error del formulario entero, anunciado como alerta. */
  general: string | null;
  porCampo: Record<string, string>;
  /** `404 recurso_inexistente`: el envío queda deshabilitado y se relee el listado. */
  registroInexistente: boolean;
}

function resultado(parcial: Partial<ErrorInterpretado>): ErrorInterpretado {
  return {
    general: null,
    porCampo: {},
    registroInexistente: false,
    ...parcial,
  };
}

function interpretarValidacion(
  error: ErrorApi,
  campos: Readonly<Record<string, string>>,
): ErrorInterpretado {
  const porCampo: Record<string, string> = {};
  let general: string | null = null;
  for (const { campo } of error.errores) {
    const destino = campo === null ? undefined : campos[campo];
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
 * Traduce un error de escritura de la API a lo que muestra el formulario (D11). Se traduce por
 * `codigo` porque `recurso_duplicado` y `franja_superpuesta` no traen `mensaje` y los demás
 * están escritos para desarrolladores.
 */
export function interpretarErrorGestion(
  error: ErrorApi,
  config: ConfigErrores,
): ErrorInterpretado {
  if (error.codigo === "validacion")
    return interpretarValidacion(error, config.campos);
  if (error.codigo === "recurso_duplicado") {
    const campoApi = String(error.datos.campo);
    const texto = config.duplicado?.[campoApi];
    if (texto !== undefined)
      return resultado({
        porCampo: { [config.campos[campoApi] ?? campoApi]: texto },
      });
  }
  if (error.status === 404 && error.codigo === "recurso_inexistente")
    return resultado({
      general: TEXTO_REGISTRO_INEXISTENTE,
      registroInexistente: true,
    });
  const propio =
    error.codigo === null ? undefined : config.codigos?.[error.codigo];
  if (propio !== undefined)
    return propio.campo === undefined
      ? resultado({ general: propio.texto })
      : resultado({ porCampo: { [propio.campo]: propio.texto } });
  return resultado({
    general: error.status === 403 ? TEXTO_SIN_PERMISO_ESCRIBIR : error.mensaje,
  });
}
