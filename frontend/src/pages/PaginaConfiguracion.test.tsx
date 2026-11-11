import { screen } from "@testing-library/react";

import { CLAVE_TOKEN } from "../features/sesion/almacenamiento";
import { instalarApiFalsa } from "../test/apiFalsa";
import { renderizarApp } from "../test/renderizarApp";
import { usarRelojFijo } from "../test/reloj";
import { AHORA_SEGUNDOS, tokenDeRecepcionista } from "../test/tokens";

usarRelojFijo();

beforeEach(() => {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
  );
});

function ubicacion(): string {
  return screen.getByTestId("ubicacion").textContent ?? "";
}

function navegacionInterna() {
  return screen.getByRole("navigation", {
    name: "Secciones de la configuración",
  });
}

describe("Secciones de la configuración", () => {
  it("/configuracion reemplaza la entrada del historial por /configuracion/profesionales", async () => {
    const api = instalarApiFalsa();

    renderizarApp("/configuracion");

    expect(ubicacion()).toBe("/configuracion/profesionales");
    expect(screen.getByTestId("tipo-navegacion")).toHaveTextContent("REPLACE");
    expect(
      screen.getByRole("heading", { level: 1, name: "Configuración" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "Profesionales" }),
    ).toBeInTheDocument();
    expect(api.pedidos("GET /profesionales").length).toBeGreaterThan(0);
  });

  it("ofrece los cuatro enlaces y marca la sección actual", () => {
    instalarApiFalsa();

    renderizarApp("/configuracion/sillones");

    const nav = navegacionInterna();
    const nombres = Array.from(nav.querySelectorAll("a")).map(
      (a) => a.textContent,
    );
    expect(nombres).toEqual([
      "Profesionales",
      "Sillones",
      "Prestaciones",
      "Horarios",
    ]);
    expect(screen.getByRole("link", { name: "Sillones" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.getByRole("link", { name: "Profesionales" }),
    ).not.toHaveAttribute("aria-current");
  });

  it("Prestaciones lleva a su ruta, queda marcada y pide GET /prestaciones", async () => {
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/configuracion/profesionales");
    await screen.findByRole("heading", { name: "Profesionales" });

    await user.click(screen.getByRole("link", { name: "Prestaciones" }));

    expect(ubicacion()).toBe("/configuracion/prestaciones");
    expect(screen.getByRole("link", { name: "Prestaciones" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await screen.findByRole("heading", { name: "Prestaciones" });
    expect(api.pedidos("GET /prestaciones").length).toBeGreaterThan(0);
  });

  it("una sección inexistente muestra la página no encontrada", () => {
    instalarApiFalsa();

    renderizarApp("/configuracion/usuarios");

    expect(
      screen.getByRole("heading", { name: "Página no encontrada" }),
    ).toBeInTheDocument();
    expect(ubicacion()).toBe("/configuracion/usuarios");
  });
});
