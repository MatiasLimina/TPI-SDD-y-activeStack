import { useEffect, useId, useState } from "react";

import type { ErrorApi } from "../../shared/api/errorApi";
import { comoErrorApi } from "../agenda/errores";
import { useClienteApi } from "../sesion/ProveedorSesion";
import type { PacienteBusqueda } from "./tipos";

interface PropsSelector {
  elegido: PacienteBusqueda | null;
  alElegir: (paciente: PacienteBusqueda) => void;
  alCambiar: () => void;
  /** Error de campo del formulario (por ejemplo, `El paciente está inactivo.`). */
  error?: string;
}

const ESPERA_MS = 300;
const MINIMO_CARACTERES = 2;
const LIMITE = 20;
const MAXIMO_ENTRADA = 100;

type Respuesta =
  | { consulta: string; pacientes: PacienteBusqueda[] }
  | { consulta: string; error: ErrorApi };

/**
 * Búsqueda de pacientes con `GET /pacientes` (D8): espera de 300 ms tras la última tecla,
 * mínimo de 2 caracteres sin contar espacios extremos y `limite=20`. Campo de búsqueda más
 * lista de botones: se completa con Tab y Enter. Los inactivos se ven, pero no se eligen.
 */
export function SelectorPaciente({
  elegido,
  alElegir,
  alCambiar,
  error,
}: PropsSelector) {
  const cliente = useClienteApi();
  const idAviso = useId();
  const idError = useId();
  const [texto, setTexto] = useState("");
  const [respuesta, setRespuesta] = useState<Respuesta | null>(null);
  const consulta = texto.trim();
  const muyCorto = consulta.length > 0 && consulta.length < MINIMO_CARACTERES;

  useEffect(() => {
    if (consulta.length < MINIMO_CARACTERES) return;
    // Solo escribe el estado la búsqueda vigente: una respuesta tardía de otro texto se descarta
    let vigente = true;
    const temporizador = setTimeout(() => {
      const parametros = new URLSearchParams({
        q: consulta,
        limite: String(LIMITE),
      });
      cliente
        .pedir<PacienteBusqueda[]>("GET", `/pacientes?${parametros.toString()}`)
        .then((pacientes) => {
          if (vigente) setRespuesta({ consulta, pacientes });
        })
        .catch((causa: unknown) => {
          if (vigente) setRespuesta({ consulta, error: comoErrorApi(causa) });
        });
    }, ESPERA_MS);
    return () => {
      vigente = false;
      clearTimeout(temporizador);
    };
  }, [cliente, consulta]);

  if (elegido !== null) {
    return (
      <div>
        <p>
          {elegido.apellido}, {elegido.nombre}
        </p>
        <button
          type="button"
          onClick={alCambiar}
          aria-describedby={error !== undefined ? idError : undefined}
        >
          Cambiar paciente
        </button>
        {error !== undefined && <p id={idError}>{error}</p>}
      </div>
    );
  }

  // Los resultados se muestran solo si son del texto actual
  const actual = respuesta?.consulta === consulta ? respuesta : null;
  return (
    <div>
      <label>
        Buscar paciente
        <input
          type="search"
          value={texto}
          maxLength={MAXIMO_ENTRADA}
          aria-invalid={error !== undefined}
          aria-describedby={
            [muyCorto ? idAviso : null, error !== undefined ? idError : null]
              .filter((id) => id !== null)
              .join(" ") || undefined
          }
          onChange={(e) => setTexto(e.target.value)}
          // Enter en el campo no debe enviar el formulario que lo contiene
          onKeyDown={(e) => {
            if (e.key === "Enter") e.preventDefault();
          }}
        />
      </label>
      {muyCorto && <p id={idAviso}>Escribí al menos 2 caracteres.</p>}
      {error !== undefined && <p id={idError}>{error}</p>}
      {actual !== null && "error" in actual && (
        <p role="alert">{actual.error.mensaje}</p>
      )}
      {actual !== null && "pacientes" in actual && (
        <Resultados pacientes={actual.pacientes} alElegir={alElegir} />
      )}
    </div>
  );
}

function Resultados({
  pacientes,
  alElegir,
}: {
  pacientes: PacienteBusqueda[];
  alElegir: (paciente: PacienteBusqueda) => void;
}) {
  if (pacientes.length === 0)
    return <p role="status">No se encontraron pacientes.</p>;
  return (
    <div role="status">
      <ul>
        {pacientes.map((paciente) => (
          <li key={paciente.id}>
            <button
              type="button"
              disabled={!paciente.activo}
              onClick={() => alElegir(paciente)}
            >
              {paciente.apellido}, {paciente.nombre}{" "}
              <span>{paciente.documento}</span>
              {!paciente.activo && <strong>Inactivo</strong>}
            </button>
          </li>
        ))}
      </ul>
      {pacientes.length >= LIMITE && (
        <p>Hay más resultados: refiná la búsqueda.</p>
      )}
    </div>
  );
}
