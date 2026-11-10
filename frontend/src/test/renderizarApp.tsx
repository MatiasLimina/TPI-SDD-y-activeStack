import { act, render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  useLocation,
  useNavigate,
  useNavigationType,
  type NavigateFunction,
} from "react-router";

import { RutasApp } from "../App";
import { ProveedorSesion } from "../features/sesion/ProveedorSesion";
import { useClienteApi } from "../features/sesion/ProveedorSesion";
import type { ClienteApi } from "../shared/api/cliente";

/** Muestra la ruta actual, que `MemoryRouter` no expone en ninguna URL. */
function Ubicacion() {
  return <output data-testid="ubicacion">{useLocation().pathname}</output>;
}

/** Muestra cómo se llegó a la ruta actual (`POP`, `PUSH` o `REPLACE`): así se prueba que una redirección reemplaza la entrada del historial. */
function TipoNavegacion() {
  return <output data-testid="tipo-navegacion">{useNavigationType()}</output>;
}

/** Entrega a los tests la navegación programática, como la barra de direcciones. */
function SondaNavegacion({
  alObtener,
}: {
  alObtener: (navegar: NavigateFunction) => void;
}) {
  alObtener(useNavigate());
  return null;
}

/** Entrega a los tests el cliente HTTP de la sesión, el mismo que usarán las pantallas. */
function SondaCliente({
  alObtener,
}: {
  alObtener: (cliente: ClienteApi) => void;
}) {
  alObtener(useClienteApi());
  return null;
}

/**
 * La costura de los tests de pantallas: la aplicación entera en un `MemoryRouter` (D17).
 * `cliente` es el cliente HTTP de la sesión, para provocar pedidos que ninguna pantalla hace aún.
 */
export function renderizarApp(ruta: string = "/") {
  const user = vi.isFakeTimers()
    ? userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) })
    : userEvent.setup();
  let cliente: ClienteApi | null = null;
  let navegar: NavigateFunction | null = null;
  const vista = render(
    <MemoryRouter initialEntries={[ruta]}>
      <ProveedorSesion>
        <RutasApp />
        <SondaCliente alObtener={(obtenido) => (cliente = obtenido)} />
      </ProveedorSesion>
      <SondaNavegacion alObtener={(obtenida) => (navegar = obtenida)} />
      <Ubicacion />
      <TipoNavegacion />
    </MemoryRouter>,
  );
  if (cliente === null || navegar === null)
    throw new Error("Las sondas no obtuvieron los datos");
  const irA = navegar as NavigateFunction;
  return {
    user,
    cliente: cliente as ClienteApi,
    /** Navega como si se escribiera la ruta en la barra de direcciones. */
    navegarA: (ruta: string) => act(() => void irA(ruta)),
    ...vista,
  };
}
