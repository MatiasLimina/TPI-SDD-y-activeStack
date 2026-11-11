import { fireEvent, screen, waitFor, within } from "@testing-library/react";

import { CLAVE_TOKEN } from "../features/sesion/almacenamiento";
import { instalarApiFalsa } from "../test/apiFalsa";
import {
  bloqueo,
  ID_ANA,
  ID_BLOQUEO,
  ID_LUIS,
  profesionalConMatricula,
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
const ANA = profesionalConMatricula({ id: ID_ANA });
const LUIS = profesionalConMatricula({
  id: ID_LUIS,
  nombre: "Luis",
  apellido: "Inventado",
  activo: false,
});
const ID_BLOQUEO_2 = "00000000-0000-4000-8000-0000000000f8";
const ID_BLOQUEO_3 = "00000000-0000-4000-8000-0000000000f7";
const MENSAJE_TURNOS =
  "Hay turnos activos en ese intervalo: reprogramalos o cancelalos antes de bloquear.";

function comoRecepcionista() {
  sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(VIGENTE));
}

function comoOdontologo() {
  sessionStorage.setItem(CLAVE_TOKEN, tokenDeOdontologo(VIGENTE));
}

function api(bloqueos: unknown[] = [bloqueo()]) {
  const falsa = instalarApiFalsa();
  falsa.responder("GET /profesionales", { status: 200, cuerpo: [ANA, LUIS] });
  falsa.responder("GET /bloqueos", { status: 200, cuerpo: bloqueos });
  return falsa;
}

describe("Bloqueos: pantalla y listado", () => {
  beforeEach(comoRecepcionista);

  it("muestra la hora local aunque la suite corra en otra zona", async () => {
    api([
      bloqueo({
        inicio: "2026-11-09T18:00:00Z",
        fin: "2026-11-09T19:00:00Z",
        motivo: "Congreso",
      }),
    ]);

    renderizarApp("/bloqueos");

    const fila = await screen.findByRole("row", { name: /Ficticia, Ana/ });
    expect(within(fila).getByText("09/11/2026 15:00")).toBeInTheDocument();
    expect(within(fila).getByText("09/11/2026 16:00")).toBeInTheDocument();
    expect(within(fila).getByText("Congreso")).toBeInTheDocument();
  });

  it("pide los profesionales y los bloqueos al montarse", async () => {
    const falsa = api();

    renderizarApp("/bloqueos");

    await screen.findByRole("table");
    expect(falsa.pedidos("GET /profesionales")).toHaveLength(1);
    expect(falsa.pedidos("GET /bloqueos")).toHaveLength(1);
  });

  it("un profesional fuera del catálogo se ve como Profesional no disponible, sin el id", async () => {
    const ID_FUERA = "00000000-0000-4000-8000-0000000000ee";
    api([bloqueo({ profesional_id: ID_FUERA })]);

    renderizarApp("/bloqueos");

    expect(await screen.findByText("Profesional no disponible")).toBeVisible();
    expect(screen.queryByText(new RegExp(ID_FUERA))).not.toBeInTheDocument();
  });

  it("el filtro arranca en Todos y no manda profesional_id", async () => {
    const falsa = api();

    renderizarApp("/bloqueos");

    await screen.findByRole("table");
    expect(screen.getByLabelText("Profesional")).toHaveDisplayValue("Todos");
    expect(
      falsa.pedidos("GET /bloqueos")[0]?.parametros.has("profesional_id"),
    ).toBe(false);
  });

  it("filtrar por un profesional guarda el id en la URL y lo manda como profesional_id", async () => {
    const falsa = api();
    const { user } = renderizarApp("/bloqueos");
    await screen.findByRole("option", { name: "Ficticia, Ana" });

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );

    await waitFor(() =>
      expect(
        falsa.pedidos("GET /bloqueos").at(-1)?.parametros.get("profesional_id"),
      ).toBe(ID_ANA),
    );
    expect(screen.getByTestId("busqueda")).toHaveTextContent(
      `profesional=${ID_ANA}`,
    );
  });

  it("el filtro ofrece a los profesionales inactivos marcados", async () => {
    api();

    renderizarApp("/bloqueos");

    expect(
      await screen.findByRole("option", { name: "Inventado, Luis (inactivo)" }),
    ).toBeInTheDocument();
  });

  it("un parámetro mal formado se ignora", async () => {
    const falsa = api();

    renderizarApp("/bloqueos?profesional=no-es-un-id");

    await screen.findByRole("table");
    expect(screen.getByLabelText("Profesional")).toHaveDisplayValue("Todos");
    expect(
      falsa.pedidos("GET /bloqueos")[0]?.parametros.has("profesional_id"),
    ).toBe(false);
  });

  it("el título de la recepcionista es Bloqueos", async () => {
    api();

    renderizarApp("/bloqueos");

    expect(
      await screen.findByRole("heading", { level: 1, name: "Bloqueos" }),
    ).toBeInTheDocument();
  });

  it("no ofrece una acción Editar", async () => {
    api();

    renderizarApp("/bloqueos");

    await screen.findByRole("table");
    expect(
      screen.queryByRole("button", { name: /Editar/ }),
    ).not.toBeInTheDocument();
  });
});

describe("Bloqueos: terminados", () => {
  beforeEach(comoRecepcionista);

  const TERMINADO = bloqueo({
    id: ID_BLOQUEO_2,
    inicio: "2026-11-09T08:00:00-03:00",
    fin: "2026-11-09T09:00:00-03:00",
    motivo: "Terminado",
  });
  const VIGENTE_AHORA = bloqueo({
    id: ID_BLOQUEO,
    inicio: "2026-11-09T08:30:00-03:00",
    fin: "2026-11-09T09:30:00-03:00",
    motivo: "En curso",
  });

  it("oculta el que termina justo ahora y muestra el que sigue", async () => {
    api([TERMINADO, VIGENTE_AHORA]);

    renderizarApp("/bloqueos");

    expect(await screen.findByText("En curso")).toBeVisible();
    expect(screen.queryByText("Terminado")).not.toBeInTheDocument();
  });

  it("la casilla muestra ambos sin un segundo GET /bloqueos", async () => {
    const falsa = api([TERMINADO, VIGENTE_AHORA]);
    const { user } = renderizarApp("/bloqueos");
    await screen.findByText("En curso");

    await user.click(screen.getByLabelText("Mostrar bloqueos terminados"));

    expect(screen.getByText("Terminado")).toBeVisible();
    expect(screen.getByText("En curso")).toBeVisible();
    expect(falsa.pedidos("GET /bloqueos")).toHaveLength(1);
  });

  it("si todos terminaron, lo dice", async () => {
    api([
      bloqueo({
        inicio: "2026-11-08T09:00:00-03:00",
        fin: "2026-11-08T10:00:00-03:00",
      }),
    ]);

    renderizarApp("/bloqueos");

    expect(
      await screen.findByText("No hay bloqueos vigentes ni próximos."),
    ).toBeInTheDocument();
  });

  it("si no hay ninguno, dice que no hay bloqueos cargados", async () => {
    api([]);

    renderizarApp("/bloqueos");

    expect(
      await screen.findByText("No hay bloqueos cargados."),
    ).toBeInTheDocument();
  });
});

describe("Bloqueos del odontólogo", () => {
  beforeEach(comoOdontologo);

  it("titula Mis bloqueos, no manda profesional_id aunque la URL lo traiga y no ofrece selector", async () => {
    const falsa = api();

    renderizarApp(`/bloqueos?profesional=${ID_LUIS}`);

    expect(
      await screen.findByRole("heading", { level: 1, name: "Mis bloqueos" }),
    ).toBeInTheDocument();
    await screen.findByRole("table");
    expect(
      falsa.pedidos("GET /bloqueos")[0]?.parametros.has("profesional_id"),
    ).toBe(false);
    expect(screen.queryByLabelText("Profesional")).not.toBeInTheDocument();
  });

  it("el formulario no tiene el campo Profesional y el cuerpo no manda profesional_id", async () => {
    const falsa = api();
    falsa.responder("POST /bloqueos", { status: 201, cuerpo: bloqueo() });
    const { user } = renderizarApp("/bloqueos");
    await screen.findByRole("table");

    await user.click(screen.getByRole("button", { name: "Nuevo bloqueo" }));
    const dialogo = screen.getByRole("dialog", { name: "Nuevo bloqueo" });
    expect(
      within(dialogo).queryByLabelText("Profesional"),
    ).not.toBeInTheDocument();
    fireEvent.change(within(dialogo).getByLabelText("Fecha desde"), {
      target: { value: "2026-11-12" },
    });
    fireEvent.change(within(dialogo).getByLabelText("Hora desde"), {
      target: { value: "10:00" },
    });
    fireEvent.change(within(dialogo).getByLabelText("Fecha hasta"), {
      target: { value: "2026-11-13" },
    });
    fireEvent.change(within(dialogo).getByLabelText("Hora hasta"), {
      target: { value: "18:00" },
    });
    fireEvent.change(within(dialogo).getByLabelText("Motivo"), {
      target: { value: "Congreso" },
    });
    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Bloqueo creado.");
    const cuerpo = falsa.pedidos("POST /bloqueos")[0]?.cuerpo;
    expect(cuerpo).toEqual({
      inicio: "2026-11-12T10:00:00-03:00",
      fin: "2026-11-13T18:00:00-03:00",
      motivo: "Congreso",
    });
  });

  it("borrar un bloqueo que ya no es suyo (403) avisa, relee y mantiene la sesión", async () => {
    const falsa = api();
    falsa.responder(`DELETE /bloqueos/${ID_BLOQUEO}`, {
      status: 403,
      cuerpo: { detail: { codigo: "profesional_ajeno", mensaje: "x" } },
    });
    const { user } = renderizarApp("/bloqueos");
    await screen.findByRole("table");
    await user.click(
      screen.getByRole("button", {
        name: "Borrar bloqueo de Ficticia, Ana del 09/11/2026 15:00 al 09/11/2026 16:00",
      }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Borrar bloqueo" });

    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar borrado" }),
    );

    expect(
      await within(dialogo).findByText("No tenés permiso para esta operación."),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).not.toBeNull();
    await waitFor(() => expect(falsa.pedidos("GET /bloqueos")).toHaveLength(2));
  });
});

describe("Bloqueos: alta de la recepcionista", () => {
  beforeEach(comoRecepcionista);

  async function abrirAlta(bloqueos?: unknown[]) {
    const falsa = api(bloqueos);
    const vista = renderizarApp("/bloqueos");
    await screen.findByRole("option", { name: "Ficticia, Ana" });
    await waitFor(() =>
      expect(screen.queryByText("Cargando…")).not.toBeInTheDocument(),
    );
    await vista.user.click(
      screen.getByRole("button", { name: "Nuevo bloqueo" }),
    );
    return {
      falsa,
      ...vista,
      dialogo: screen.getByRole("dialog", { name: "Nuevo bloqueo" }),
    };
  }

  function completar(
    dialogo: HTMLElement,
    valores: {
      profesional?: string;
      fechaDesde: string;
      horaDesde: string;
      fechaHasta: string;
      horaHasta: string;
      motivo: string;
    },
    user: ReturnType<typeof renderizarApp>["user"],
  ) {
    const cambiar = (etiqueta: string, value: string) =>
      fireEvent.change(within(dialogo).getByLabelText(etiqueta), {
        target: { value },
      });
    cambiar("Fecha desde", valores.fechaDesde);
    cambiar("Hora desde", valores.horaDesde);
    cambiar("Fecha hasta", valores.fechaHasta);
    cambiar("Hora hasta", valores.horaHasta);
    cambiar("Motivo", valores.motivo);
    if (valores.profesional !== undefined)
      return user.selectOptions(
        within(dialogo).getByLabelText("Profesional"),
        valores.profesional,
      );
    return Promise.resolve();
  }

  const DATOS = {
    fechaDesde: "2026-11-12",
    horaDesde: "10:03",
    fechaHasta: "2026-11-12",
    horaHasta: "10:07",
    motivo: "Trámite",
  };

  it("las fechas arrancan en el día actual del consultorio y las horas vacías", async () => {
    vi.setSystemTime("2026-11-10T02:00:00Z");
    // El token del beforeEach vence antes de esta hora
    sessionStorage.setItem(
      CLAVE_TOKEN,
      tokenDeRecepcionista(AHORA_SEGUNDOS + 2 * 24 * 3600),
    );

    const { dialogo } = await abrirAlta();

    expect(within(dialogo).getByLabelText("Fecha desde")).toHaveValue(
      "2026-11-09",
    );
    expect(within(dialogo).getByLabelText("Fecha hasta")).toHaveValue(
      "2026-11-09",
    );
    expect(within(dialogo).getByLabelText("Hora desde")).toHaveValue("");
    expect(within(dialogo).getByLabelText("Hora hasta")).toHaveValue("");
  });

  it("las horas admiten cualquier minuto y el motivo limita a 255", async () => {
    const { dialogo } = await abrirAlta();

    expect(within(dialogo).getByLabelText("Hora desde")).toHaveAttribute(
      "step",
      "60",
    );
    expect(within(dialogo).getByLabelText("Motivo")).toHaveAttribute(
      "maxLength",
      "255",
    );
  });

  it("envía el cuerpo con el profesional elegido y el desfasaje del consultorio", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    falsa.responder("POST /bloqueos", { status: 201, cuerpo: bloqueo() });
    await completar(dialogo, { ...DATOS, profesional: "Ficticia, Ana" }, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Bloqueo creado.")).toBeInTheDocument();
    expect(falsa.pedidos("POST /bloqueos")[0]?.cuerpo).toEqual({
      profesional_id: ID_ANA,
      inicio: "2026-11-12T10:03:00-03:00",
      fin: "2026-11-12T10:07:00-03:00",
      motivo: "Trámite",
    });
    await waitFor(() => expect(falsa.pedidos("GET /bloqueos")).toHaveLength(2));
  });

  it("permite bloquear a un profesional inactivo", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    falsa.responder("POST /bloqueos", { status: 201, cuerpo: bloqueo() });
    await completar(
      dialogo,
      { ...DATOS, profesional: "Inventado, Luis (inactivo)" },
      user,
    );

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Bloqueo creado.");
    expect(falsa.pedidos("POST /bloqueos")[0]?.cuerpo).toMatchObject({
      profesional_id: ID_LUIS,
    });
  });

  it("sin elegir profesional marca el campo y no hace pedidos", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    await completar(dialogo, DATOS, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      within(dialogo).getByLabelText("Profesional"),
    ).toHaveAccessibleDescription("Completá este campo.");
    expect(falsa.pedidos("POST /bloqueos")).toHaveLength(0);
  });

  it("un campo obligatorio vacío (motivo) no hace pedidos", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    await completar(
      dialogo,
      { ...DATOS, motivo: "", profesional: "Ficticia, Ana" },
      user,
    );

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      within(dialogo).getByLabelText("Motivo"),
    ).toHaveAccessibleDescription("Completá este campo.");
    expect(falsa.pedidos("POST /bloqueos")).toHaveLength(0);
  });

  it("bloqueo_invalido se muestra como error general y conserva los datos", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    falsa.responder("POST /bloqueos", {
      status: 422,
      cuerpo: { detail: { codigo: "bloqueo_invalido", mensaje: "..." } },
    });
    await completar(dialogo, { ...DATOS, profesional: "Ficticia, Ana" }, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await within(dialogo).findByText(
        "El bloqueo debe terminar después de empezar y tener un motivo.",
      ),
    ).toBeInTheDocument();
    expect(within(dialogo).getByLabelText("Motivo")).toHaveValue("Trámite");
    expect(within(dialogo).getByLabelText("Hora desde")).toHaveValue("10:03");
  });

  it("profesional_requerido marca Profesional sin mostrar el mensaje de la API", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    falsa.responder("POST /bloqueos", {
      status: 422,
      cuerpo: {
        detail: {
          codigo: "profesional_requerido",
          mensaje: "indicá el profesional del bloqueo",
        },
      },
    });
    await completar(dialogo, { ...DATOS, profesional: "Ficticia, Ana" }, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(
        within(dialogo).getByLabelText("Profesional"),
      ).toHaveAccessibleDescription("Completá este campo."),
    );
    expect(screen.queryByText(/indicá el profesional/)).not.toBeInTheDocument();
    expect(within(dialogo).getByLabelText("Motivo")).toHaveValue("Trámite");
  });

  it("referencia_invalida marca Profesional y relee los profesionales", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    falsa.responder("POST /bloqueos", {
      status: 422,
      cuerpo: {
        detail: {
          codigo: "referencia_invalida",
          referencia: "profesional",
          motivo: "inexistente",
        },
      },
    });
    await completar(dialogo, { ...DATOS, profesional: "Ficticia, Ana" }, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(
        within(dialogo).getByLabelText("Profesional"),
      ).toHaveAccessibleDescription("El profesional ya no existe."),
    );
    expect(falsa.pedidos("GET /profesionales")).toHaveLength(2);
  });

  it("un 403 profesional_ajeno al crear conserva el diálogo y la sesión", async () => {
    const { falsa, user, dialogo } = await abrirAlta();
    falsa.responder("POST /bloqueos", {
      status: 403,
      cuerpo: { detail: { codigo: "profesional_ajeno", mensaje: "x" } },
    });
    await completar(dialogo, { ...DATOS, profesional: "Ficticia, Ana" }, user);

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await within(dialogo).findByText("No tenés permiso para esta operación."),
    ).toBeInTheDocument();
    expect(within(dialogo).getByLabelText("Motivo")).toHaveValue("Trámite");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).not.toBeNull();
  });

  describe("bloqueo creado que ya terminó", () => {
    const YA_TERMINADO = bloqueo({
      id: ID_BLOQUEO_3,
      inicio: "2026-11-08T10:00:00-03:00",
      fin: "2026-11-08T12:00:00-03:00",
      motivo: "Licencia",
    });
    const PASADO = {
      profesional: "Ficticia, Ana",
      fechaDesde: "2026-11-08",
      horaDesde: "10:00",
      fechaHasta: "2026-11-08",
      horaHasta: "12:00",
      motivo: "Licencia",
    };

    it("con la casilla desmarcada avisa que está oculto y no cambia la casilla", async () => {
      const { falsa, user, dialogo } = await abrirAlta([]);
      falsa.responder("POST /bloqueos", { status: 201, cuerpo: YA_TERMINADO });
      falsa.responder("GET /bloqueos", { status: 200, cuerpo: [YA_TERMINADO] });
      await completar(dialogo, PASADO, user);

      await user.click(
        within(dialogo).getByRole("button", { name: "Guardar" }),
      );

      expect(
        await screen.findByText(
          "Bloqueo creado. Está oculto porque ya terminó.",
        ),
      ).toBeInTheDocument();
      await waitFor(() =>
        expect(falsa.pedidos("GET /bloqueos")).toHaveLength(2),
      );
      expect(
        screen.getByLabelText("Mostrar bloqueos terminados"),
      ).not.toBeChecked();
      expect(screen.queryByText("Licencia")).not.toBeInTheDocument();
    });

    it("con la casilla marcada avisa Bloqueo creado. y el bloqueo aparece", async () => {
      const { falsa, user, dialogo } = await abrirAlta([]);
      falsa.responder("POST /bloqueos", { status: 201, cuerpo: YA_TERMINADO });
      falsa.responder("GET /bloqueos", { status: 200, cuerpo: [YA_TERMINADO] });
      await user.click(screen.getByLabelText("Mostrar bloqueos terminados"));
      await completar(dialogo, PASADO, user);

      await user.click(
        within(dialogo).getByRole("button", { name: "Guardar" }),
      );

      expect(await screen.findByText("Bloqueo creado.")).toBeInTheDocument();
      expect(await screen.findByText("Licencia")).toBeVisible();
    });
  });
});

describe("Bloqueos: bloqueo sobre turnos activos", () => {
  const TURNO_1 = {
    id: "00000000-0000-4000-8000-0000000000f1",
    inicio: "2026-11-12T10:30:00-03:00",
    fin: "2026-11-12T11:15:00-03:00",
  };
  const TURNO_2 = {
    id: "00000000-0000-4000-8000-0000000000f2",
    inicio: "2026-11-13T09:00:00-03:00",
    fin: "2026-11-13T09:30:00-03:00",
  };

  async function enviarConConflicto(
    rol: "recepcionista" | "odontologo",
    turnos: unknown[],
    hasta = "2026-11-12",
  ) {
    if (rol === "recepcionista") comoRecepcionista();
    else comoOdontologo();
    const falsa = api();
    falsa.responder("POST /bloqueos", {
      status: 409,
      cuerpo: { detail: { codigo: "bloqueo_con_turnos", turnos } },
    });
    const vista = renderizarApp("/bloqueos");
    await screen.findByRole("table");
    await vista.user.click(
      screen.getByRole("button", { name: "Nuevo bloqueo" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Nuevo bloqueo" });
    const cambiar = (etiqueta: string, value: string) =>
      fireEvent.change(within(dialogo).getByLabelText(etiqueta), {
        target: { value },
      });
    cambiar("Fecha desde", "2026-11-12");
    cambiar("Hora desde", "10:00");
    cambiar("Fecha hasta", hasta);
    cambiar("Hora hasta", "12:00");
    cambiar("Motivo", "Congreso");
    if (rol === "recepcionista")
      await vista.user.selectOptions(
        within(dialogo).getByLabelText("Profesional"),
        "Ficticia, Ana",
      );
    await vista.user.click(
      within(dialogo).getByRole("button", { name: "Guardar" }),
    );
    await within(dialogo).findByText(MENSAJE_TURNOS);
    return { falsa, dialogo, ...vista };
  }

  it("muestra el mensaje, el turno en hora local y el enlace a la agenda del día, sin ids ni pedidos a pacientes", async () => {
    const { falsa, dialogo } = await enviarConConflicto("recepcionista", [
      TURNO_1,
    ]);

    expect(within(dialogo).getByText("12/11/2026 10:30 a 11:15")).toBeVisible();
    const enlace = within(dialogo).getByRole("link", {
      name: "Ver en la agenda",
    });
    expect(enlace).toHaveAttribute(
      "href",
      `/agenda?fecha=2026-11-12&profesional=${ID_ANA}`,
    );
    expect(dialogo.textContent).not.toContain(TURNO_1.id);
    expect(
      falsa.pedidos().filter((p) => p.ruta.startsWith("/pacientes")),
    ).toHaveLength(0);
  });

  it("el enlace del odontólogo no lleva profesional", async () => {
    const { dialogo } = await enviarConConflicto("odontologo", [TURNO_1]);

    expect(
      within(dialogo).getByRole("link", { name: "Ver en la agenda" }),
    ).toHaveAttribute("href", "/agenda?fecha=2026-11-12");
  });

  it("con turnos de días distintos, cada uno enlaza a su fecha", async () => {
    const { dialogo } = await enviarConConflicto(
      "recepcionista",
      [TURNO_1, TURNO_2],
      "2026-11-13",
    );

    const filas = within(dialogo).getAllByRole("listitem");
    expect(filas).toHaveLength(2);
    expect(
      within(filas[0]!).getByText("12/11/2026 10:30 a 11:15"),
    ).toBeVisible();
    expect(within(filas[0]!).getByRole("link")).toHaveAttribute(
      "href",
      `/agenda?fecha=2026-11-12&profesional=${ID_ANA}`,
    );
    expect(
      within(filas[1]!).getByText("13/11/2026 09:00 a 09:30"),
    ).toBeVisible();
    expect(within(filas[1]!).getByRole("link")).toHaveAttribute(
      "href",
      `/agenda?fecha=2026-11-13&profesional=${ID_ANA}`,
    );
  });

  it("el enlace lleva a la agenda de ese día", async () => {
    const { user, dialogo } = await enviarConConflicto("recepcionista", [
      TURNO_1,
    ]);

    await user.click(
      within(dialogo).getByRole("link", { name: "Ver en la agenda" }),
    );

    expect(
      await screen.findByRole("heading", { name: "Agenda" }),
    ).toBeVisible();
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/agenda");
    expect(screen.getByTestId("busqueda")).toHaveTextContent(
      `?fecha=2026-11-12&profesional=${ID_ANA}`,
    );
  });
});

describe("Bloqueos: borrado", () => {
  beforeEach(comoRecepcionista);

  const NOMBRE_ANA_15_16 =
    "Borrar bloqueo de Ficticia, Ana del 12/11/2026 15:00 al 12/11/2026 16:00";

  it("tres bloqueos con el mismo inicio tienen nombres distintos", async () => {
    api([
      bloqueo({
        id: ID_BLOQUEO,
        inicio: "2026-11-12T15:00:00-03:00",
        fin: "2026-11-12T16:00:00-03:00",
      }),
      bloqueo({
        id: ID_BLOQUEO_2,
        profesional_id: ID_LUIS,
        inicio: "2026-11-12T15:00:00-03:00",
        fin: "2026-11-12T16:00:00-03:00",
      }),
      bloqueo({
        id: ID_BLOQUEO_3,
        inicio: "2026-11-12T15:00:00-03:00",
        fin: "2026-11-12T17:00:00-03:00",
      }),
    ]);

    renderizarApp("/bloqueos");
    await screen.findByRole("table");

    for (const nombre of [
      NOMBRE_ANA_15_16,
      "Borrar bloqueo de Inventado, Luis del 12/11/2026 15:00 al 12/11/2026 16:00",
      "Borrar bloqueo de Ficticia, Ana del 12/11/2026 15:00 al 12/11/2026 17:00",
    ])
      expect(screen.getAllByRole("button", { name: nombre })).toHaveLength(1);
  });

  it("confirma con la aclaración, hace el DELETE, avisa y relee", async () => {
    const falsa = api([
      bloqueo({
        inicio: "2026-11-12T15:00:00-03:00",
        fin: "2026-11-12T16:00:00-03:00",
      }),
    ]);
    falsa.responder(`DELETE /bloqueos/${ID_BLOQUEO}`, { status: 204 });
    const { user } = renderizarApp("/bloqueos");
    await screen.findByRole("table");

    await user.click(screen.getByRole("button", { name: NOMBRE_ANA_15_16 }));
    const dialogo = screen.getByRole("dialog", { name: "Borrar bloqueo" });
    expect(
      within(dialogo).getByText("El horario vuelve a admitir turnos."),
    ).toBeInTheDocument();
    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar borrado" }),
    );

    expect(await screen.findByText("Bloqueo borrado.")).toBeInTheDocument();
    expect(falsa.pedidos(`DELETE /bloqueos/${ID_BLOQUEO}`)).toHaveLength(1);
    await waitFor(() => expect(falsa.pedidos("GET /bloqueos")).toHaveLength(2));
  });

  it("Volver no borra nada", async () => {
    const falsa = api([
      bloqueo({
        inicio: "2026-11-12T15:00:00-03:00",
        fin: "2026-11-12T16:00:00-03:00",
      }),
    ]);
    const { user } = renderizarApp("/bloqueos");
    await screen.findByRole("table");
    await user.click(screen.getByRole("button", { name: NOMBRE_ANA_15_16 }));

    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Volver",
      }),
    );

    expect(falsa.pedidos(`DELETE /bloqueos/${ID_BLOQUEO}`)).toHaveLength(0);
  });
});
