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

const SIN_ELEMENTOS = { status: 200, cuerpo: { turnos: [], bloqueos: [] } };
const CON_UN_TURNO_DEL_DIA_9 = {
  status: 200,
  cuerpo: { turnos: [turno()], bloqueos: [] },
};

// Un turno del 11/11: si la respuesta del día 10 pisara a la del 11, el período dejaría de verse vacío
const CON_UN_TURNO = {
  status: 200,
  cuerpo: {
    turnos: [
      turno({
        inicio: "2026-11-11T10:00:00-03:00",
        fin: "2026-11-11T10:45:00-03:00",
      }),
    ],
    bloqueos: [],
  },
};

describe("Respuestas fuera de orden", () => {
  it("la respuesta del último pedido gana aunque la del anterior llegue después", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { navegarA } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByText(VACIO);
    const dia10 = api.pendiente("GET /turnos");
    const dia11 = api.pendiente("GET /turnos");

    await navegarA("/agenda?fecha=2026-11-10");
    await navegarA("/agenda?fecha=2026-11-11");
    await act(async () => {
      dia11.resolver(SIN_ELEMENTOS);
    });
    await screen.findByText(VACIO);
    await act(async () => {
      dia10.resolver(CON_UN_TURNO);
    });

    // Si el día 10 hubiera pisado al 11, ya no se vería el período vacío
    expect(screen.getByText(VACIO)).toBeInTheDocument();
    expect(
      api.pedidos("GET /turnos").map((p) => p.parametros.get("desde")),
    ).toEqual(["2026-11-09", "2026-11-10", "2026-11-11"]);
  });

  it("el error de un pedido anterior no se muestra", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { navegarA } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByText(VACIO);
    const dia10 = api.pendiente("GET /turnos");
    const dia11 = api.pendiente("GET /turnos");
    await navegarA("/agenda?fecha=2026-11-10");
    await navegarA("/agenda?fecha=2026-11-11");
    await act(async () => {
      dia11.resolver(SIN_ELEMENTOS);
    });
    await screen.findByText(VACIO);

    await act(async () => {
      dia10.fallarPorRed();
    });

    expect(
      screen.queryByText("No se pudo conectar con el servidor."),
    ).not.toBeInTheDocument();
    expect(screen.getByText(VACIO)).toBeInTheDocument();
  });

  it("al cambiar de período no se ven datos del anterior mientras llegan los nuevos", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { navegarA } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByText(VACIO);
    api.pendiente("GET /turnos");

    await navegarA("/agenda?fecha=2026-11-10");

    expect(await screen.findByText("Cargando agenda…")).toBeInTheDocument();
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
  });
});

function ubicacion(): string {
  return screen.getByTestId("ubicacion").textContent ?? "";
}

describe("Errores al cargar la agenda", () => {
  it("una falla de red en la agenda muestra el mensaje y ofrece reintentar", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", { red: true });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeVisible();
    expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument();
  });

  it("un 500 en un catálogo muestra el mensaje genérico y ofrece reintentar", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { status: 500, cuerpo: { detail: "x" } });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(
      await screen.findByText("Ocurrió un error. Intentá de nuevo."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeVisible();
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
  });

  it("un 403 se muestra sin cerrar la sesión ni cambiar la ruta", async () => {
    conSesion("odontologo");
    const token = sessionStorage.getItem(CLAVE_TOKEN);
    const api = instalarApiFalsa();
    api.responder("GET /turnos", {
      status: 403,
      cuerpo: {
        detail: {
          codigo: "profesional_ajeno",
          mensaje: "Solo podés consultar tu propia agenda",
        },
      },
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(
      await screen.findByText("Solo podés consultar tu propia agenda"),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
    expect(ubicacion()).toBe("/agenda");
  });

  it("Reintentar recupera la agenda cuando la API vuelve a responder", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", { red: true });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByText("No se pudo conectar con el servidor.");
    api.responder("GET /turnos", SIN_ELEMENTOS);

    await user.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(
      screen.queryByText("No se pudo conectar con el servidor."),
    ).not.toBeInTheDocument();
  });

  it("Reintentar vuelve a pedir un catálogo que falló", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { status: 500, cuerpo: {} });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByText("Ocurrió un error. Intentá de nuevo.");
    api.responder("GET /sillones", { status: 200, cuerpo: [] });

    await user.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(api.pedidos("GET /sillones")).toHaveLength(2);
  });
});

describe("Actualización manual", () => {
  it("Actualizar vuelve a pedir el mismo período sin quitar lo que se ve", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", CON_UN_TURNO_DEL_DIA_9);
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await waitFor(() =>
      expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument(),
    );
    const pendiente = api.pendiente("GET /turnos");

    await user.click(screen.getByRole("button", { name: "Actualizar" }));

    expect(api.pedidos("GET /turnos")).toHaveLength(2);
    expect(api.pedidos("GET /turnos")[1]?.parametros.get("desde")).toBe(
      "2026-11-09",
    );
    expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument();
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
    await act(async () => {
      pendiente.resolver(CON_UN_TURNO_DEL_DIA_9);
    });
  });

  it("Actualizar no vuelve a pedir los catálogos", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByText(VACIO);

    await user.click(screen.getByRole("button", { name: "Actualizar" }));

    await waitFor(() => expect(api.pedidos("GET /turnos")).toHaveLength(2));
    expect(api.pedidos("GET /profesionales")).toHaveLength(1);
    expect(api.pedidos("GET /sillones")).toHaveLength(1);
    expect(api.pedidos("GET /prestaciones")).toHaveLength(1);
  });

  it("una recarga fallida conserva lo que se veía y muestra el error", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", CON_UN_TURNO_DEL_DIA_9);
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await waitFor(() =>
      expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument(),
    );
    api.responder("GET /turnos", { red: true });

    await user.click(screen.getByRole("button", { name: "Actualizar" }));

    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    // Sigue sin mostrar el período vacío ni la carga: los datos anteriores están a la vista
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
    expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument();
  });

  it("un turno cancelado por otro usuario deja de verse tras Actualizar", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", CON_UN_TURNO_DEL_DIA_9);
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await waitFor(() =>
      expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument(),
    );
    expect(screen.queryByText(SOLO_CANCELADOS)).not.toBeInTheDocument();
    api.responder("GET /turnos", {
      status: 200,
      cuerpo: { turnos: [turno({ estado: "cancelado" })], bloqueos: [] },
    });

    await user.click(screen.getByRole("button", { name: "Actualizar" }));

    expect(await screen.findByText(SOLO_CANCELADOS)).toBeInTheDocument();
  });
});
