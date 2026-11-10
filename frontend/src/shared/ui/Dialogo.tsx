import { useEffect, useId, useRef, type ReactNode } from "react";

import estilos from "./Dialogo.module.css";

interface PropsDialogo {
  abierto: boolean;
  titulo: string;
  /** Se llama cuando el diálogo se cierra por su cuenta (`Esc`): el padre debe darlo por cerrado. */
  onCerrar: () => void;
  children: ReactNode;
}

/**
 * `<dialog>` nativo abierto con `showModal()`: foco atrapado, `Esc` y `::backdrop` sin
 * dependencias. El estado `abierto` se sincroniza con el evento `close`, para que un `Esc`
 * no impida volver a abrirlo (D6).
 */
export function Dialogo({ abierto, titulo, onCerrar, children }: PropsDialogo) {
  const referencia = useRef<HTMLDialogElement>(null);
  const idTitulo = useId();

  useEffect(() => {
    const dialogo = referencia.current;
    if (dialogo === null) return;
    if (abierto && !dialogo.open) dialogo.showModal();
    if (!abierto && dialogo.open) dialogo.close();
  }, [abierto]);

  return (
    <dialog
      ref={referencia}
      className={estilos.dialogo}
      aria-labelledby={idTitulo}
      onClose={onCerrar}
    >
      <h2 id={idTitulo}>{titulo}</h2>
      {children}
    </dialog>
  );
}
