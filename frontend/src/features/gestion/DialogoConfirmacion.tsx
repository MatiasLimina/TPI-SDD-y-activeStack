import type { ReactNode } from "react";

import { Dialogo } from "../../shared/ui/Dialogo";

interface PropsDialogoConfirmacion {
  titulo: string;
  abierto: boolean;
  textoConfirmar: string;
  enviando: boolean;
  /** El registro ya no existe: no hay nada que confirmar (D11). */
  deshabilitarConfirmacion?: boolean;
  alConfirmar: () => void;
  alCerrar: () => void;
  /** Error de la operación, en el mismo diálogo. */
  error?: ReactNode;
  /** Qué elemento se confirma y qué consecuencia tiene. */
  children: ReactNode;
}

/** Confirmación de una acción destructiva (desactivar, borrar), con el error en el mismo diálogo. */
export function DialogoConfirmacion({
  titulo,
  abierto,
  textoConfirmar,
  enviando,
  deshabilitarConfirmacion = false,
  alConfirmar,
  alCerrar,
  error,
  children,
}: PropsDialogoConfirmacion) {
  return (
    <Dialogo abierto={abierto} titulo={titulo} onCerrar={alCerrar}>
      {abierto && (
        <div>
          {error != null && <div role="alert">{error}</div>}
          {children}
          <button
            type="button"
            disabled={enviando || deshabilitarConfirmacion}
            onClick={alConfirmar}
          >
            {textoConfirmar}
          </button>
          <button type="button" onClick={alCerrar}>
            Volver
          </button>
        </div>
      )}
    </Dialogo>
  );
}
