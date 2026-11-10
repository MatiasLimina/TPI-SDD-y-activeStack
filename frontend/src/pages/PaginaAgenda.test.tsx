import { act, screen, waitFor } from "@testing-library/react";

import { CLAVE_TOKEN } from "../features/sesion/almacenamiento";
import { instalarApiFalsa } from "../test/apiFalsa";
import { turno } from "../test/fabricas";
import { renderizarApp } from "../test/renderizarApp";
import { usarRelojFijo } from "../test/reloj";
import {
  AHORA_SEGUNDOS,
  tokenDeOdontologo,
  tokenDeRecepcionista,
} from "../test/tokens";

usarRelojFijo();

const VIGENTE = AHORA_SEGUNDOS + 3600;
const VACIO = "No hay turnos ni bloqueos en este período.";
const SOLO_CANCELADOS =
  "Solo hay turnos cancelados en este período. Activá Mostrar cancelados para verlos.";

function conSesion(rol: "recepcionista" | "odontologo" = "recepcionista") {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    rol === "recepcionista"
      ? tokenDeRecepcionista(VIGENTE)
      : tokenDeOdontologo(VIGENTE),
  );
}

describe("Carga de la agenda", () => {
  it("pide los turnos del día y los tres catálogos", async () => {
    conSesion();
    const api = instalarApiFalsa();

    renderizarApp("/agenda?fecha=2026-11-09");

    await screen.findByText(VACIO);
    const [pedidoTurnos] = api.pedidos("GET /turnos");
    expect(api.pedidos("GET /turnos")).toHaveLength(1);
    expect(pedidoTurnos?.parametros.get("desde")).toBe("2026-11-09");
    expect(pedidoTurnos?.parametros.get("hasta")).toBe("2026-11-09");
    expect(pedidoTurnos?.parametros.has("profesional_id")).toBe(false);
    expect(pedidoTurnos?.parametros.has("sillon_id")).toBe(false);
    expect(api.pedidos("GET /profesionales")).toHaveLength(1);
    expect(api.pedidos("GET /sillones")).toHaveLength(1);
    expect(api.pedidos("GET /prestaciones")).toHaveLength(1);
  });

  it("indica la carga mientras el pedido de la agenda no responde", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const pendiente = api.pendiente("GET /turnos");

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText("Cargando agenda…")).toBeInTheDocument();
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
    await act(async () => {
      pendiente.resolver({
        status: 200,
        cuerpo: { turnos: [], bloqueos: [] },
      });
    });
    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument();
  });

  it("también indica la carga mientras faltan los catálogos", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const pendiente = api.pendiente("GET /sillones");

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText("Cargando agenda…")).toBeInTheDocument();
    await act(async () => {
      pendiente.resolver({ status: 200, cuerpo: [] });
    });
    expect(await screen.findByText(VACIO)).toBeInTheDocument();
  });

  it("un período sin elementos informa que no hay nada", async () => {
    conSesion();
    instalarApiFalsa();

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(screen.queryByText(SOLO_CANCELADOS)).not.toBeInTheDocument();
  });

  it("si solo hay cancelados ocultos usa el texto propio y no el de período vacío", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", {
      status: 200,
      cuerpo: { turnos: [turno({ estado: "cancelado" })], bloqueos: [] },
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText(SOLO_CANCELADOS)).toBeInTheDocument();
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
  });

  it("con un turno programado no muestra ningún mensaje de período vacío", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", {
      status: 200,
      cuerpo: { turnos: [turno()], bloqueos: [] },
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    await waitFor(() =>
      expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument(),
    );
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
    expect(screen.queryByText(SOLO_CANCELADOS)).not.toBeInTheDocument();
  });
});
