import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { crearClienteApi, type ClienteApi } from "../../shared/api/cliente";
import { CLAVE_TOKEN, eliminarToken, guardarToken } from "./almacenamiento";
import { interpretarToken, type Claims } from "./claims";

export interface Sesion {
  token: string;
  claims: Claims;
}

interface ValorSesion {
  sesion: Sesion | null;
  /** `true` si la sesión anterior terminó por vencimiento (aviso en `/login`). */
  avisoVencida: boolean;
  cliente: ClienteApi;
  /** Crea la sesión con el token del login; `false` si el token no sirve. */
  iniciarSesion: (token: string) => boolean;
}

const ContextoSesion = createContext<ValorSesion | null>(null);

/** Token de la sesión actual, legible de forma síncrona por el cliente HTTP (D4). */
function crearTokenActual(inicial: string | null) {
  let valor = inicial;
  return {
    leer: () => valor,
    establecer: (token: string | null) => {
      valor = token;
    },
  };
}

/** Solo lee: el token se descarta en un efecto, porque el inicializador puede correr dos veces. */
function leerSesionGuardada(): {
  sesion: Sesion | null;
  avisoVencida: boolean;
} {
  const token = sessionStorage.getItem(CLAVE_TOKEN);
  if (token === null) return { sesion: null, avisoVencida: false };
  const resultado = interpretarToken(token);
  if (resultado.estado === "vigente") {
    return { sesion: { token, claims: resultado.claims }, avisoVencida: false };
  }
  return { sesion: null, avisoVencida: resultado.estado === "vencido" };
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const [inicial] = useState(leerSesionGuardada);
  const [sesion, setSesion] = useState<Sesion | null>(inicial.sesion);
  const [avisoVencida, setAvisoVencida] = useState(inicial.avisoVencida);
  const [actual] = useState(() =>
    crearTokenActual(inicial.sesion?.token ?? null),
  );

  useEffect(() => {
    if (inicial.sesion === null) eliminarToken();
  }, [inicial]);

  const cliente = useMemo(
    () =>
      crearClienteApi({ obtenerToken: actual.leer, alNoAutenticado: () => {} }),
    [actual],
  );

  const valor = useMemo<ValorSesion>(
    () => ({
      sesion,
      avisoVencida,
      cliente,
      iniciarSesion: (token) => {
        const resultado = interpretarToken(token);
        if (resultado.estado !== "vigente") return false;
        guardarToken(token);
        actual.establecer(token);
        setAvisoVencida(false);
        setSesion({ token, claims: resultado.claims });
        return true;
      },
    }),
    [sesion, avisoVencida, cliente, actual],
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
