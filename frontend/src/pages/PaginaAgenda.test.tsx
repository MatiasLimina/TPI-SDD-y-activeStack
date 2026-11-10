import { act, screen, waitFor, within } from "@testing-library/react";

import { CLAVE_TOKEN } from "../features/sesion/almacenamiento";
import { instalarApiFalsa, type ApiFalsa } from "../test/apiFalsa";
import {
  bloqueo,
  ID_LUIS,
  prestacion,
  profesional,
  sillon,
  turno,
} from "../test/fabricas";
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

function conSesion(
  rol: "recepcionista" | "odontologo" = "recepcionista",
  exp: number = VIGENTE,
) {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    rol === "recepcionista"
      ? tokenDeRecepcionista(exp)
      : tokenDeOdontologo(exp),
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
    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
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
    // Los datos anteriores siguen a la vista
    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
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

interface Datos {
  profesionales?: ReturnType<typeof profesional>[];
  sillones?: ReturnType<typeof sillon>[];
  prestaciones?: ReturnType<typeof prestacion>[];
  turnos?: ReturnType<typeof turno>[];
  bloqueos?: ReturnType<typeof bloqueo>[];
}

/** Configura los catálogos y la agenda; por defecto, Ana, `Sillón 1` y `Limpieza`. */
function cargar(api: ApiFalsa, datos: Datos = {}) {
  api.responder("GET /profesionales", {
    status: 200,
    cuerpo: datos.profesionales ?? [profesional()],
  });
  api.responder("GET /sillones", {
    status: 200,
    cuerpo: datos.sillones ?? [sillon()],
  });
  api.responder("GET /prestaciones", {
    status: 200,
    cuerpo: datos.prestaciones ?? [prestacion()],
  });
  api.responder("GET /turnos", {
    status: 200,
    cuerpo: { turnos: datos.turnos ?? [], bloqueos: datos.bloqueos ?? [] },
  });
}

function columna(nombre: string) {
  return screen.getByRole("region", { name: nombre });
}

describe("Contenido de la agenda", () => {
  it("muestra el turno con su hora, el paciente y la prestación en la columna del profesional", async () => {
    conSesion();
    cargar(instalarApiFalsa(), { turnos: [turno()] });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(within(ana).getByText("10:00")).toBeInTheDocument();
    expect(within(ana).getByText("10:45")).toBeInTheDocument();
    expect(within(ana).getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(within(ana).getByText("Limpieza")).toBeInTheDocument();
  });

  it("muestra los horarios en Buenos Aires aunque el navegador esté en Tokio", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      turnos: [
        turno({
          inicio: "2026-11-09T22:30:00-03:00",
          fin: "2026-11-09T23:15:00-03:00",
        }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(within(ana).getByText("22:30")).toBeInTheDocument();
    expect(within(ana).getByText("23:15")).toBeInTheDocument();
  });

  it("muestra la medianoche como 00:00 y nunca como 24:00", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      turnos: [
        turno({
          inicio: "2026-11-09T00:00:00-03:00",
          fin: "2026-11-09T00:30:00-03:00",
        }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(within(ana).getByText("00:00")).toBeInTheDocument();
    expect(screen.queryByText(/24:00/)).not.toBeInTheDocument();
  });

  it("muestra el nombre de una prestación desactivada", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      prestaciones: [prestacion({ nombre: "Control", activa: false })],
      turnos: [turno()],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText("Control")).toBeInTheDocument();
  });

  it("un id ausente del catálogo se ve con un texto genérico y sin mostrar el id", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      prestaciones: [],
      turnos: [
        turno({ prestacion_id: "00000000-0000-4000-8000-0000000000d9" }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(
      await screen.findByText("Prestación no disponible"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/00000000-0000-4000-8000-0000000000d9/),
    ).not.toBeInTheDocument();
  });

  it("un turno de un profesional ausente del catálogo tiene su columna con texto genérico", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      turnos: [turno({ profesional_id: ID_LUIS })],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    const columnaDesconocida = await screen.findByRole("region", {
      name: "Profesional no disponible",
    });
    expect(
      within(columnaDesconocida).getByText("Imaginaria, Carla"),
    ).toBeInTheDocument();
    expect(columna("Ficticia, Ana")).toBeInTheDocument();
    expect(screen.queryByText(new RegExp(ID_LUIS))).not.toBeInTheDocument();
  });

  it("incluye en el nombre de las columnas a los profesionales desactivados con turnos", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      profesionales: [
        profesional(),
        profesional({
          id: ID_LUIS,
          nombre: "Luis",
          apellido: "Inventado",
          activo: false,
        }),
      ],
      turnos: [turno({ profesional_id: ID_LUIS })],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(
      await screen.findByRole("region", { name: "Inventado, Luis" }),
    ).toBeInTheDocument();
  });
});

/** `desde` y `hasta` del último `GET /turnos` hecho. */
function rangoPedido(api: ApiFalsa): [string | null, string | null] {
  const pedidos = api.pedidos("GET /turnos");
  const ultimo = pedidos[pedidos.length - 1];
  return [
    ultimo?.parametros.get("desde") ?? null,
    ultimo?.parametros.get("hasta") ?? null,
  ];
}

async function esperarCarga() {
  await waitFor(() =>
    expect(screen.queryByText("Cargando agenda…")).not.toBeInTheDocument(),
  );
}

describe("Vistas diaria y semanal", () => {
  it("la semana va de lunes a domingo con una columna por día", async () => {
    conSesion();
    const api = instalarApiFalsa();

    renderizarApp("/agenda?vista=semana&fecha=2026-11-12");

    expect(
      await screen.findByRole("region", { name: "Lunes 09/11" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("region")).toHaveLength(7);
    expect(
      screen.getByRole("region", { name: "Domingo 15/11" }),
    ).toBeInTheDocument();
    expect(rangoPedido(api)).toEqual(["2026-11-09", "2026-11-15"]);
  });

  it.each([
    ["lunes", "2026-11-09"],
    ["domingo", "2026-11-15"],
  ])("con una fecha que es %s la semana es la misma", async (_dia, fecha) => {
    conSesion();
    const api = instalarApiFalsa();

    renderizarApp(`/agenda?vista=semana&fecha=${fecha}`);

    await esperarCarga();
    expect(rangoPedido(api)).toEqual(["2026-11-09", "2026-11-15"]);
  });

  it("de día a semana muestra la semana de la fecha en curso", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Semana" }));

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-11-09", "2026-11-15"]),
    );
  });

  it("de semana a día pide la fecha en curso", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?vista=semana&fecha=2026-11-12");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Día" }));

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-11-12", "2026-11-12"]),
    );
  });
});

describe("Navegación entre períodos", () => {
  it("el período siguiente de un día es el día siguiente, con cambio de mes", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?fecha=2026-11-30");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Período siguiente" }));

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-12-01", "2026-12-01"]),
    );
  });

  it("el período anterior de una semana es la semana anterior", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?vista=semana&fecha=2026-11-09");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Período anterior" }));

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-11-02", "2026-11-08"]),
    );
  });

  it("una semana que cruza el año pasa a la siguiente", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?vista=semana&fecha=2026-12-21");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Período siguiente" }));

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-12-28", "2027-01-03"]),
    );
  });

  it("Hoy vuelve al día actual en la vista diaria", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?fecha=2026-12-20");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Hoy" }));

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-11-09", "2026-11-09"]),
    );
  });

  it("Hoy en la vista semanal muestra la semana actual", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user } = renderizarApp("/agenda?vista=semana&fecha=2026-12-14");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Hoy" }));

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-11-09", "2026-11-15"]),
    );
  });
});

describe("La vista se conserva en la URL", () => {
  it("recargar desde la URL conserva la vista y el filtro de sillón", async () => {
    conSesion();
    const api = instalarApiFalsa();

    renderizarApp(
      "/agenda?vista=semana&fecha=2026-11-12&sillon=00000000-0000-4000-8000-0000000000c1",
    );

    await esperarCarga();
    const [pedido] = api.pedidos("GET /turnos");
    expect(pedido?.parametros.get("desde")).toBe("2026-11-09");
    expect(pedido?.parametros.get("hasta")).toBe("2026-11-15");
    expect(pedido?.parametros.get("sillon_id")).toBe(
      "00000000-0000-4000-8000-0000000000c1",
    );
  });

  it("cada cambio hace una navegación nueva: volver atrás recupera la vista anterior", async () => {
    conSesion();
    const api = instalarApiFalsa();
    const { user, volver } = renderizarApp("/agenda?fecha=2026-11-09");
    await esperarCarga();
    await user.click(screen.getByRole("button", { name: "Período siguiente" }));
    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-11-10", "2026-11-10"]),
    );

    await volver();

    await waitFor(() =>
      expect(rangoPedido(api)).toEqual(["2026-11-09", "2026-11-09"]),
    );
    expect(screen.getByTestId("busqueda").textContent).toBe(
      "?fecha=2026-11-09",
    );
  });

  it("la URL de la vista no contiene datos de pacientes", async () => {
    conSesion();
    const api = instalarApiFalsa();
    api.responder("GET /turnos", CON_UN_TURNO_DEL_DIA_9);
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await esperarCarga();

    await user.click(screen.getByRole("button", { name: "Semana" }));

    const busqueda = screen.getByTestId("busqueda").textContent ?? "";
    expect(busqueda).toBe("?vista=semana&fecha=2026-11-09");
    expect(busqueda).not.toMatch(/Carla|Imaginaria/);
  });

  it.each([
    ["una fecha que no existe", "2026-02-30", "2026-11-09"],
    ["un año posterior al admitido", "9999-12-31", "2026-11-09"],
    ["un año anterior al admitido", "0999-12-31", "2026-11-09"],
    ["el último año admitido", "9998-12-31", "9998-12-31"],
    ["el primer año admitido", "1000-01-01", "1000-01-01"],
  ])("con %s pide la fecha que corresponde", async (_caso, fecha, pedida) => {
    conSesion();
    const api = instalarApiFalsa();

    renderizarApp(`/agenda?fecha=${fecha}`);

    await esperarCarga();
    expect(rangoPedido(api)).toEqual([pedida, pedida]);
  });

  it("un filtro mal formado se ignora", async () => {
    conSesion();
    const api = instalarApiFalsa();

    renderizarApp("/agenda?fecha=2026-11-09&profesional=no-es-un-id");

    await esperarCarga();
    expect(
      api.pedidos("GET /turnos")[0]?.parametros.has("profesional_id"),
    ).toBe(false);
  });
});

describe("Día actual del consultorio", () => {
  it("a las 23:00 en Buenos Aires la agenda abre el día de Buenos Aires, no el de Tokio", async () => {
    vi.setSystemTime("2026-11-10T02:00:00Z");
    conSesion("recepcionista", AHORA_SEGUNDOS + 7 * 86400);
    const api = instalarApiFalsa();

    renderizarApp("/agenda");

    await esperarCarga();
    expect(rangoPedido(api)).toEqual(["2026-11-09", "2026-11-09"]);
  });

  it("a las 00:00 en Buenos Aires ya es el día siguiente", async () => {
    vi.setSystemTime("2026-11-10T03:00:00Z");
    conSesion("recepcionista", AHORA_SEGUNDOS + 7 * 86400);
    const api = instalarApiFalsa();

    renderizarApp("/agenda");

    await esperarCarga();
    expect(rangoPedido(api)).toEqual(["2026-11-10", "2026-11-10"]);
  });
});
