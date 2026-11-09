import { screen } from "@testing-library/react";

import { instalarFetchFalso } from "../../test/fetchFalso";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import {
  AHORA_SEGUNDOS,
  tokenDeOdontologo,
  tokenDeRecepcionista,
} from "../../test/tokens";
import { CLAVE_TOKEN } from "./almacenamiento";

usarRelojFijo();

function ubicacion(): string {
  return screen.getByTestId("ubicacion").textContent ?? "";
}

const VIGENTE = AHORA_SEGUNDOS + 3600;

describe("Guarda de autenticación", () => {
  it.each(["/agenda", "/configuracion", "/"])(
    "sin sesión, %s lleva a /login",
    (ruta) => {
      instalarFetchFalso();

      renderizarApp(ruta);

      expect(ubicacion()).toBe("/login");
      expect(screen.getByLabelText("Email")).toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { name: "Agenda" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { name: "Sin permiso" }),
      ).not.toBeInTheDocument();
    },
  );
});

describe("Usuario con sesión en rutas de entrada", () => {
  it.each([
    ["recepcionista", "/login", tokenDeRecepcionista(VIGENTE)],
    ["odontologo", "/", tokenDeOdontologo(VIGENTE)],
    ["recepcionista", "/", tokenDeRecepcionista(VIGENTE)],
    ["odontologo", "/login", tokenDeOdontologo(VIGENTE)],
  ])(
    "con sesión de %s, %s lleva a /agenda sin mostrar el formulario",
    (_rol, ruta, token) => {
      sessionStorage.setItem(CLAVE_TOKEN, token);

      renderizarApp(ruta);

      expect(ubicacion()).toBe("/agenda");
      expect(
        screen.getByRole("heading", { name: "Agenda" }),
      ).toBeInTheDocument();
      expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
    },
  );
});

describe("Guarda por rol", () => {
  it("la recepcionista ve el contenido de /configuracion", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));

    renderizarApp("/configuracion");

    expect(
      screen.getByRole("heading", { name: "Configuración" }),
    ).toBeInTheDocument();
    expect(ubicacion()).toBe("/configuracion");
  });

  it("el odontólogo ve la falta de permiso, con la URL intacta y el token guardado", () => {
    const token = tokenDeOdontologo(VIGENTE);
    sessionStorage.setItem(CLAVE_TOKEN, token);

    renderizarApp("/configuracion");

    expect(
      screen.getByRole("heading", { name: "Sin permiso" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Configuración" }),
    ).not.toBeInTheDocument();
    expect(ubicacion()).toBe("/configuracion");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
  });

  it("desde la falta de permiso, el enlace lleva al inicio del odontólogo", async () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeOdontologo(VIGENTE));
    const { user } = renderizarApp("/configuracion");

    await user.click(screen.getByRole("link", { name: "Volver al inicio" }));

    expect(ubicacion()).toBe("/agenda");
    expect(screen.getByRole("heading", { name: "Agenda" })).toBeInTheDocument();
  });

  it("el odontólogo ve el contenido de /agenda", () => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeOdontologo(VIGENTE));

    renderizarApp("/agenda");

    expect(screen.getByRole("heading", { name: "Agenda" })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Sin permiso" }),
    ).not.toBeInTheDocument();
  });
});

describe("Ruta inexistente", () => {
  it("sin sesión muestra la página no encontrada, sin redirigir", () => {
    renderizarApp("/no-existe");

    expect(
      screen.getByRole("heading", { name: "Página no encontrada" }),
    ).toBeInTheDocument();
    expect(ubicacion()).toBe("/no-existe");
  });

  it("sin sesión, el enlace a / lleva al login", async () => {
    const { user } = renderizarApp("/no-existe");

    await user.click(screen.getByRole("link", { name: "Ir al inicio" }));

    expect(ubicacion()).toBe("/login");
  });

  it.each([
    ["recepcionista", tokenDeRecepcionista(VIGENTE)],
    ["odontologo", tokenDeOdontologo(VIGENTE)],
  ])(
    "con sesión de %s, el enlace a / lleva a su inicio",
    async (_rol, token) => {
      sessionStorage.setItem(CLAVE_TOKEN, token);
      const { user } = renderizarApp("/no-existe");
      expect(
        screen.getByRole("heading", { name: "Página no encontrada" }),
      ).toBeInTheDocument();

      await user.click(screen.getByRole("link", { name: "Ir al inicio" }));

      expect(ubicacion()).toBe("/agenda");
      expect(
        screen.getByRole("heading", { name: "Agenda" }),
      ).toBeInTheDocument();
    },
  );
});
