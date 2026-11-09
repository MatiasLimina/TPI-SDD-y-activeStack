import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";

import { RutasApp } from "../App";
import { ProveedorSesion } from "../features/sesion/ProveedorSesion";
import { useClienteApi } from "../features/sesion/ProveedorSesion";
import type { ClienteApi } from "../shared/api/cliente";

/** Muestra la ruta actual, que `MemoryRouter` no expone en ninguna URL. */
function Ubicacion() {
  return <output data-testid="ubicacion">{useLocation().pathname}</output>;
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
  const vista = render(
    <MemoryRouter initialEntries={[ruta]}>
      <ProveedorSesion>
        <RutasApp />
        <SondaCliente alObtener={(obtenido) => (cliente = obtenido)} />
      </ProveedorSesion>
      <Ubicacion />
    </MemoryRouter>,
  );
  if (cliente === null) throw new Error("La sonda no obtuvo el cliente");
  return { user, cliente: cliente as ClienteApi, ...vista };
}
