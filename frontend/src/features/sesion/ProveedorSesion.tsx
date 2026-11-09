import { createContext, useContext, useMemo, type ReactNode } from "react";

import { crearClienteApi, type ClienteApi } from "../../shared/api/cliente";

interface ValorSesion {
  cliente: ClienteApi;
}

const ContextoSesion = createContext<ValorSesion | null>(null);

export function ProveedorSesion({ children }: { children: ReactNode }) {
  const valor = useMemo<ValorSesion>(
    () => ({
      cliente: crearClienteApi({
        obtenerToken: () => null,
        alNoAutenticado: () => {},
      }),
    }),
    [],
  );
  return (
    <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
  );
}

function useValorSesion(): ValorSesion {
  const valor = useContext(ContextoSesion);
  if (valor === null) throw new Error("Falta el ProveedorSesion");
  return valor;
}

export function useClienteApi(): ClienteApi {
  return useValorSesion().cliente;
}
