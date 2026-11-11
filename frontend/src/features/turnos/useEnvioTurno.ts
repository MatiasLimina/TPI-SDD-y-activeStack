import { useRef, useState } from "react";

import type { ErrorApi } from "../../shared/api/errorApi";
import { comoErrorApi } from "../../shared/api/comoErrorApi";
import {
  interpretarErrorTurno,
  type CampoTurno,
  type Operacion,
} from "./erroresTurno";

export type ErroresPorCampo = Partial<Record<CampoTurno, string>>;

/** Selectores cuyo valor rechazado sigue como opción hasta que se cambie (P5). */
type CampoDeRecurso = "profesional" | "prestacion" | "sillon";

interface Dependencias {
  alReleerAgenda: () => void;
  /** Devuelve el error si la relectura falla (D7). */
  alReleerCatalogos: () => Promise<ErrorApi | null>;
}

/**
 * Estado de envío compartido por los formularios de turno: errores por campo y generales,
 * envío en curso, turno obsoleto, valor rechazado y sillón forzado. Los datos del formulario
 * viven en su propio estado y no se tocan ante un error.
 */
export function useEnvioTurno(
  operacion: Operacion,
  { alReleerAgenda, alReleerCatalogos }: Dependencias,
) {
  const [errores, setErrores] = useState<ErroresPorCampo>({});
  const [generales, setGenerales] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  // Número del último envío: la relectura de uno anterior no toca los errores del vigente
  const ultimoEnvio = useRef(0);
  const [turnoObsoleto, setTurnoObsoleto] = useState(false);
  // La prestación para la que la API dijo que hace falta sillón aunque el catálogo no lo pida
  const [sillonForzadoPara, setSillonForzadoPara] = useState<string | null>(
    null,
  );
  const [rechazado, setRechazado] = useState<
    Partial<Record<CampoDeRecurso, string>>
  >({});

  /** El valor rechazado se ofrece mientras siga elegido. */
  function conservar(campo: CampoDeRecurso, elegido: string): string[] {
    return rechazado[campo] !== undefined && rechazado[campo] === elegido
      ? [elegido]
      : [];
  }

  /** El sillón se muestra para esta prestación aunque el catálogo no lo pida. */
  function sillonForzado(prestacionId: string): boolean {
    return sillonForzadoPara !== null && sillonForzadoPara === prestacionId;
  }

  /** Reemplaza los errores previos: así se limpian al reenviar. */
  function mostrarObligatorios(faltantes: ErroresPorCampo): boolean {
    setErrores(faltantes);
    setGenerales([]);
    return Object.keys(faltantes).length === 0;
  }

  /**
   * Hace la escritura. Devuelve `true` si salió bien; si no, muestra el error traducido y
   * relee lo que el error revela desactualizado (agenda, catálogos).
   */
  async function enviar(
    escribir: () => Promise<unknown>,
    elegidos: Record<CampoDeRecurso, string>,
  ): Promise<boolean> {
    ultimoEnvio.current += 1;
    const mio = ultimoEnvio.current;
    setEnviando(true);
    try {
      await escribir();
      return true;
    } catch (causa) {
      const error = comoErrorApi(causa);
      const interpretado = interpretarErrorTurno(error, operacion);
      setErrores(interpretado.porCampo);
      setGenerales(interpretado.general === null ? [] : [interpretado.general]);
      // Solo sillon_requerido revela que el catálogo está desactualizado; vale para esa prestación
      if (error.codigo === "sillon_requerido")
        setSillonForzadoPara(elegidos.prestacion);
      const referencia = error.datos.referencia;
      if (
        error.codigo === "referencia_invalida" &&
        (referencia === "profesional" ||
          referencia === "prestacion" ||
          referencia === "sillon")
      )
        setRechazado({ [referencia]: elegidos[referencia] });
      if (interpretado.turnoObsoleto) setTurnoObsoleto(true);
      if (interpretado.releerAgenda) alReleerAgenda();
      setEnviando(false);
      if (interpretado.releerCatalogos) {
        const falla = await alReleerCatalogos();
        // El formulario sigue abierto: la falla se suma como error general (D7, P14)
        if (falla !== null && mio === ultimoEnvio.current)
          setGenerales((anteriores) => [...anteriores, falla.mensaje]);
      }
      return false;
    }
  }

  return {
    errores,
    generales,
    enviando,
    turnoObsoleto,
    sillonForzado,
    conservar,
    mostrarObligatorios,
    mostrarGenerales: setGenerales,
    enviar,
  };
}
