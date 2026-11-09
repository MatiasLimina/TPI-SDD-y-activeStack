import { useRef, useState, type FormEvent } from "react";

import { useClienteApi } from "../features/sesion/ProveedorSesion";
import { ErrorApi, MENSAJE_GENERICO } from "../shared/api/errorApi";

export default function PaginaLogin() {
  const cliente = useClienteApi();
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const enCurso = useRef(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (enCurso.current) return;
    const datos = new FormData(evento.currentTarget);
    enCurso.current = true;
    setEnviando(true);
    setError(null);
    try {
      await cliente.pedir("POST", "/auth/login", {
        email: String(datos.get("email")),
        password: String(datos.get("password")),
      });
    } catch (causa) {
      setError(causa instanceof ErrorApi ? causa.mensaje : MENSAJE_GENERICO);
    } finally {
      enCurso.current = false;
      setEnviando(false);
    }
  }

  return (
    <main>
      <h1>Turnos y Agenda</h1>
      <form onSubmit={(evento) => void enviar(evento)}>
        <label>
          Email
          <input
            name="email"
            type="text"
            inputMode="email"
            autoComplete="username"
            required
          />
        </label>
        <label>
          Contraseña
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
        </label>
        {error !== null && <p role="alert">{error}</p>}
        <button type="submit" disabled={enviando}>
          {enviando ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
    </main>
  );
}
