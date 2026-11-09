import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import App from "../App";

/** La costura de los tests de pantallas: `App` entero en un `MemoryRouter` (D17). */
export function renderizarApp(ruta: string = "/") {
  const user = vi.isFakeTimers()
    ? userEvent.setup({ advanceTimers: (ms) => vi.advanceTimersByTime(ms) })
    : userEvent.setup();
  const vista = render(
    <MemoryRouter initialEntries={[ruta]}>
      <App />
    </MemoryRouter>,
  );
  return { user, ...vista };
}
