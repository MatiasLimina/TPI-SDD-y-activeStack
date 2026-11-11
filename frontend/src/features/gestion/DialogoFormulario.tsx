import type { FormEvent, ReactNode } from "react";

import { Dialogo } from "../../shared/ui/Dialogo";

interface PropsDialogoFormulario {
  titulo: string;
  abierto: boolean;
  alCerrar: () => void;
  alEnviar: () => void;
  enviando: boolean;
  /** El registro ya no existe: el envío queda deshabilitado (D11). */
  deshabilitarEnvio?: boolean;
  textoEnviar?: string;
  /** Error del formulario entero, anunciado como alerta. */
  errorGeneral?: ReactNode;
  /** `No hiciste cambios.` con rol `status` (D5). */
  sinCambios?: boolean;
  children: ReactNode;
}

/**
 * Formulario de alta o edición en un diálogo modal (D4): `noValidate` (la API decide, DD-34 P8),
 * envío deshabilitado mientras se envía y `Volver` sin pedidos. El contenido solo se monta con
 * el diálogo abierto, así que cada apertura empieza con el estado limpio.
 */
export function DialogoFormulario({
  titulo,
  abierto,
  alCerrar,
  alEnviar,
  enviando,
  deshabilitarEnvio = false,
  textoEnviar = "Guardar",
  errorGeneral,
  sinCambios = false,
  children,
}: PropsDialogoFormulario) {
  function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!enviando && !deshabilitarEnvio) alEnviar();
  }

  return (
    <Dialogo abierto={abierto} titulo={titulo} onCerrar={alCerrar}>
      {abierto && (
        <form noValidate onSubmit={enviar}>
          {errorGeneral != null && <div role="alert">{errorGeneral}</div>}
          {sinCambios && <p role="status">No hiciste cambios.</p>}
          {children}
          <button type="submit" disabled={enviando || deshabilitarEnvio}>
            {textoEnviar}
          </button>
          <button type="button" onClick={alCerrar}>
            Volver
          </button>
        </form>
      )}
    </Dialogo>
  );
}
