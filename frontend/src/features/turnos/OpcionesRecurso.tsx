interface Recurso {
  id: string;
}

interface PropsOpciones<R extends Recurso> {
  catalogo: R[];
  estaActivo: (recurso: R) => boolean;
  nombreDe: (recurso: R) => string;
  /** Texto de una opción cuyo id ya no figura en el catálogo. */
  nombreAusente: string;
  /** Ids que se siguen ofreciendo aunque no estén activos: el rechazado o el actual del turno. */
  conservar: string[];
}

/**
 * Opciones de un selector de formulario: solo los recursos activos (D7, D9), más los ids que se
 * deben seguir ofreciendo. Un inactivo que se conserva lleva `(inactivo)`; uno que ya no figura
 * en el catálogo, el texto genérico y sin la marca.
 */
export function OpcionesRecurso<R extends Recurso>({
  catalogo,
  estaActivo,
  nombreDe,
  nombreAusente,
  conservar,
}: PropsOpciones<R>) {
  const activos = catalogo.filter(estaActivo);
  const aparte = [...new Set(conservar)].filter(
    (id) => !activos.some((r) => r.id === id),
  );
  return (
    <>
      {activos.map((r) => (
        <option key={r.id} value={r.id}>
          {nombreDe(r)}
        </option>
      ))}
      {aparte.map((id) => {
        const recurso = catalogo.find((r) => r.id === id);
        return (
          <option key={id} value={id}>
            {recurso === undefined
              ? nombreAusente
              : `${nombreDe(recurso)} (inactivo)`}
          </option>
        );
      })}
    </>
  );
}
