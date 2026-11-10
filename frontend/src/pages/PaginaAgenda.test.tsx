import {
  act,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";

import { CLAVE_TOKEN } from "../features/sesion/almacenamiento";
import { instalarApiFalsa, type ApiFalsa } from "../test/apiFalsa";
import {
  bloqueo,
  ID_ANA,
  ID_LIMPIEZA,
  ID_LUIS,
  ID_SILLON_1,
  ID_SILLON_2,
  paciente,
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

/** Solo los elementos de una columna, sin su encabezado. */
function elementos(region: HTMLElement) {
  return within(within(region).getByRole("list"));
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

const ID_INEXISTENTE = "00000000-0000-4000-8000-0000000000a9";
const LUIS_INACTIVO = profesional({
  id: ID_LUIS,
  nombre: "Luis",
  apellido: "Inventado",
  activo: false,
});

function ultimoTurnos(api: ApiFalsa) {
  const pedidos = api.pedidos("GET /turnos");
  const ultimo = pedidos[pedidos.length - 1];
  if (ultimo === undefined) throw new Error("No hubo pedidos a /turnos");
  return ultimo;
}

describe("Filtros por profesional y por sillón", () => {
  it("filtrar por profesional pide solo ese profesional y deja una columna", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      profesionales: [
        profesional(),
        profesional({ id: ID_LUIS, nombre: "Luis", apellido: "Inventado" }),
      ],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(screen.getAllByRole("region")).toHaveLength(2);

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Inventado, Luis",
    );

    await waitFor(() =>
      expect(ultimoTurnos(api).parametros.get("profesional_id")).toBe(ID_LUIS),
    );
    await waitFor(() => expect(screen.getAllByRole("region")).toHaveLength(1));
    expect(
      screen.getByRole("region", { name: "Inventado, Luis" }),
    ).toBeInTheDocument();
  });

  it("filtrar por profesional y sillón a la vez envía los dos parámetros", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      sillones: [sillon(), sillon({ id: ID_SILLON_2, nombre: "Sillón 2" })],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await esperarCarga();

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Sillón"), "Sillón 2");

    await waitFor(() => {
      const ultimo = ultimoTurnos(api);
      expect(ultimo.parametros.get("profesional_id")).toBe(ID_ANA);
      expect(ultimo.parametros.get("sillon_id")).toBe(ID_SILLON_2);
    });
  });

  it("la opción Todos los sillones quita el filtro", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    const { user } = renderizarApp(
      "/agenda?fecha=2026-11-09&sillon=" + ID_SILLON_1,
    );
    await esperarCarga();
    expect(ultimoTurnos(api).parametros.get("sillon_id")).toBe(ID_SILLON_1);

    await user.selectOptions(
      screen.getByLabelText("Sillón"),
      "Todos los sillones",
    );

    await waitFor(() =>
      expect(ultimoTurnos(api).parametros.has("sillon_id")).toBe(false),
    );
  });

  it("los selectores incluyen a los desactivados, identificados como inactivos", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      profesionales: [profesional(), LUIS_INACTIVO],
      sillones: [
        sillon({ id: ID_SILLON_2, nombre: "Sillón 2", activo: false }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(
      await screen.findByRole("option", { name: "Inventado, Luis (inactivo)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Sillón 2 (inactivo)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Todos los profesionales" }),
    ).toBeInTheDocument();
  });

  it("filtrar por un desactivado sin elementos no deja columnas y informa el período vacío", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { profesionales: [profesional(), LUIS_INACTIVO] });

    renderizarApp("/agenda?fecha=2026-11-09&profesional=" + ID_LUIS);

    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(screen.queryAllByRole("region")).toHaveLength(0);
  });

  it("filtrar por un desactivado con solo cancelados ocultos no deja columnas y usa el texto propio", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      profesionales: [profesional(), LUIS_INACTIVO],
      turnos: [turno({ profesional_id: ID_LUIS, estado: "cancelado" })],
    });

    renderizarApp("/agenda?fecha=2026-11-09&profesional=" + ID_LUIS);

    expect(await screen.findByText(SOLO_CANCELADOS)).toBeInTheDocument();
    expect(screen.queryAllByRole("region")).toHaveLength(0);
  });

  it("un id bien formado que no existe se pide, se muestra como no disponible y no genera columna", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);

    renderizarApp("/agenda?fecha=2026-11-09&profesional=" + ID_INEXISTENTE);

    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(ultimoTurnos(api).parametros.get("profesional_id")).toBe(
      ID_INEXISTENTE,
    );
    expect(
      screen.getByRole("option", {
        name: "Profesional no disponible",
        selected: true,
      }),
    ).toBeInTheDocument();
    expect(screen.queryAllByRole("region")).toHaveLength(0);
  });
});

describe("Bloqueos en la agenda", () => {
  it("muestra el bloqueo con su identificación, horario y motivo, sin acciones", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { bloqueos: [bloqueo()] });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(within(ana).getByText("Bloqueo")).toBeInTheDocument();
    expect(within(ana).getByText("15:00")).toBeInTheDocument();
    expect(within(ana).getByText("16:00")).toBeInTheDocument();
    expect(within(ana).getByText("Congreso")).toBeInTheDocument();
    expect(within(ana).queryByRole("button")).not.toBeInTheDocument();
  });

  it("con filtro de sillón sigue mostrando el bloqueo del profesional", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { bloqueos: [bloqueo()] });

    renderizarApp("/agenda?fecha=2026-11-09&sillon=" + ID_SILLON_1);

    expect(await screen.findByText("Congreso")).toBeInTheDocument();
  });

  it("en la semana sin filtro de profesional el bloqueo nombra a su profesional", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { bloqueos: [bloqueo()] });

    renderizarApp("/agenda?vista=semana&fecha=2026-11-09");

    const lunes = await screen.findByRole("region", { name: "Lunes 09/11" });
    expect(within(lunes).getByText("Ficticia, Ana")).toBeInTheDocument();
  });

  it("en la vista por profesional el bloqueo no repite el nombre que ya dice la columna", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { bloqueos: [bloqueo()] });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(elementos(ana).queryByText("Ficticia, Ana")).not.toBeInTheDocument();
  });
});

describe("Datos visibles de cada turno según las columnas", () => {
  it("en la semana el turno muestra el profesional y el sillón", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { turnos: [turno()] });

    renderizarApp("/agenda?vista=semana&fecha=2026-11-09");

    const lunes = await screen.findByRole("region", { name: "Lunes 09/11" });
    expect(within(lunes).getByText("Ficticia, Ana")).toBeInTheDocument();
    expect(within(lunes).getByText("Sillón 1")).toBeInTheDocument();
  });

  it("en la vista por profesional el turno muestra el sillón y no repite al profesional", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { turnos: [turno()] });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(within(ana).getByText("Sillón 1")).toBeInTheDocument();
    expect(elementos(ana).queryByText("Ficticia, Ana")).not.toBeInTheDocument();
  });

  it("en la vista por sillón el turno muestra al profesional y no repite el sillón", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { turnos: [turno()] });

    renderizarApp("/agenda?fecha=2026-11-09&columnas=sillon");

    const columnaSillon = await screen.findByRole("region", {
      name: "Sillón 1",
    });
    expect(
      within(columnaSillon).getByText("Ficticia, Ana"),
    ).toBeInTheDocument();
    expect(
      elementos(columnaSillon).queryByText("Sillón 1"),
    ).not.toBeInTheDocument();
  });
});

describe("Agrupar la vista diaria por sillón", () => {
  it("elegir agrupar por sillón cambia las columnas y queda en la URL", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      turnos: [turno({ id: "t1" }), turno({ id: "t2", sillon_id: null })],
      bloqueos: [bloqueo()],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByRole("region", { name: "Ficticia, Ana" });

    await user.selectOptions(screen.getByLabelText("Agrupar por"), "Sillón");

    const columnaSillon = await screen.findByRole("region", {
      name: "Sillón 1",
    });
    expect(
      within(columnaSillon).getByText("Imaginaria, Carla"),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Sin sillón" })).getByText(
        "Imaginaria, Carla",
      ),
    ).toBeInTheDocument();
    const bloqueos = screen.getByRole("region", { name: "Bloqueos" });
    expect(within(bloqueos).getByText("Ficticia, Ana")).toBeInTheDocument();
    expect(screen.getByTestId("busqueda").textContent).toContain(
      "columnas=sillon",
    );
  });

  it("sin turnos sin sillón ni bloqueos no se ven esas columnas", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { turnos: [turno()] });

    renderizarApp("/agenda?fecha=2026-11-09&columnas=sillon");

    await screen.findByRole("region", { name: "Sillón 1" });
    expect(
      screen.queryByRole("region", { name: "Sin sillón" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "Bloqueos" }),
    ).not.toBeInTheDocument();
  });

  it("agrupando por sillón, el filtro de profesional conserva las columnas de sillones", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      sillones: [sillon(), sillon({ id: ID_SILLON_2, nombre: "Sillón 2" })],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09&columnas=sillon");
    await screen.findByRole("region", { name: "Sillón 1" });

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );

    await waitFor(() =>
      expect(ultimoTurnos(api).parametros.get("profesional_id")).toBe(ID_ANA),
    );
    expect(
      screen.getByRole("region", { name: "Sillón 1" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "Sillón 2" }),
    ).toBeInTheDocument();
  });

  it("agrupando por sillón, el filtro de sillón deja ese sillón y Bloqueos", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      sillones: [sillon(), sillon({ id: ID_SILLON_2, nombre: "Sillón 2" })],
      bloqueos: [bloqueo()],
    });

    renderizarApp(
      "/agenda?fecha=2026-11-09&columnas=sillon&sillon=" + ID_SILLON_1,
    );

    await screen.findByRole("region", { name: "Sillón 1" });
    expect(
      screen.getByRole("region", { name: "Bloqueos" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: "Sillón 2" }),
    ).not.toBeInTheDocument();
  });

  it("en la vista semanal no se ofrece agrupar por sillón", async () => {
    conSesion();
    instalarApiFalsa();

    renderizarApp("/agenda?vista=semana&fecha=2026-11-09");

    await esperarCarga();
    expect(screen.queryByLabelText("Agrupar por")).not.toBeInTheDocument();
  });
});

const BRUNO = {
  id: "00000000-0000-4000-8000-0000000000e2",
  nombre: "Bruno",
  apellido: "Ejemplo",
};

describe("Turnos cancelados", () => {
  it("están ocultos por defecto y se ve solo el programado", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      turnos: [
        turno({ id: "t1" }),
        turno({ id: "t2", paciente: BRUNO, estado: "cancelado" }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(screen.queryByText("Ejemplo, Bruno")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Mostrar cancelados")).not.toBeChecked();
  });

  it("Mostrar cancelados los muestra con el texto Cancelado y sin un pedido nuevo", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      turnos: [
        turno({ id: "t1" }),
        turno({ id: "t2", paciente: BRUNO, estado: "cancelado" }),
      ],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByText("Imaginaria, Carla");
    const pedidosAntes = api.pedidos().length;

    await user.click(screen.getByLabelText("Mostrar cancelados"));

    const cancelado = (await screen.findByText("Ejemplo, Bruno")).closest(
      "li",
    )!;
    const programado = screen.getByText("Imaginaria, Carla").closest("li")!;
    expect(within(cancelado).getByText("Cancelado")).toBeInTheDocument();
    expect(within(programado).queryByText("Cancelado")).not.toBeInTheDocument();
    expect(api.pedidos()).toHaveLength(pedidosAntes);
    expect(screen.getByTestId("busqueda").textContent).toContain(
      "cancelados=1",
    );
  });

  it("desactivar la casilla los vuelve a ocultar y quita el parámetro", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      turnos: [turno({ id: "t2", paciente: BRUNO, estado: "cancelado" })],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09&cancelados=1");
    await screen.findByText("Ejemplo, Bruno");

    await user.click(screen.getByLabelText("Mostrar cancelados"));

    await waitFor(() =>
      expect(screen.queryByText("Ejemplo, Bruno")).not.toBeInTheDocument(),
    );
    expect(screen.getByTestId("busqueda").textContent).not.toContain(
      "cancelados",
    );
  });

  it("la casilla se conserva al recargar desde la URL", async () => {
    conSesion();
    cargar(instalarApiFalsa());

    renderizarApp("/agenda?fecha=2026-11-09&cancelados=1");

    expect(await screen.findByLabelText("Mostrar cancelados")).toBeChecked();
  });

  it("un profesional desactivado con solo cancelados ocultos no tiene columna, y sí al mostrarlos", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      profesionales: [profesional(), LUIS_INACTIVO],
      turnos: [turno({ profesional_id: ID_LUIS, estado: "cancelado" })],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(
      screen.queryByRole("region", { name: "Inventado, Luis" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Mostrar cancelados"));

    expect(
      await screen.findByRole("region", { name: "Inventado, Luis" }),
    ).toBeInTheDocument();
  });
});

describe("Elementos que cruzan días", () => {
  it("un turno que cruza la medianoche se ve en los dos días con sus extremos reales", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      turnos: [
        turno({
          inicio: "2026-11-10T23:30:00-03:00",
          fin: "2026-11-11T00:30:00-03:00",
        }),
      ],
    });

    renderizarApp("/agenda?vista=semana&fecha=2026-11-09");

    const martes = await screen.findByRole("region", { name: "Martes 10/11" });
    const miercoles = screen.getByRole("region", { name: "Miércoles 11/11" });
    for (const dia of [martes, miercoles]) {
      expect(within(dia).getByText("10/11 23:30")).toBeInTheDocument();
      expect(within(dia).getByText("11/11 00:30")).toBeInTheDocument();
    }
    expect(
      within(screen.getByRole("region", { name: "Lunes 09/11" })).queryByText(
        "Imaginaria, Carla",
      ),
    ).not.toBeInTheDocument();
  });

  it("un bloqueo de varios días ocupa el día de la vista e indica sus extremos reales", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      bloqueos: [
        bloqueo({
          inicio: "2026-11-09T08:00:00-03:00",
          fin: "2026-11-13T20:00:00-03:00",
        }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-11");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(within(ana).getByText("09/11 08:00")).toBeInTheDocument();
    expect(within(ana).getByText("13/11 20:00")).toBeInTheDocument();
  });

  it("un bloqueo que no respeta la grilla muestra su hora real", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      bloqueos: [
        bloqueo({
          inicio: "2026-11-09T10:03:00-03:00",
          fin: "2026-11-09T10:07:00-03:00",
        }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(within(ana).getByText("10:03")).toBeInTheDocument();
    expect(within(ana).getByText("10:07")).toBeInTheDocument();
  });

  it("un bloqueo que termina justo a la medianoche no aparece en el día siguiente", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, {
      bloqueos: [
        bloqueo({
          inicio: "2026-11-10T20:00:00-03:00",
          fin: "2026-11-11T00:00:00-03:00",
        }),
      ],
    });

    renderizarApp("/agenda?vista=semana&fecha=2026-11-09");

    const martes = await screen.findByRole("region", { name: "Martes 10/11" });
    expect(within(martes).getByText("Bloqueo")).toBeInTheDocument();
    expect(
      within(
        screen.getByRole("region", { name: "Miércoles 11/11" }),
      ).queryByText("Bloqueo"),
    ).not.toBeInTheDocument();
  });
});

describe("Agenda del odontólogo", () => {
  it("no envía profesional_id aunque esté en la URL y no ofrece filtro de profesional ni agrupar", async () => {
    conSesion("odontologo");
    const api = instalarApiFalsa();
    cargar(api);

    renderizarApp("/agenda?fecha=2026-11-09&profesional=" + ID_LUIS);

    await esperarCarga();
    expect(
      api.pedidos("GET /turnos")[0]?.parametros.has("profesional_id"),
    ).toBe(false);
    expect(screen.queryByLabelText("Profesional")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Agrupar por")).not.toBeInTheDocument();
  });

  it("puede filtrar por sillón: envía sillon_id y no profesional_id", async () => {
    conSesion("odontologo");
    const api = instalarApiFalsa();
    cargar(api, {
      sillones: [sillon(), sillon({ id: ID_SILLON_2, nombre: "Sillón 2" })],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await esperarCarga();

    await user.selectOptions(screen.getByLabelText("Sillón"), "Sillón 2");

    await waitFor(() => {
      const ultimo = ultimoTurnos(api);
      expect(ultimo.parametros.get("sillon_id")).toBe(ID_SILLON_2);
      expect(ultimo.parametros.has("profesional_id")).toBe(false);
    });
  });

  it("tiene una sola columna, la de su profesional, aunque esté vacía", async () => {
    conSesion("odontologo");
    const api = instalarApiFalsa();
    cargar(api, {
      profesionales: [
        profesional(),
        profesional({ id: ID_LUIS, nombre: "Luis", apellido: "Inventado" }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(screen.getAllByRole("region")).toHaveLength(1);
    expect(columna("Ficticia, Ana")).toBeInTheDocument();
  });

  it("también si su profesional está desactivado", async () => {
    conSesion("odontologo");
    const api = instalarApiFalsa();
    cargar(api, { profesionales: [profesional({ activo: false })] });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText(VACIO)).toBeInTheDocument();
    expect(screen.getAllByRole("region")).toHaveLength(1);
    expect(columna("Ficticia, Ana")).toBeInTheDocument();
  });

  it("agrupar por sillón en la URL se ignora", async () => {
    conSesion("odontologo");
    cargar(instalarApiFalsa());

    renderizarApp("/agenda?fecha=2026-11-09&columnas=sillon");

    await screen.findByRole("region", { name: "Ficticia, Ana" });
    expect(screen.getAllByRole("region")).toHaveLength(1);
  });

  it("no pide pacientes y ve el nombre del paciente en la agenda", async () => {
    conSesion("odontologo");
    const api = instalarApiFalsa();
    cargar(api, { turnos: [turno()] });

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(
      api.pedidos().filter((p) => p.ruta.startsWith("/pacientes")),
    ).toHaveLength(0);
  });

  it("no ve Nuevo turno ni, en el detalle, Reprogramar ni Cancelar turno", async () => {
    conSesion("odontologo");
    const api = instalarApiFalsa();
    cargar(api, {
      turnos: [
        turno({
          inicio: "2026-11-09T15:00:00-03:00",
          fin: "2026-11-09T15:45:00-03:00",
        }),
      ],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");

    await user.click(
      await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
    );

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Nuevo turno" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Reprogramar" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cancelar turno" }),
    ).not.toBeInTheDocument();
  });
});

describe("Operaciones solo para la recepcionista", () => {
  const FUTURO = {
    inicio: "2026-11-09T15:00:00-03:00",
    fin: "2026-11-09T15:45:00-03:00",
  };

  async function abrirDetalle(datos: Datos) {
    conSesion();
    cargar(instalarApiFalsa(), datos);
    const vista = renderizarApp("/agenda?fecha=2026-11-09&cancelados=1");
    await vista.user.click(
      await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
    );
    await screen.findByRole("dialog");
    return vista;
  }

  it("ve Nuevo turno y, en el detalle de un programado futuro, Reprogramar y Cancelar turno", async () => {
    await abrirDetalle({ turnos: [turno(FUTURO)] });

    expect(
      screen.getByRole("button", { name: "Nuevo turno" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reprogramar" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Cancelar turno" }),
    ).toBeInTheDocument();
  });

  it("un turno cancelado futuro no ofrece Reprogramar ni Cancelar turno", async () => {
    await abrirDetalle({ turnos: [turno({ ...FUTURO, estado: "cancelado" })] });

    expect(
      screen.queryByRole("button", { name: "Reprogramar" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cancelar turno" }),
    ).not.toBeInTheDocument();
  });

  it("un turno cuyo inicio es igual al reloj ya inició: no ofrece las operaciones", async () => {
    // El reloj fijo es 2026-11-09 09:00 hora local
    await abrirDetalle({
      turnos: [
        turno({
          inicio: "2026-11-09T09:00:00-03:00",
          fin: "2026-11-09T09:45:00-03:00",
        }),
      ],
    });

    expect(
      screen.queryByRole("button", { name: "Reprogramar" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cancelar turno" }),
    ).not.toBeInTheDocument();
  });

  it("un turno que empieza cinco minutos después del reloj sí las ofrece", async () => {
    await abrirDetalle({
      turnos: [
        turno({
          inicio: "2026-11-09T09:05:00-03:00",
          fin: "2026-11-09T09:50:00-03:00",
        }),
      ],
    });

    expect(
      screen.getByRole("button", { name: "Reprogramar" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Cancelar turno" }),
    ).toBeInTheDocument();
  });
});

describe("Detalle de un turno", () => {
  it("muestra horario, paciente, prestación, profesional, sillón y estado", async () => {
    conSesion();
    cargar(instalarApiFalsa(), { turnos: [turno()] });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");

    await user.click(
      await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
    );

    const detalle = await screen.findByRole("dialog", {
      name: "Detalle del turno",
    });
    expect(
      within(detalle).getByText("09/11 10:00 – 10:45"),
    ).toBeInTheDocument();
    expect(within(detalle).getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(within(detalle).getByText("Limpieza")).toBeInTheDocument();
    expect(within(detalle).getByText("Ficticia, Ana")).toBeInTheDocument();
    expect(within(detalle).getByText("Sillón 1")).toBeInTheDocument();
    expect(within(detalle).getByText("Programado")).toBeInTheDocument();
  });

  it("un turno cancelado muestra el estado Cancelado y el motivo", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      turnos: [turno({ estado: "cancelado", motivo_cancelacion: "Viaje" })],
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09&cancelados=1");

    await user.click(
      await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
    );

    const detalle = await screen.findByRole("dialog");
    expect(within(detalle).getByText("Cancelado")).toBeInTheDocument();
    expect(within(detalle).getByText("Viaje")).toBeInTheDocument();
  });

  it("un turno sin sillón muestra Sin sillón", async () => {
    conSesion();
    cargar(instalarApiFalsa(), { turnos: [turno({ sillon_id: null })] });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");

    await user.click(
      await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
    );

    expect(
      within(await screen.findByRole("dialog")).getByText("Sin sillón"),
    ).toBeInTheDocument();
  });

  it("no muestra documento, teléfono ni email del paciente aunque la API los enviara", async () => {
    conSesion();
    const conDatosDePaciente = turno();
    Object.assign(conDatosDePaciente.paciente, {
      documento: "00000104",
      telefono: "1100000000",
      email: "carla@example.com",
    });
    cargar(instalarApiFalsa(), { turnos: [conDatosDePaciente] });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");

    await user.click(
      await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
    );

    await screen.findByRole("dialog");
    expect(
      screen.queryByText(/00000104|1100000000|carla@example.com/),
    ).not.toBeInTheDocument();
  });

  it("Cerrar deja la agenda sin diálogo abierto", async () => {
    conSesion();
    cargar(instalarApiFalsa(), { turnos: [turno()] });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    await user.click(
      await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
    );
    await screen.findByRole("dialog");

    await user.click(screen.getByRole("button", { name: "Cerrar" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("Accesibilidad de la agenda", () => {
  it("un turno se elige con el teclado: con el foco en el turno, Enter abre su detalle", async () => {
    conSesion();
    cargar(instalarApiFalsa(), { turnos: [turno()] });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    const boton = await screen.findByRole("button", {
      name: /Imaginaria, Carla/,
    });

    boton.focus();
    await user.keyboard("{Enter}");

    expect(
      await screen.findByRole("dialog", { name: "Detalle del turno" }),
    ).toBeInTheDocument();
  });

  it("los elementos de una columna están en orden cronológico en el documento", async () => {
    conSesion();
    cargar(instalarApiFalsa(), {
      turnos: [
        turno({
          id: "t11",
          paciente: BRUNO,
          inicio: "2026-11-09T11:00:00-03:00",
          fin: "2026-11-09T11:30:00-03:00",
        }),
        turno({
          id: "t09",
          inicio: "2026-11-09T09:00:00-03:00",
          fin: "2026-11-09T09:30:00-03:00",
        }),
      ],
    });

    renderizarApp("/agenda?fecha=2026-11-09");

    const ana = await screen.findByRole("region", { name: "Ficticia, Ana" });
    const botones = within(ana).getAllByRole("button");
    expect(botones[0]).toHaveTextContent("Imaginaria, Carla");
    expect(botones[1]).toHaveTextContent("Ejemplo, Bruno");
  });

  it("los filtros y la casilla tienen etiqueta", async () => {
    conSesion();
    cargar(instalarApiFalsa());

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(await screen.findByLabelText("Profesional")).toBeInTheDocument();
    expect(screen.getByLabelText("Sillón")).toBeInTheDocument();
    expect(screen.getByLabelText("Mostrar cancelados")).toBeInTheDocument();
  });

  it("los controles de vista y de período tienen nombre accesible", async () => {
    conSesion();
    cargar(instalarApiFalsa());

    renderizarApp("/agenda?fecha=2026-11-09");

    expect(
      await screen.findByRole("group", { name: "Vista" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Período" })).toBeInTheDocument();
  });
});

type Usuario = ReturnType<typeof renderizarApp>["user"];

async function abrirNuevoTurno(user: Usuario) {
  await esperarCarga();
  await user.click(screen.getByRole("button", { name: "Nuevo turno" }));
  return await screen.findByRole("dialog", { name: "Nuevo turno" });
}

/** Completa el formulario de alta con todo lo obligatorio, para el 12/11 a las 10:00. */
async function llenarAlta(user: Usuario, api: ApiFalsa, dialogo: HTMLElement) {
  api.responder("GET /pacientes", { status: 200, cuerpo: [paciente()] });
  await user.type(within(dialogo).getByLabelText("Buscar paciente"), "car");
  await user.click(
    await within(dialogo).findByRole("button", { name: /Imaginaria, Carla/ }),
  );
  await user.selectOptions(
    within(dialogo).getByLabelText("Profesional"),
    "Ficticia, Ana",
  );
  await user.selectOptions(
    within(dialogo).getByLabelText("Prestación"),
    "Limpieza",
  );
  await user.selectOptions(
    within(dialogo).getByLabelText("Sillón"),
    "Sillón 1",
  );
  fireEvent.change(within(dialogo).getByLabelText("Fecha"), {
    target: { value: "2026-11-12" },
  });
  fireEvent.change(within(dialogo).getByLabelText("Hora"), {
    target: { value: "10:00" },
  });
}

function enviarAlta(user: Usuario, dialogo: HTMLElement) {
  return user.click(
    within(dialogo).getByRole("button", { name: "Crear turno" }),
  );
}

describe("Alta de un turno desde la agenda", () => {
  it("un alta exitosa hace un POST, cierra el formulario, relee la agenda y confirma con día y hora", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);
    const lecturasAntes = api.pedidos("GET /turnos").length;

    await enviarAlta(user, dialogo);

    expect(
      await screen.findByText("Turno creado para el 12/11 a las 10:00."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.pedidos("POST /turnos")).toHaveLength(1);
    expect(api.pedidos("GET /turnos")).toHaveLength(lecturasAntes + 1);
  });

  it("no salta a la fecha del turno: la agenda sigue en el período en curso", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);

    await enviarAlta(user, dialogo);

    await screen.findByText("Turno creado para el 12/11 a las 10:00.");
    expect(screen.getByTestId("busqueda").textContent).toBe(
      "?fecha=2026-11-09",
    );
  });

  it("precarga la fecha de la agenda y el profesional del filtro", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    const { user } = renderizarApp(
      "/agenda?fecha=2026-11-12&profesional=" + ID_ANA,
    );
    const dialogo = await abrirNuevoTurno(user);

    expect(within(dialogo).getByLabelText("Fecha")).toHaveValue("2026-11-12");
    expect(within(dialogo).getByLabelText("Profesional")).toHaveValue(ID_ANA);
  });

  it("con un POST sin responder el envío queda deshabilitado y no se hace otro", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    api.pendiente("POST /turnos");
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);

    await enviarAlta(user, dialogo);
    const boton = within(dialogo).getByRole("button", { name: "Crear turno" });
    await user.click(boton);

    expect(boton).toBeDisabled();
    expect(api.pedidos("POST /turnos")).toHaveLength(1);
  });

  it("si la relectura falla después del alta, el alta sigue confirmada y se ven el error y los datos anteriores", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api, { turnos: [turno({ paciente: BRUNO, id: "previo" })] });
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    const dialogo = await abrirNuevoTurno(user);
    await screen.findByText("Ejemplo, Bruno");
    await llenarAlta(user, api, dialogo);
    api.responder("GET /turnos", { red: true });

    await enviarAlta(user, dialogo);

    expect(
      await screen.findByText("Turno creado para el 12/11 a las 10:00."),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(screen.getByText("Ejemplo, Bruno")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("una lectura vieja del mismo período que llega después de la relectura no pisa el turno creado", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    const lecturaVieja = api.pendiente("GET /turnos");
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = renderizarApp("/agenda?fecha=2026-11-09");
    // Con la lectura inicial sin responder, el alta ya puede hacerse: los catálogos cargaron
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Nuevo turno" }),
      ).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Nuevo turno" }));
    const dialogo = await screen.findByRole("dialog", { name: "Nuevo turno" });
    await llenarAlta(user, api, dialogo);
    api.responder("GET /turnos", {
      status: 200,
      cuerpo: {
        turnos: [turno({ paciente: BRUNO, id: "creado" })],
        bloqueos: [],
      },
    });

    await enviarAlta(user, dialogo);
    expect(await screen.findByText("Ejemplo, Bruno")).toBeInTheDocument();
    await act(async () => {
      lecturaVieja.resolver(SIN_ELEMENTOS);
    });

    expect(screen.getByText("Ejemplo, Bruno")).toBeInTheDocument();
    expect(screen.queryByText(VACIO)).not.toBeInTheDocument();
  });
});

describe("Errores del alta que cambian la agenda", () => {
  it("un 409 solapamiento conserva todos los datos, muestra el conflicto y relee la agenda", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    api.responder("POST /turnos", {
      status: 409,
      cuerpo: {
        detail: {
          codigo: "solapamiento",
          recursos: ["profesional", "paciente"],
        },
      },
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);
    fireEvent.change(within(dialogo).getByLabelText("Duración"), {
      target: { value: "60" },
    });
    const lecturasAntes = api.pedidos("GET /turnos").length;

    await enviarAlta(user, dialogo);

    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(
      "Ese horario ya está ocupado para el profesional y el paciente.",
    );
    expect(
      screen.getByRole("dialog", { name: "Nuevo turno" }),
    ).toBeInTheDocument();
    expect(within(dialogo).getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(within(dialogo).getByLabelText("Profesional")).toHaveValue(ID_ANA);
    expect(within(dialogo).getByLabelText("Prestación")).toHaveValue(
      ID_LIMPIEZA,
    );
    expect(within(dialogo).getByLabelText("Sillón")).toHaveValue(ID_SILLON_1);
    expect(within(dialogo).getByLabelText("Fecha")).toHaveValue("2026-11-12");
    expect(within(dialogo).getByLabelText("Hora")).toHaveValue("10:00");
    expect(within(dialogo).getByLabelText("Duración")).toHaveValue(60);
    await waitFor(() =>
      expect(api.pedidos("GET /turnos")).toHaveLength(lecturasAntes + 1),
    );
  });

  it("un turno_en_bloqueo se muestra como error general y relee la agenda", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    api.responder("POST /turnos", {
      status: 422,
      cuerpo: { detail: { codigo: "turno_en_bloqueo", mensaje: "técnico" } },
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);
    const lecturasAntes = api.pedidos("GET /turnos").length;

    await enviarAlta(user, dialogo);

    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(
      "El turno se superpone con un bloqueo de la agenda del profesional.",
    );
    await waitFor(() =>
      expect(api.pedidos("GET /turnos")).toHaveLength(lecturasAntes + 1),
    );
  });

  it("corregir y reenviar con éxito hace un segundo POST y cierra el formulario", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    let intentos = 0;
    api.responder("POST /turnos", () => {
      intentos += 1;
      return intentos === 1
        ? {
            status: 409,
            cuerpo: {
              detail: { codigo: "solapamiento", recursos: ["profesional"] },
            },
          }
        : { status: 201, cuerpo: {} };
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);
    await enviarAlta(user, dialogo);
    await within(dialogo).findByRole("alert");

    fireEvent.change(within(dialogo).getByLabelText("Hora"), {
      target: { value: "11:00" },
    });
    await enviarAlta(user, dialogo);

    expect(
      await screen.findByText("Turno creado para el 12/11 a las 11:00."),
    ).toBeInTheDocument();
    expect(api.pedidos("POST /turnos")).toHaveLength(2);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("un reenvío con otro error borra el anterior", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    let intentos = 0;
    api.responder("POST /turnos", () => {
      intentos += 1;
      return intentos === 1
        ? {
            status: 409,
            cuerpo: {
              detail: { codigo: "solapamiento", recursos: ["profesional"] },
            },
          }
        : {
            status: 422,
            cuerpo: {
              detail: { codigo: "fuera_de_horario", mensaje: "técnico" },
            },
          };
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);
    await enviarAlta(user, dialogo);
    await within(dialogo).findByText(
      "Ese horario ya está ocupado para el profesional.",
    );

    fireEvent.change(within(dialogo).getByLabelText("Hora"), {
      target: { value: "23:00" },
    });
    await enviarAlta(user, dialogo);

    expect(
      await within(dialogo).findByText(
        "El turno queda fuera del horario de atención del profesional.",
      ),
    ).toBeInTheDocument();
    expect(
      within(dialogo).queryByText(
        "Ese horario ya está ocupado para el profesional.",
      ),
    ).not.toBeInTheDocument();
  });
});

describe("Alta: sesión y permisos", () => {
  it("un 401 no_autenticado al enviar lleva a /login con el aviso de sesión vencida", async () => {
    conSesion();
    const api = instalarApiFalsa();
    cargar(api);
    api.responder("POST /turnos", {
      status: 401,
      cuerpo: {
        detail: { codigo: "no_autenticado", mensaje: "No autenticado" },
      },
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);

    await enviarAlta(user, dialogo);

    await waitFor(() => expect(ubicacion()).toBe("/login"));
    expect(
      screen.getByText("Tu sesión venció. Iniciá sesión de nuevo."),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it("un 403 rol_insuficiente no cierra la sesión y deja el formulario abierto", async () => {
    conSesion();
    const token = sessionStorage.getItem(CLAVE_TOKEN);
    const api = instalarApiFalsa();
    cargar(api);
    api.responder("POST /turnos", {
      status: 403,
      cuerpo: { detail: { codigo: "rol_insuficiente", mensaje: "técnico" } },
    });
    const { user } = renderizarApp("/agenda?fecha=2026-11-12");
    const dialogo = await abrirNuevoTurno(user);
    await llenarAlta(user, api, dialogo);

    await enviarAlta(user, dialogo);

    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(
      "No tenés permiso para esta operación.",
    );
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
    expect(ubicacion()).toBe("/agenda");
    expect(
      screen.getByRole("dialog", { name: "Nuevo turno" }),
    ).toBeInTheDocument();
  });
});
