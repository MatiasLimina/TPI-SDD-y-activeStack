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
 * dependencias; `Esc` en un campo de búsqueda también cierra de una vez. El estado `abierto` se sincroniza con el evento `close`, para que un `Esc`
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
      onKeyDownCapture={(e) => {
        // Chrome usa el primer Esc de un `<input type="search">` para borrar el texto y recién el
        // segundo cierra el diálogo. Se evita el borrado y se cierra con una sola pulsación
        const objetivo = e.target;
        if (
          e.key === "Escape" &&
          objetivo instanceof HTMLInputElement &&
          objetivo.type === "search"
        ) {
          e.preventDefault();
          e.currentTarget.close();
        }
      }}
    >
      <h2 id={idTitulo}>{titulo}</h2>
      {children}
    </dialog>
  );
}
