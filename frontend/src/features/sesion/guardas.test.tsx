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
