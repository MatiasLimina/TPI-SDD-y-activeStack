import { act, screen, waitFor, within } from "@testing-library/react";

import { CLAVE_TOKEN } from "../features/sesion/almacenamiento";
import { instalarApiFalsa, type ApiFalsa } from "../test/apiFalsa";
import { ID_CARLA, pacienteFicha } from "../test/fabricas";
import { renderizarApp } from "../test/renderizarApp";
import { usarRelojManual } from "../test/reloj";
import {
  AHORA_ISO,
  AHORA_SEGUNDOS,
  tokenDeRecepcionista,
} from "../test/tokens";

const RUTA = "/pacientes";
const CARLA = pacienteFicha();
const ID_OTRA = "00000000-0000-4000-8000-0000000000e2";
const OTRA_CARLA = pacienteFicha({ id: ID_OTRA, documento: "00000105" });

beforeEach(() => {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
  );
});

/** Reloj que avanza solo, para que `findBy*` y `waitFor` funcionen. */
function relojAutomatico() {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(AHORA_ISO);
  });
  afterEach(() => {
    vi.useRealTimers();
  });
}

function veintiuno(): ReturnType<typeof pacienteFicha>[] {
  return Array.from({ length: 21 }, (_, i) =>
    pacienteFicha({
      id: `00000000-0000-4000-8000-0000000001${String(i).padStart(2, "0")}`,
      apellido: `Imaginaria${String(i).padStart(2, "0")}`,
      documento: `0000${String(1000 + i)}`,
    }),
  );
}

async function avanzar(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("Pacientes: listado", () => {
  relojAutomatico();

  async function abrir(lista: unknown[] = [CARLA]): Promise<{
    api: ApiFalsa;
    user: ReturnType<typeof renderizarApp>["user"];
  }> {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: lista });
    const { user } = renderizarApp(RUTA);
    return { api, user };
  }

  it("la primera carga pide limite=21, desplazamiento=0 y no manda q", async () => {
    const { api } = await abrir();
    await screen.findByRole("table");

    const [pedido] = api.pedidos("GET /pacientes");
    expect(api.pedidos("GET /pacientes")).toHaveLength(1);
    expect(pedido?.parametros.get("limite")).toBe("21");
    expect(pedido?.parametros.get("desplazamiento")).toBe("0");
    expect(pedido?.parametros.has("q")).toBe(false);
  });

  it("muestra los datos de cada paciente, y Sin email si no tiene", async () => {
    await abrir();
    await screen.findByRole("table");

    const fila = screen.getByRole("row", { name: /Imaginaria, Carla/ });
    expect(within(fila).getByText("00000104")).toBeInTheDocument();
    expect(within(fila).getByText("011-0000-0104")).toBeInTheDocument();
    expect(within(fila).getByText("Sin email")).toBeInTheDocument();
  });

  it("muestra el email cuando existe", async () => {
    await abrir([pacienteFicha({ email: "carla@ejemplo.test" })]);

    expect(await screen.findByText("carla@ejemplo.test")).toBeInTheDocument();
    expect(screen.queryByText("Sin email")).not.toBeInTheDocument();
  });

  it("sin pacientes y sin búsqueda muestra el mensaje de la pantalla", async () => {
    await abrir([]);

    expect(
      await screen.findByText("Todavía no hay pacientes registrados."),
    ).toBeInTheDocument();
  });

  it("21 pacientes: muestra 20 filas, Página 1, Siguiente habilitado y Anterior no", async () => {
    await abrir(veintiuno());
    await screen.findByRole("table");

    expect(screen.getAllByRole("row")).toHaveLength(21);
    expect(screen.getByText("Página 1")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
  });

  it("20 pacientes exactos: sin Siguiente", async () => {
    await abrir(veintiuno().slice(0, 20));
    await screen.findByRole("table");

    expect(screen.getAllByRole("row")).toHaveLength(21);
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
  });

  it("avanza y vuelve pidiendo desplazamiento=20 y luego 0", async () => {
    const { api, user } = await abrir(veintiuno());
    await screen.findByRole("table");

    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await screen.findByText("Página 2");
    expect(
      api.pedidos("GET /pacientes").at(-1)?.parametros.get("desplazamiento"),
    ).toBe("20");
    await user.click(screen.getByRole("button", { name: "Anterior" }));
    await screen.findByText("Página 1");

    expect(
      api.pedidos("GET /pacientes").at(-1)?.parametros.get("desplazamiento"),
    ).toBe("0");
  });

  it("falla de red: muestra el error con Reintentar", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { red: true });

    renderizarApp(RUTA);

    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reintentar" }),
    ).toBeInTheDocument();
  });
});

describe("Pacientes: búsqueda", () => {
  usarRelojManual();

  async function abrir() {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [CARLA] });
    const vista = renderizarApp(RUTA);
    await avanzar(50);
    expect(screen.getByRole("table")).toBeInTheDocument();
    return { api, ...vista };
  }

  it("espera 300 ms tras la última tecla antes de buscar con q", async () => {
    const { api, user } = await abrir();

    await user.type(screen.getByLabelText("Buscar"), "pe");
    await avanzar(299);
    expect(api.pedidos("GET /pacientes")).toHaveLength(1);
    await avanzar(1);

    const pedidos = api.pedidos("GET /pacientes");
    expect(pedidos).toHaveLength(2);
    expect(pedidos[1]?.parametros.get("q")).toBe("pe");
    expect(pedidos[1]?.parametros.get("limite")).toBe("21");
    expect(pedidos[1]?.parametros.get("desplazamiento")).toBe("0");
  });

  it("busca con un solo carácter", async () => {
    const { api, user } = await abrir();

    await user.type(screen.getByLabelText("Buscar"), "4");
    await avanzar(300);

    expect(api.pedidos("GET /pacientes").at(-1)?.parametros.get("q")).toBe("4");
  });

  it("cada tecla reinicia la espera: se busca una sola vez con el texto final", async () => {
    const { api, user } = await abrir();

    await user.type(screen.getByLabelText("Buscar"), "p");
    await avanzar(200);
    await user.type(screen.getByLabelText("Buscar"), "e");
    await avanzar(200);
    expect(api.pedidos("GET /pacientes")).toHaveLength(1);
    await avanzar(100);

    expect(api.pedidos("GET /pacientes")).toHaveLength(2);
    expect(api.pedidos("GET /pacientes").at(-1)?.parametros.get("q")).toBe(
      "pe",
    );
  });

  it("un texto en blanco vuelve a listar sin q", async () => {
    const { api, user } = await abrir();
    await user.type(screen.getByLabelText("Buscar"), "pe");
    await avanzar(300);

    const campo = screen.getByLabelText("Buscar");
    await user.clear(campo);
    await user.type(campo, "   ");
    await avanzar(300);

    expect(api.pedidos("GET /pacientes").at(-1)?.parametros.has("q")).toBe(
      false,
    );
  });

  it("recorta los espacios de los extremos", async () => {
    const { api, user } = await abrir();

    await user.type(screen.getByLabelText("Buscar"), "  pe ");
    await avanzar(300);

    expect(api.pedidos("GET /pacientes").at(-1)?.parametros.get("q")).toBe(
      "pe",
    );
  });

  it("limita la búsqueda a 100 caracteres y es un campo de búsqueda", async () => {
    await abrir();

    const campo = screen.getByLabelText("Buscar");
    expect(campo).toHaveAttribute("type", "search");
    expect(campo).toHaveAttribute("maxLength", "100");
  });

  it("sin resultados muestra No se encontraron pacientes.", async () => {
    const { api, user } = await abrir();
    api.responder("GET /pacientes", { status: 200, cuerpo: [] });

    await user.type(screen.getByLabelText("Buscar"), "zzz");
    await avanzar(300);

    expect(
      screen.getByText("No se encontraron pacientes."),
    ).toBeInTheDocument();
  });

  it("con búsquedas fuera de orden se ven los resultados de la última", async () => {
    const { api, user } = await abrir();
    const viejo = api.pendiente("GET /pacientes");
    const nuevo = api.pendiente("GET /pacientes");

    await user.type(screen.getByLabelText("Buscar"), "pe");
    await avanzar(300);
    await user.type(screen.getByLabelText("Buscar"), "r");
    await avanzar(300);
    await act(async () => {
      nuevo.resolver({
        status: 200,
        cuerpo: [pacienteFicha({ apellido: "Per", nombre: "Nueva" })],
      });
    });
    await avanzar(10);
    await act(async () => {
      viejo.resolver({
        status: 200,
        cuerpo: [pacienteFicha({ apellido: "Pe", nombre: "Vieja" })],
      });
    });
    await avanzar(10);

    expect(screen.getByText("Per, Nueva")).toBeInTheDocument();
    expect(screen.queryByText("Pe, Vieja")).not.toBeInTheDocument();
  });

  it("una búsqueda desde la página 2 vuelve a la página 1", async () => {
    const { api, user } = await abrir();
    api.responder("GET /pacientes", { status: 200, cuerpo: veintiuno() });
    await user.type(screen.getByLabelText("Buscar"), "i");
    await avanzar(300);
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await avanzar(50);
    expect(screen.getByText("Página 2")).toBeInTheDocument();

    const campo = screen.getByLabelText("Buscar");
    await user.clear(campo);
    await user.type(campo, "pe");
    await avanzar(300);

    const ultimo = api.pedidos("GET /pacientes").at(-1);
    expect(ultimo?.parametros.get("desplazamiento")).toBe("0");
    expect(ultimo?.parametros.get("q")).toBe("pe");
    expect(screen.getByText("Página 1")).toBeInTheDocument();
  });

  it("la URL sigue siendo /pacientes, sin parámetros, tras buscar y avanzar", async () => {
    const { api, user } = await abrir();
    api.responder("GET /pacientes", { status: 200, cuerpo: veintiuno() });
    await user.type(screen.getByLabelText("Buscar"), "Imaginaria");
    await avanzar(300);
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await avanzar(50);

    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/pacientes");
    expect(screen.getByTestId("busqueda")).toBeEmptyDOMElement();
  });

  it("una búsqueda que falla no escribe datos del paciente en la consola", async () => {
    const espias = (["log", "info", "warn", "error", "debug"] as const).map(
      (metodo) => vi.spyOn(console, metodo).mockImplementation(() => {}),
    );
    const { api, user } = await abrir();
    api.responder("GET /pacientes", { red: true });

    await user.type(screen.getByLabelText("Buscar"), "Imaginaria");
    await avanzar(300);

    expect(
      screen.getByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    for (const espia of espias)
      for (const llamada of espia.mock.calls)
        expect(JSON.stringify(llamada)).not.toContain("Imaginaria");
  });
});

describe("Pacientes: alta, edición y desactivación", () => {
  relojAutomatico();

  async function abrir(lista: unknown[] = [CARLA]) {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: lista });
    const vista = renderizarApp(RUTA);
    await screen.findByRole("table");
    return { api, ...vista };
  }

  async function abrirAlta() {
    const vista = await abrir();
    await vista.user.click(
      screen.getByRole("button", { name: "Nuevo paciente" }),
    );
    return {
      ...vista,
      dialogo: screen.getByRole("dialog", { name: "Nuevo paciente" }),
    };
  }

  async function llenar(
    dialogo: HTMLElement,
    user: ReturnType<typeof renderizarApp>["user"],
    email = "",
  ) {
    await user.type(within(dialogo).getByLabelText("Nombre"), "Carla");
    await user.type(within(dialogo).getByLabelText("Apellido"), "Imaginaria");
    await user.type(within(dialogo).getByLabelText("Documento"), "00000104");
    await user.type(
      within(dialogo).getByLabelText("Teléfono"),
      "011-0000-0104",
    );
    if (email !== "")
      await user.type(within(dialogo).getByLabelText("Email"), email);
  }

  it("limita los largos: 100, 100, 20, 30 y 254", async () => {
    const { dialogo } = await abrirAlta();

    const largos: Array<[string, string]> = [
      ["Nombre", "100"],
      ["Apellido", "100"],
      ["Documento", "20"],
      ["Teléfono", "30"],
      ["Email", "254"],
    ];
    for (const [etiqueta, largo] of largos)
      expect(within(dialogo).getByLabelText(etiqueta)).toHaveAttribute(
        "maxLength",
        largo,
      );
  });

  it("el alta sin email lo omite del cuerpo y avisa Paciente guardado.", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /pacientes", { status: 201, cuerpo: CARLA });
    await llenar(dialogo, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Paciente guardado.")).toBeInTheDocument();
    expect(api.pedidos("POST /pacientes")[0]?.cuerpo).toEqual({
      nombre: "Carla",
      apellido: "Imaginaria",
      documento: "00000104",
      telefono: "011-0000-0104",
    });
  });

  it("el alta con email lo envía", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /pacientes", { status: 201, cuerpo: CARLA });
    await llenar(dialogo, user, "carla@ejemplo.test");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Paciente guardado.");
    expect(api.pedidos("POST /pacientes")[0]?.cuerpo).toMatchObject({
      email: "carla@ejemplo.test",
    });
  });

  it("un obligatorio vacío no hace pedidos", async () => {
    const { api, user, dialogo } = await abrirAlta();
    await user.type(within(dialogo).getByLabelText("Nombre"), "Carla");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    for (const etiqueta of ["Apellido", "Documento", "Teléfono"])
      expect(
        within(dialogo).getByLabelText(etiqueta),
      ).toHaveAccessibleDescription("Completá este campo.");
    expect(within(dialogo).getByLabelText("Email")).not.toBeInvalid();
    expect(api.pedidos("POST /pacientes")).toHaveLength(0);
  });

  it("un documento repetido marca Documento y conserva el diálogo", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /pacientes", {
      status: 409,
      cuerpo: { detail: { codigo: "recurso_duplicado", campo: "documento" } },
    });
    await llenar(dialogo, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(
        within(dialogo).getByLabelText("Documento"),
      ).toHaveAccessibleDescription(
        "Ya existe un paciente con ese documento, activo o desactivado.",
      ),
    );
    expect(
      screen.getByRole("dialog", { name: "Nuevo paciente" }),
    ).toBeVisible();
  });

  it("un 422 sobre el email marca Email sin mostrar el msg de la API", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /pacientes", {
      status: 422,
      cuerpo: {
        detail: [
          {
            loc: ["body", "email"],
            msg: "el email debe tener la forma algo@algo, sin espacios",
            type: "value_error",
          },
        ],
      },
    });
    await llenar(dialogo, user, "carla@ejemplo.test");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(
        within(dialogo).getByLabelText("Email"),
      ).toHaveAccessibleDescription("Revisá este campo."),
    );
    expect(screen.queryByText(/algo@algo/)).not.toBeInTheDocument();
  });

  it("un 422 sin campo muestra Revisá los datos ingresados. con rol alert", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /pacientes", {
      status: 422,
      cuerpo: {
        detail: [{ loc: ["body"], msg: "Field required", type: "missing" }],
      },
    });
    await llenar(dialogo, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(
      "Revisá los datos ingresados.",
    );
  });

  it("al vaciar el email en la edición envía email null", async () => {
    const { api, user } = await abrir([
      pacienteFicha({ email: "carla@ejemplo.test" }),
    ]);
    api.responder(`PATCH /pacientes/${ID_CARLA}`, {
      status: 200,
      cuerpo: CARLA,
    });
    await user.click(
      screen.getByRole("button", {
        name: "Editar Imaginaria, Carla (00000104)",
      }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Editar paciente" });
    expect(within(dialogo).getByLabelText("Email")).toHaveValue(
      "carla@ejemplo.test",
    );

    await user.clear(within(dialogo).getByLabelText("Email"));
    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Paciente guardado.");
    expect(api.pedidos(`PATCH /pacientes/${ID_CARLA}`)[0]?.cuerpo).toEqual({
      email: null,
    });
  });

  it("corrige el documento de un paciente desactivado", async () => {
    const { api, user } = await abrir([pacienteFicha({ activo: false })]);
    api.responder(`PATCH /pacientes/${ID_CARLA}`, {
      status: 200,
      cuerpo: CARLA,
    });
    expect(
      screen.queryByRole("button", {
        name: "Desactivar Imaginaria, Carla (00000104)",
      }),
    ).not.toBeInTheDocument();

    await user.click(
      screen.getByRole("button", {
        name: "Editar Imaginaria, Carla (00000104)",
      }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Editar paciente" });
    const documento = within(dialogo).getByLabelText("Documento");
    await user.clear(documento);
    await user.type(documento, "00000105");
    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Paciente guardado.");
    expect(api.pedidos(`PATCH /pacientes/${ID_CARLA}`)[0]?.cuerpo).toEqual({
      documento: "00000105",
    });
  });

  it("sin cambios no hace el PATCH", async () => {
    const { api, user } = await abrir();
    await user.click(
      screen.getByRole("button", {
        name: "Editar Imaginaria, Carla (00000104)",
      }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Editar paciente" });

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      within(dialogo).getByText("No hiciste cambios."),
    ).toBeInTheDocument();
    expect(api.pedidos(`PATCH /pacientes/${ID_CARLA}`)).toHaveLength(0);
  });

  it("dos homónimos tienen botones distintos por el documento", async () => {
    await abrir([CARLA, OTRA_CARLA]);

    for (const documento of ["00000104", "00000105"])
      for (const accion of ["Editar", "Desactivar"])
        expect(
          screen.getAllByRole("button", {
            name: `${accion} Imaginaria, Carla (${documento})`,
          }),
        ).toHaveLength(1);
  });

  it("desactivar muestra el texto, hace el POST, avisa y relee la página y la búsqueda actuales", async () => {
    const { api, user } = await abrir();
    api.responder(`POST /pacientes/${ID_CARLA}/desactivar`, {
      status: 200,
      cuerpo: { ...CARLA, activo: false },
    });
    await user.click(
      screen.getByRole("button", {
        name: "Desactivar Imaginaria, Carla (00000104)",
      }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Desactivar paciente" });
    expect(
      within(dialogo).getByText(
        "No va a poder recibir turnos nuevos. Sus turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.",
      ),
    ).toBeInTheDocument();

    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar desactivación" }),
    );

    expect(
      await screen.findByText("Paciente desactivado."),
    ).toBeInTheDocument();
    expect(api.pedidos(`POST /pacientes/${ID_CARLA}/desactivar`)).toHaveLength(
      1,
    );
    await waitFor(() => expect(api.pedidos("GET /pacientes")).toHaveLength(2));
    const [primero, segundo] = api.pedidos("GET /pacientes");
    expect(segundo?.parametros.toString()).toBe(primero?.parametros.toString());
  });
});
