import { screen } from "@testing-library/react";

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
  it("muestra a la recepcionista su rol y los enlaces a la agenda y a la configuración", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));

    renderizarApp("/agenda");

    expect(screen.getByText("Recepcionista")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agenda" })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Configuración" }),
    ).toBeInTheDocument();
  });

  it("muestra al odontólogo su rol, la agenda y ningún enlace a la configuración", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeOdontologo(VIGENTE));

    renderizarApp("/agenda");

    expect(screen.getByText("Odontólogo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agenda" })).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Configuración" }),
    ).not.toBeInTheDocument();
  });

  it("el login no usa el layout: sin navegación ni cierre de sesión", () => {
    renderizarApp("/login");

    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cerrar sesión" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Recepcionista")).not.toBeInTheDocument();
  });

  it("la pantalla provisoria de configuración no hace pedidos a la API", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));
    const api = instalarApiFalsa();

    renderizarApp("/configuracion");

    expect(ubicacion()).toBe("/configuracion");
    expect(
      screen.getByRole("heading", { name: "Configuración" }),
    ).toBeInTheDocument();
    expect(api.fetch).not.toHaveBeenCalled();
  });

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
