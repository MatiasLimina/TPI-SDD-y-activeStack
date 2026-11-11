import { useRef, useState } from "react";

import { comoErrorApi } from "../../shared/api/comoErrorApi";
import type { ErrorApi } from "../../shared/api/errorApi";
import {
  interpretarErrorGestion,
  TEXTO_COMPLETAR,
  type ConfigErrores,
} from "./erroresGestion";

/**
 * Estado de envío de un formulario o una confirmación de gestión (D4): errores por campo y
 * generales, envío en curso, registro inexistente y aviso de sin cambios. Los datos del
 * formulario viven en su propio estado y no se tocan ante un error (se conservan).
 */
export function useEnvioGestion(
  config: ConfigErrores,
  alRegistroInexistente?: () => void,
) {
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [obsoleto, setObsoleto] = useState(false);
  const [sinCambios, setSinCambios] = useState(false);
  const [errorApi, setErrorApi] = useState<ErrorApi | null>(null);
  // Un doble clic entre dos renders no debe mandar dos pedidos
  const enCurso = useRef(false);

  function limpiar() {
    setErrores({});
    setGeneral(null);
    setSinCambios(false);
    setErrorApi(null);
  }

  /** Reemplaza los errores previos: así se limpian al reenviar. `true` si no hay ninguno. */
  function validar(propios: Record<string, string>): boolean {
    limpiar();
    setErrores(propios);
    return Object.keys(propios).length === 0;
  }

  /** `Completá este campo.` en cada campo vacío, más los errores propios del formulario. */
  function validarObligatorios(
    vacios: readonly string[],
    otros: Record<string, string> = {},
  ): boolean {
    const faltantes: Record<string, string> = {};
    for (const campo of vacios) faltantes[campo] = TEXTO_COMPLETAR;
    return validar({ ...otros, ...faltantes });
  }

  function avisarSinCambios() {
    limpiar();
    setSinCambios(true);
  }

  /** Hace la escritura. `true` si salió bien; si no, muestra el error traducido. */
  async function enviar(
    escribir: () => Promise<unknown>,
    alFallar?: (error: ErrorApi) => void,
  ): Promise<boolean> {
    if (enCurso.current) return false;
    enCurso.current = true;
    limpiar();
    setEnviando(true);
    try {
      await escribir();
      return true;
    } catch (causa) {
      const error = comoErrorApi(causa);
      const interpretado = interpretarErrorGestion(error, config);
      setErrorApi(error);
      setErrores(interpretado.porCampo);
      setGeneral(interpretado.general);
      if (interpretado.registroInexistente) {
        setObsoleto(true);
        alRegistroInexistente?.();
      }
      alFallar?.(error);
      return false;
    } finally {
      enCurso.current = false;
      setEnviando(false);
    }
  }

  return {
    errores,
    general,
    enviando,
    obsoleto,
    sinCambios,
    /** Último error de la API, para que la pantalla lea sus `datos` (por ejemplo, `turnos`). */
    errorApi,
    validar,
    validarObligatorios,
    avisarSinCambios,
    enviar,
  };
}
