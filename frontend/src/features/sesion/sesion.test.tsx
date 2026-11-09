import { screen } from "@testing-library/react";

import { instalarFetchFalso } from "../../test/fetchFalso";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import {
  AHORA_SEGUNDOS,
  crearToken,
  tokenDeOdontologo,
  tokenDeRecepcionista,
} from "../../test/tokens";
import { CLAVE_TOKEN } from "./almacenamiento";

usarRelojFijo();

const AVISO_VENCIDA = "Tu sesión venció. Iniciá sesión de nuevo.";

function ubicacion(): string {
  return screen.getByTestId("ubicacion").textContent ?? "";
}

describe("Arranque con un token guardado", () => {
  it.each([
    ["recepcionista", tokenDeRecepcionista(AHORA_SEGUNDOS + 60)],
    ["odontologo", tokenDeOdontologo(AHORA_SEGUNDOS + 60)],
  ])("un token vigente de %s conserva la sesión en /agenda", (_rol, token) => {
    sessionStorage.setItem(CLAVE_TOKEN, token);
    const falso = instalarFetchFalso();

    renderizarApp("/agenda");

    expect(screen.getByRole("heading", { name: "Agenda" })).toBeInTheDocument();
    expect(ubicacion()).toBe("/agenda");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
    expect(falso).not.toHaveBeenCalled();
  });

  it.each([
    ["con exp pasado", AHORA_SEGUNDOS - 60],
    ["con exp igual al reloj", AHORA_SEGUNDOS],
  ])("un token vencido (%s) se elimina y avisa en /login", (_caso, exp) => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(exp));

    renderizarApp("/agenda");

    expect(ubicacion()).toBe("/login");
    expect(screen.getByText(AVISO_VENCIDA)).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it.each([
    ["ilegible", "no-es-un-jwt"],
    [
      "de rol desconocido",
      crearToken({ rol: "administrador", exp: AHORA_SEGUNDOS + 3600 }),
    ],
    [
      "de rol desconocido y exp pasado",
      crearToken({ rol: "administrador", exp: AHORA_SEGUNDOS - 60 }),
    ],
    ["sin exp", crearToken({ rol: "recepcionista", profesional_id: null })],
  ])("un token %s se elimina sin avisar", (_caso, token) => {
    sessionStorage.setItem(CLAVE_TOKEN, token);

    renderizarApp("/agenda");

    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it("sin token guardado, /login no muestra el aviso", () => {
    renderizarApp("/agenda");

    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
  });
});
