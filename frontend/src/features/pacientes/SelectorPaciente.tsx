import { useEffect, useId, useState } from "react";

import { useClienteApi } from "../sesion/ProveedorSesion";
import type { PacienteBusqueda } from "./tipos";

interface PropsSelector {
  elegido: PacienteBusqueda | null;
  alElegir: (paciente: PacienteBusqueda) => void;
  alCambiar: () => void;
}

const ESPERA_MS = 300;
const MINIMO_CARACTERES = 2;
const LIMITE = 20;
const MAXIMO_ENTRADA = 100;

/**
 * Búsqueda de pacientes con `GET /pacientes` (D8): espera de 300 ms tras la última tecla,
 * mínimo de 2 caracteres sin contar espacios extremos y `limite=20`.
 */
export function SelectorPaciente({ elegido }: PropsSelector) {
  const cliente = useClienteApi();
  const idAviso = useId();
  const [texto, setTexto] = useState("");
  const consulta = texto.trim();
  const muyCorto = consulta.length > 0 && consulta.length < MINIMO_CARACTERES;

  useEffect(() => {
    if (consulta.length < MINIMO_CARACTERES) return;
    const temporizador = setTimeout(() => {
      const parametros = new URLSearchParams({
        q: consulta,
        limite: String(LIMITE),
      });
      void cliente.pedir("GET", `/pacientes?${parametros.toString()}`);
    }, ESPERA_MS);
    return () => clearTimeout(temporizador);
  }, [cliente, consulta]);

  if (elegido !== null) return null;
  return (
    <div>
      <label>
        Buscar paciente
        <input
          type="search"
          value={texto}
          maxLength={MAXIMO_ENTRADA}
          aria-describedby={muyCorto ? idAviso : undefined}
          onChange={(e) => setTexto(e.target.value)}
        />
      </label>
      {muyCorto && <p id={idAviso}>Escribí al menos 2 caracteres.</p>}
    </div>
  );
}
