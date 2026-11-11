import { screen, waitFor } from "@testing-library/react";

import { CLAVE_TOKEN } from "../../features/sesion/almacenamiento";
import { instalarApiFalsa } from "../../test/apiFalsa";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import {
  AHORA_SEGUNDOS,
  tokenDeOdontologo,
  tokenDeRecepcionista,
} from "../../test/tokens";

usarRelojFijo();

// La agenda hace pedidos al montarse: la API falsa los responde vacíos
beforeEach(() => {
  instalarApiFalsa();
});

const VIGENTE = AHORA_SEGUNDOS + 3600;
const AVISO_VENCIDA = "Tu sesión venció. Iniciá sesión de nuevo.";

function ubicacion(): string {
  return screen.getByTestId("ubicacion").textContent ?? "";
}

describe("Layout de la aplicación", () => {
  it("muestra a la recepcionista su rol y los enlaces a agenda, configuración, pacientes y bloqueos", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));

    renderizarApp("/agenda");

    expect(screen.getByText("Recepcionista")).toBeInTheDocument();
    for (const nombre of ["Agenda", "Configuración", "Pacientes", "Bloqueos"])
      expect(screen.getByRole("link", { name: nombre })).toBeInTheDocument();
  });

  it("muestra al odontólogo su rol, agenda y bloqueos, y ningún enlace a configuración ni a pacientes", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeOdontologo(VIGENTE));

    renderizarApp("/agenda");

    expect(screen.getByText("Odontólogo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agenda" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Bloqueos" })).toBeInTheDocument();
    for (const nombre of ["Configuración", "Pacientes"])
      expect(
        screen.queryByRole("link", { name: nombre }),
      ).not.toBeInTheDocument();
  });

  it("marca la sección actual como página actual, también dentro de una subruta", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));

    renderizarApp("/configuracion/sillones");

    expect(screen.getByRole("link", { name: "Configuración" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Agenda" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("en la agenda, solo el enlace Agenda es la página actual", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeOdontologo(VIGENTE));

    renderizarApp("/bloqueos");

    expect(screen.getByRole("link", { name: "Bloqueos" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Agenda" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("el login no usa el layout: sin navegación ni cierre de sesión", () => {
    renderizarApp("/login");

    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cerrar sesión" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Recepcionista")).not.toBeInTheDocument();
  });

  it.each(["/configuracion", "/pacientes", "/bloqueos"])(
    "ninguna ruta del layout es provisoria: %s pide sus datos a la API",
    async (ruta) => {
      sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));
      const api = instalarApiFalsa();
      api.responder("GET /pacientes", { status: 200, cuerpo: [] });

      renderizarApp(ruta);

      await waitFor(() => expect(api.fetch).toHaveBeenCalled());
      expect(screen.queryByText(/Pantalla provisoria/)).not.toBeInTheDocument();
    },
  );

  it("cerrar sesión elimina el token, lleva a /login sin aviso y volver a /agenda pide login", async () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));
    const { user, navegarA } = renderizarApp("/agenda");

    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();

    await navegarA("/agenda");

    expect(ubicacion()).toBe("/login");
    expect(
      screen.queryByRole("heading", { name: "Agenda" }),
    ).not.toBeInTheDocument();
  });
});
