import { useId, type ReactNode } from "react";

interface AtributosCampo {
  id: string;
  "aria-invalid": boolean;
  "aria-describedby": string | undefined;
}

interface PropsCampo {
  etiqueta: string;
  /** Error del campo: se asocia al control y lo marca como inválido (D17). */
  error?: string | undefined;
  /** Ayuda del campo; si hay error, el control se describe solo con el error. */
  ayuda?: string | undefined;
  children: (atributos: AtributosCampo) => ReactNode;
}

/** Etiqueta, control, ayuda y error de un campo de formulario, asociados por accesibilidad. */
export function Campo({ etiqueta, error, ayuda, children }: PropsCampo) {
  const id = useId();
  const idMensaje = `${id}-mensaje`;
  const mensaje = error ?? ayuda;
  return (
    <div>
      <label htmlFor={id}>{etiqueta}</label>
      {children({
        id,
        "aria-invalid": error !== undefined,
        "aria-describedby": mensaje === undefined ? undefined : idMensaje,
      })}
      {mensaje !== undefined && <p id={idMensaje}>{mensaje}</p>}
    </div>
  );
}
