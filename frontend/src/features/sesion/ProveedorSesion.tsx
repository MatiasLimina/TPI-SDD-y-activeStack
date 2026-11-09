import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { crearClienteApi, type ClienteApi } from "../../shared/api/cliente";
import { guardarToken } from "./almacenamiento";
import { interpretarToken, type Claims } from "./claims";

export interface Sesion {
  token: string;
  claims: Claims;
}

interface ValorSesion {
  sesion: Sesion | null;
  cliente: ClienteApi;
  /** Crea la sesión con el token del login; `false` si el token no sirve. */
  iniciarSesion: (token: string) => boolean;
}

const ContextoSesion = createContext<ValorSesion | null>(null);

function crearTokenActual() {
  let valor: string | null = null;
  return {
    leer: () => valor,
    establecer: (token: string | null) => {
      valor = token;
    },
  };
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [sesion, setSesion] = useState<Sesion | null>(null);
  // Token de la sesión actual, legible de forma síncrona por el cliente HTTP (D4)
  const [actual] = useState(crearTokenActual);

  const cliente = useMemo(
    () =>
      crearClienteApi({
        obtenerToken: actual.leer,
        alNoAutenticado: () => {},
      }),
    [actual],
  );

  const valor = useMemo<ValorSesion>(
    () => ({
      sesion,
      cliente,
      iniciarSesion: (token) => {
        const resultado = interpretarToken(token);
        if (resultado.estado === "invalido") return false;
        guardarToken(token);
        actual.establecer(token);
        setSesion({ token, claims: resultado.claims });
        return true;
      },
    }),
    [sesion, cliente, actual],
  );
  return (
    <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
  );
}

export function useSesion(): ValorSesion {
  const valor = useContext(ContextoSesion);
  if (valor === null) throw new Error("Falta el ProveedorSesion");
  return valor;
}

export function useClienteApi(): ClienteApi {
  return useSesion().cliente;
}
