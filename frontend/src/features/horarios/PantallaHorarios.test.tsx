import {
  act,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";

import { CLAVE_TOKEN } from "../sesion/almacenamiento";
import { instalarApiFalsa } from "../../test/apiFalsa";
import {
  franja,
  ID_ANA,
  ID_FRANJA,
  ID_LUIS,
  profesionalConMatricula,
} from "../../test/fabricas";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import { AHORA_SEGUNDOS, tokenDeRecepcionista } from "../../test/tokens";

usarRelojFijo();

const RUTA = "/configuracion/horarios";
const SIN_PROFESIONAL = "Elegí un profesional para ver o cargar su horario.";
const ANA = profesionalConMatricula({ id: ID_ANA });
const LUIS = profesionalConMatricula({
  id: ID_LUIS,
  nombre: "Luis",
  apellido: "Inventado",
  matricula: null,
  activo: false,
});
const ID_DESCONOCIDO = "00000000-0000-4000-8000-0000000000ff";
const ID_FRANJA_TARDE = "00000000-0000-4000-8000-0000000000ab";
const FRANJAS_ANA = [
  franja({ id: ID_FRANJA }),
  franja({
    id: ID_FRANJA_TARDE,
    hora_inicio: "14:00:00",
    hora_fin: "18:00:00",
  }),
];
const RUTA_FRANJAS_ANA = `/profesionales/${ID_ANA}/horarios`;

beforeEach(() => {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
  );
});

function apiConProfesionales() {
  const api = instalarApiFalsa();
  api.responder("GET /profesionales", { status: 200, cuerpo: [ANA, LUIS] });
  api.responder(`GET ${RUTA_FRANJAS_ANA}`, {
    status: 200,
    cuerpo: FRANJAS_ANA,
  });
  return api;
}

async function abrirDeAna() {
  const api = apiConProfesionales();
  const vista = renderizarApp(`${RUTA}?profesional=${ID_ANA}`);
  await screen.findByRole("region", { name: "Lunes" });
  return { api, ...vista };
}

function seccionDelDia(nombre: string) {
  return screen.getByRole("region", { name: nombre });
}

describe("Horarios: elección del profesional", () => {
  it("sin profesional pide el catálogo pero ninguna franja, y lo avisa", async () => {
    const api = apiConProfesionales();

    renderizarApp(RUTA);

    expect(await screen.findByText(SIN_PROFESIONAL)).toBeInTheDocument();
    await screen.findByRole("option", { name: "Ficticia, Ana" });
    expect(
      api.pedidos().filter((p) => p.ruta.endsWith("/horarios")),
    ).toHaveLength(0);
  });

  it("Nueva franja se ve deshabilitada y descrita sin profesional; al elegir uno se habilita", async () => {
    apiConProfesionales();
    const { user } = renderizarApp(RUTA);
    await screen.findByRole("option", { name: "Ficticia, Ana" });

    const boton = screen.getByRole("button", { name: "Nueva franja" });
    expect(boton).toBeVisible();
    expect(boton).toBeDisabled();
    expect(boton).toHaveAccessibleDescription(SIN_PROFESIONAL);

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Nueva franja" }),
      ).toBeEnabled(),
    );
    expect(screen.queryByText(SIN_PROFESIONAL)).not.toBeInTheDocument();
  });

  it("al elegir un profesional guarda el id en la URL y pide sus franjas", async () => {
    const api = apiConProfesionales();
    const { user } = renderizarApp(RUTA);
    await screen.findByRole("option", { name: "Ficticia, Ana" });

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );

    await waitFor(() =>
      expect(api.pedidos(`GET ${RUTA_FRANJAS_ANA}`)).toHaveLength(1),
    );
    expect(screen.getByTestId("busqueda")).toHaveTextContent(
      `profesional=${ID_ANA}`,
    );
  });

  it("ofrece al profesional inactivo marcado y se puede elegir", async () => {
    const api = apiConProfesionales();
    api.responder(`GET /profesionales/${ID_LUIS}/horarios`, {
      status: 200,
      cuerpo: [],
    });
    const { user } = renderizarApp(RUTA);
    await screen.findByRole("option", { name: "Inventado, Luis (inactivo)" });

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Inventado, Luis (inactivo)",
    );

    await waitFor(() =>
      expect(
        api.pedidos(`GET /profesionales/${ID_LUIS}/horarios`),
      ).toHaveLength(1),
    );
  });

  it("toma el profesional de la URL y pide sus franjas", async () => {
    const api = apiConProfesionales();

    renderizarApp(`${RUTA}?profesional=${ID_ANA}`);

    await screen.findByRole("region", { name: "Lunes" });
    expect(screen.getByLabelText("Profesional")).toHaveDisplayValue(
      "Ficticia, Ana",
    );
    expect(api.pedidos(`GET ${RUTA_FRANJAS_ANA}`)).toHaveLength(1);
  });

  it.each([
    ["mal formado", "no-es-un-id"],
    ["desconocido", ID_DESCONOCIDO],
  ])(
    "un parámetro %s se ignora: sin franjas y con Nueva franja deshabilitada",
    async (_caso, valor) => {
      const api = apiConProfesionales();

      renderizarApp(`${RUTA}?profesional=${valor}`);

      expect(await screen.findByText(SIN_PROFESIONAL)).toBeInTheDocument();
      await screen.findByRole("option", { name: "Ficticia, Ana" });
      expect(
        screen.getByRole("button", { name: "Nueva franja" }),
      ).toBeDisabled();
      expect(
        api.pedidos().filter((p) => p.ruta.endsWith("/horarios")),
      ).toHaveLength(0);
    },
  );

  it("falla el catálogo: muestra el error con Reintentar", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /profesionales", { red: true });

    renderizarApp(RUTA);

    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reintentar" }),
    ).toBeInTheDocument();
  });
});

describe("Horarios: franjas por día", () => {
  it("lista las franjas de cada día sin segundos y Sin atención en los días vacíos", async () => {
    await abrirDeAna();

    const lunes = seccionDelDia("Lunes");
    const textos = within(lunes)
      .getAllByRole("listitem")
      .map((li) => li.textContent);
    expect(textos[0]).toContain("09:00 a 13:00");
    expect(textos[1]).toContain("14:00 a 18:00");
    for (const dia of [
      "Martes",
      "Miércoles",
      "Jueves",
      "Viernes",
      "Sábado",
      "Domingo",
    ])
      expect(
        within(seccionDelDia(dia)).getByText("Sin atención"),
      ).toBeVisible();
    expect(within(lunes).queryByText("Sin atención")).not.toBeInTheDocument();
  });

  it("muestra la hora local aunque la suite corra en otra zona", async () => {
    const api = apiConProfesionales();
    api.responder(`GET ${RUTA_FRANJAS_ANA}`, {
      status: 200,
      cuerpo: [franja({ dia_semana: 2 })],
    });

    renderizarApp(`${RUTA}?profesional=${ID_ANA}`);

    const miercoles = await screen.findByRole("region", { name: "Miércoles" });
    expect(within(miercoles).getByText("09:00 a 13:00")).toBeInTheDocument();
  });

  it("un profesional sin horario lo dice y muestra los siete días sin atención", async () => {
    const api = apiConProfesionales();
    api.responder(`GET ${RUTA_FRANJAS_ANA}`, { status: 200, cuerpo: [] });

    renderizarApp(`${RUTA}?profesional=${ID_ANA}`);

    expect(
      await screen.findByText(
        "Este profesional no tiene horario cargado: no admite turnos.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Sin atención")).toHaveLength(7);
  });

  it("al cambiar de profesional se ven las franjas del último, aunque la respuesta vieja llegue después", async () => {
    const api = apiConProfesionales();
    const pendienteAna = api.pendiente(`GET ${RUTA_FRANJAS_ANA}`);
    api.responder(`GET /profesionales/${ID_LUIS}/horarios`, {
      status: 200,
      cuerpo: [
        franja({ id: "luis-1", profesional_id: ID_LUIS, dia_semana: 1 }),
      ],
    });
    const { user } = renderizarApp(`${RUTA}?profesional=${ID_ANA}`);
    await screen.findByRole("option", { name: "Inventado, Luis (inactivo)" });

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Inventado, Luis (inactivo)",
    );
    const martes = await screen.findByRole("region", { name: "Martes" });
    await within(martes).findByText("09:00 a 13:00");
    await act(async () => {
      pendienteAna.resolver({
        status: 200,
        cuerpo: [franja({ id: "ana-1", dia_semana: 3 })],
      });
    });

    expect(
      within(seccionDelDia("Jueves")).getByText("Sin atención"),
    ).toBeVisible();
    expect(
      within(seccionDelDia("Martes")).getByText("09:00 a 13:00"),
    ).toBeVisible();
  });

  it("el error de un pedido viejo no se muestra", async () => {
    const api = apiConProfesionales();
    const pendienteAna = api.pendiente(`GET ${RUTA_FRANJAS_ANA}`);
    api.responder(`GET /profesionales/${ID_LUIS}/horarios`, {
      status: 200,
      cuerpo: [
        franja({ id: "luis-1", profesional_id: ID_LUIS, dia_semana: 1 }),
      ],
    });
    const { user } = renderizarApp(`${RUTA}?profesional=${ID_ANA}`);
    await screen.findByRole("option", { name: "Inventado, Luis (inactivo)" });

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Inventado, Luis (inactivo)",
    );
    await within(
      await screen.findByRole("region", { name: "Martes" }),
    ).findByText("09:00 a 13:00");
    await act(async () => {
      pendienteAna.fallarPorRed();
    });

    expect(
      screen.queryByText("No se pudo conectar con el servidor."),
    ).not.toBeInTheDocument();
    expect(
      within(seccionDelDia("Martes")).getByText("09:00 a 13:00"),
    ).toBeVisible();
  });
});

describe("Horarios: alta de una franja", () => {
  async function abrirAlta() {
    const vista = await abrirDeAna();
    await vista.user.click(
      screen.getByRole("button", { name: "Nueva franja" }),
    );
    return {
      ...vista,
      dialogo: screen.getByRole("dialog", { name: "Nueva franja" }),
    };
  }

  async function completar(
    dialogo: HTMLElement,
    user: ReturnType<typeof renderizarApp>["user"],
    dia: string | null,
    desde: string,
    hasta: string,
  ) {
    if (dia !== null)
      await user.selectOptions(within(dialogo).getByLabelText("Día"), dia);
    fireEvent.change(within(dialogo).getByLabelText("Desde"), {
      target: { value: desde },
    });
    fireEvent.change(within(dialogo).getByLabelText("Hasta"), {
      target: { value: hasta },
    });
  }

  it("Desde y Hasta son de tipo time con paso de 5 minutos, y hay ayuda de una franja", async () => {
    const { dialogo } = await abrirAlta();

    for (const etiqueta of ["Desde", "Hasta"]) {
      const campo = within(dialogo).getByLabelText(etiqueta);
      expect(campo).toHaveAttribute("type", "time");
      expect(campo).toHaveAttribute("step", "300");
    }
    expect(
      within(dialogo).getByText(
        "Un turno debe entrar completo en una franja: dos franjas contiguas no se suman.",
      ),
    ).toBeInTheDocument();
  });

  it("envía el día numérico y las horas HH:MM, avisa y relee las franjas", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder(`POST ${RUTA_FRANJAS_ANA}`, {
      status: 201,
      cuerpo: franja(),
    });
    await completar(dialogo, user, "Martes", "09:00", "13:00");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Franja guardada.")).toBeInTheDocument();
    expect(api.pedidos(`POST ${RUTA_FRANJAS_ANA}`)[0]?.cuerpo).toEqual({
      dia_semana: 1,
      hora_inicio: "09:00",
      hora_fin: "13:00",
    });
    await waitFor(() =>
      expect(api.pedidos(`GET ${RUTA_FRANJAS_ANA}`)).toHaveLength(2),
    );
  });

  it("un día sin elegir marca Día y no hace pedidos", async () => {
    const { api, user, dialogo } = await abrirAlta();
    await completar(dialogo, user, null, "09:00", "13:00");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(within(dialogo).getByLabelText("Día")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(api.pedidos(`POST ${RUTA_FRANJAS_ANA}`)).toHaveLength(0);
  });

  it("franja_invalida muestra el error general y conserva los datos", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder(`POST ${RUTA_FRANJAS_ANA}`, {
      status: 422,
      cuerpo: { detail: { codigo: "franja_invalida", mensaje: "..." } },
    });
    await completar(dialogo, user, "Lunes", "22:00", "02:00");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await within(dialogo).findByText(
        "La franja debe terminar después de empezar, el mismo día, y en horas múltiplo de 5 minutos.",
      ),
    ).toBeInTheDocument();
    expect(within(dialogo).getByLabelText("Día")).toHaveDisplayValue("Lunes");
    expect(within(dialogo).getByLabelText("Desde")).toHaveValue("22:00");
    expect(within(dialogo).getByLabelText("Hasta")).toHaveValue("02:00");
  });

  it("franja_superpuesta muestra el error con rol alert", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder(`POST ${RUTA_FRANJAS_ANA}`, {
      status: 409,
      cuerpo: { detail: { codigo: "franja_superpuesta" } },
    });
    await completar(dialogo, user, "Lunes", "12:00", "15:00");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    const alerta = await within(dialogo).findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Se superpone con otra franja de ese día.",
    );
  });
});

describe("Horarios: edición y borrado", () => {
  it("editar muestra el día y las horas HH:MM y envía solo la hora de fin cambiada", async () => {
    const { api, user } = await abrirDeAna();
    api.responder(`PATCH ${RUTA_FRANJAS_ANA}/${ID_FRANJA}`, {
      status: 200,
      cuerpo: franja(),
    });

    await user.click(
      screen.getByRole("button", { name: "Editar lunes 09:00 a 13:00" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Editar franja" });
    expect(within(dialogo).getByLabelText("Día")).toHaveDisplayValue("Lunes");
    expect(within(dialogo).getByLabelText("Desde")).toHaveValue("09:00");
    expect(within(dialogo).getByLabelText("Hasta")).toHaveValue("13:00");
    fireEvent.change(within(dialogo).getByLabelText("Hasta"), {
      target: { value: "12:00" },
    });
    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Franja guardada.");
    expect(
      api.pedidos(`PATCH ${RUTA_FRANJAS_ANA}/${ID_FRANJA}`)[0]?.cuerpo,
    ).toEqual({ hora_fin: "12:00" });
  });

  it("cambiar el día envía solo dia_semana", async () => {
    const { api, user } = await abrirDeAna();
    api.responder(`PATCH ${RUTA_FRANJAS_ANA}/${ID_FRANJA}`, {
      status: 200,
      cuerpo: franja(),
    });
    await user.click(
      screen.getByRole("button", { name: "Editar lunes 09:00 a 13:00" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Editar franja" });

    await user.selectOptions(within(dialogo).getByLabelText("Día"), "Viernes");
    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Franja guardada.");
    expect(
      api.pedidos(`PATCH ${RUTA_FRANJAS_ANA}/${ID_FRANJA}`)[0]?.cuerpo,
    ).toEqual({ dia_semana: 4 });
  });

  it("sin cambios no hace el PATCH", async () => {
    const { api, user } = await abrirDeAna();
    await user.click(
      screen.getByRole("button", { name: "Editar lunes 09:00 a 13:00" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Editar franja" });

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      within(dialogo).getByText("No hiciste cambios."),
    ).toBeInTheDocument();
    expect(api.pedidos(`PATCH ${RUTA_FRANJAS_ANA}/${ID_FRANJA}`)).toHaveLength(
      0,
    );
  });

  it("borrar pide confirmación con la aclaración, hace el DELETE, avisa y relee", async () => {
    const { api, user } = await abrirDeAna();
    api.responder(`DELETE ${RUTA_FRANJAS_ANA}/${ID_FRANJA_TARDE}`, {
      status: 204,
    });

    await user.click(
      screen.getByRole("button", { name: "Borrar lunes 14:00 a 18:00" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Borrar franja" });
    expect(
      within(dialogo).getByText("Los turnos ya agendados no cambian."),
    ).toBeInTheDocument();
    expect(within(dialogo).getByText(/lunes/)).toBeInTheDocument();
    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar borrado" }),
    );

    expect(await screen.findByText("Franja borrada.")).toBeInTheDocument();
    expect(
      api.pedidos(`DELETE ${RUTA_FRANJAS_ANA}/${ID_FRANJA_TARDE}`),
    ).toHaveLength(1);
    await waitFor(() =>
      expect(api.pedidos(`GET ${RUTA_FRANJAS_ANA}`)).toHaveLength(2),
    );
  });

  it("Volver no borra nada", async () => {
    const { api, user } = await abrirDeAna();
    await user.click(
      screen.getByRole("button", { name: "Borrar lunes 14:00 a 18:00" }),
    );

    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Volver",
      }),
    );

    expect(
      api.pedidos(`DELETE ${RUTA_FRANJAS_ANA}/${ID_FRANJA_TARDE}`),
    ).toHaveLength(0);
  });

  it("una franja ya borrada (404) muestra el aviso y relee las franjas", async () => {
    const { api, user } = await abrirDeAna();
    api.responder(`DELETE ${RUTA_FRANJAS_ANA}/${ID_FRANJA_TARDE}`, {
      status: 404,
      cuerpo: { detail: { codigo: "recurso_inexistente", recurso: "horario" } },
    });
    await user.click(
      screen.getByRole("button", { name: "Borrar lunes 14:00 a 18:00" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Borrar franja" });

    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar borrado" }),
    );

    expect(
      await within(dialogo).findByText("Este registro ya no existe."),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(api.pedidos(`GET ${RUTA_FRANJAS_ANA}`)).toHaveLength(2),
    );
  });
});
