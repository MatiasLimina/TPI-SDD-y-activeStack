import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";

import App from "../App";

/** Muestra la ruta actual, que `MemoryRouter` no expone en ninguna URL. */
function Ubicacion() {
  return <output data-testid="ubicacion">{useLocation().pathname}</output>;
}

/** La costura de los tests de pantallas: `App` entero en un `MemoryRouter` (D17). */
export function renderizarApp(ruta: string = "/") {
  const user = vi.isFakeTimers()
    ? userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) })
    : userEvent.setup();
  const vista = render(
    <MemoryRouter initialEntries={[ruta]}>
      <App />
      <Ubicacion />
    </MemoryRouter>,
  );
  return { user, ...vista };
}
