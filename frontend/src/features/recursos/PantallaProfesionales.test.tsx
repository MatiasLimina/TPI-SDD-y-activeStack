import { screen, waitFor, within } from "@testing-library/react";

import { CLAVE_TOKEN } from "../sesion/almacenamiento";
import { instalarApiFalsa } from "../../test/apiFalsa";
import { ID_ANA, ID_LUIS, profesionalConMatricula } from "../../test/fabricas";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import { AHORA_SEGUNDOS, tokenDeRecepcionista } from "../../test/tokens";

usarRelojFijo();

const RUTA = "/configuracion/profesionales";
const ANA = profesionalConMatricula({ id: ID_ANA });
const LUIS = profesionalConMatricula({
  id: ID_LUIS,
  nombre: "Luis",
  apellido: "Inventado",
  matricula: null,
  activo: false,
});

beforeEach(() => {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
  );
});

async function abrir(lista: unknown[] = [ANA, LUIS]) {
  const api = instalarApiFalsa();
  api.responder("GET /profesionales", { status: 200, cuerpo: lista });
  const vista = renderizarApp(RUTA);
  await screen.findByRole("table");
  return { api, ...vista };
}

describe("Profesionales: listado", () => {
  it("muestra Apellido, Nombre, la matrícula y el estado, en el orden de la API", async () => {
    await abrir();

    const filas = screen.getAllByRole("row").slice(1);
    expect(filas).toHaveLength(2);
    expect(within(filas[0]!).getByText("Ficticia, Ana")).toBeInTheDocument();
    expect(within(filas[0]!).getByText("MN-0001")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("Inventado, Luis")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("Sin matrícula")).toBeInTheDocument();
    expect(within(filas[1]!).getByText("Inactivo")).toBeInTheDocument();
    expect(within(filas[0]!).queryByText("Inactivo")).not.toBeInTheDocument();
  });

  it("un listado vacío muestra el mensaje de la pantalla", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /profesionales", { status: 200, cuerpo: [] });

    renderizarApp(RUTA);

    expect(
      await screen.findByText("Todavía no hay profesionales cargados."),
    ).toBeInTheDocument();
  });
});

describe("Profesionales: alta", () => {
  async function abrirAlta() {
    const vista = await abrir();
    await vista.user.click(
      screen.getByRole("button", { name: "Nuevo profesional" }),
    );
    return {
      ...vista,
      dialogo: screen.getByRole("dialog", { name: "Nuevo profesional" }),
    };
  }

  it("abre vacío, con los campos Nombre, Apellido y Matrícula, y sin pedidos", async () => {
    const { api, dialogo } = await abrirAlta();

    for (const etiqueta of ["Nombre", "Apellido", "Matrícula"])
      expect(within(dialogo).getByLabelText(etiqueta)).toHaveValue("");
    expect(api.pedidos("POST /profesionales")).toHaveLength(0);
  });

  it("limita los largos: 100, 100 y 30", async () => {
    const { dialogo } = await abrirAlta();

    expect(within(dialogo).getByLabelText("Nombre")).toHaveAttribute(
      "maxLength",
      "100",
    );
    expect(within(dialogo).getByLabelText("Apellido")).toHaveAttribute(
      "maxLength",
      "100",
    );
    expect(within(dialogo).getByLabelText("Matrícula")).toHaveAttribute(
      "maxLength",
      "30",
    );
  });

  it("envía nombre, apellido y matrícula, y avisa Profesional guardado.", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /profesionales", { status: 201, cuerpo: ANA });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Ana");
    await user.type(within(dialogo).getByLabelText("Apellido"), "Ficticia");
    await user.type(within(dialogo).getByLabelText("Matrícula"), "MN-0001");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await screen.findByText("Profesional guardado."),
    ).toBeInTheDocument();
    expect(api.pedidos("POST /profesionales")[0]?.cuerpo).toEqual({
      nombre: "Ana",
      apellido: "Ficticia",
      matricula: "MN-0001",
    });
    await waitFor(() =>
      expect(api.pedidos("GET /profesionales")).toHaveLength(2),
    );
  });

  it("con la matrícula vacía la omite del cuerpo", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /profesionales", { status: 201, cuerpo: ANA });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Ana");
    await user.type(within(dialogo).getByLabelText("Apellido"), "Ficticia");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Profesional guardado.");
    expect(api.pedidos("POST /profesionales")[0]?.cuerpo).toEqual({
      nombre: "Ana",
      apellido: "Ficticia",
    });
  });

  it("un apellido vacío marca el campo y no hace pedidos", async () => {
    const { api, user, dialogo } = await abrirAlta();
    await user.type(within(dialogo).getByLabelText("Nombre"), "Ana");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    const campo = within(dialogo).getByLabelText("Apellido");
    expect(campo).toHaveAccessibleDescription("Completá este campo.");
    expect(campo).toBeInvalid();
    expect(within(dialogo).getByLabelText("Nombre")).not.toBeInvalid();
    expect(api.pedidos("POST /profesionales")).toHaveLength(0);
  });

  it("un nombre y un apellido vacíos se marcan a la vez", async () => {
    const { user, dialogo } = await abrirAlta();

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(within(dialogo).getByLabelText("Nombre")).toBeInvalid();
    expect(within(dialogo).getByLabelText("Apellido")).toBeInvalid();
    expect(within(dialogo).getByLabelText("Matrícula")).not.toBeInvalid();
  });
});

describe("Profesionales: edición", () => {
  async function abrirEdicion(nombre: string) {
    const vista = await abrir();
    await vista.user.click(screen.getByRole("button", { name: nombre }));
    return {
      ...vista,
      dialogo: screen.getByRole("dialog", { name: "Editar profesional" }),
    };
  }

  it("abre con los valores actuales", async () => {
    const { dialogo } = await abrirEdicion("Editar Ficticia, Ana");

    expect(within(dialogo).getByLabelText("Nombre")).toHaveValue("Ana");
    expect(within(dialogo).getByLabelText("Apellido")).toHaveValue("Ficticia");
    expect(within(dialogo).getByLabelText("Matrícula")).toHaveValue("MN-0001");
  });

  it("envía solo el apellido cambiado", async () => {
    const { api, user, dialogo } = await abrirEdicion("Editar Ficticia, Ana");
    api.responder(`PATCH /profesionales/${ID_ANA}`, {
      status: 200,
      cuerpo: ANA,
    });
    const campo = within(dialogo).getByLabelText("Apellido");
    await user.clear(campo);
    await user.type(campo, "Ficticia Segunda");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Profesional guardado.");
    expect(api.pedidos(`PATCH /profesionales/${ID_ANA}`)[0]?.cuerpo).toEqual({
      apellido: "Ficticia Segunda",
    });
  });

  it("al borrar la matrícula envía null", async () => {
    const { api, user, dialogo } = await abrirEdicion("Editar Ficticia, Ana");
    api.responder(`PATCH /profesionales/${ID_ANA}`, {
      status: 200,
      cuerpo: ANA,
    });
    await user.clear(within(dialogo).getByLabelText("Matrícula"));

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Profesional guardado.");
    expect(api.pedidos(`PATCH /profesionales/${ID_ANA}`)[0]?.cuerpo).toEqual({
      matricula: null,
    });
  });

  it("un espacio al final del nombre no es un cambio", async () => {
    const { api, user, dialogo } = await abrirEdicion("Editar Ficticia, Ana");
    await user.type(within(dialogo).getByLabelText("Nombre"), " ");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(within(dialogo).getByText("No hiciste cambios.")).toHaveAttribute(
      "role",
      "status",
    );
    expect(api.pedidos(`PATCH /profesionales/${ID_ANA}`)).toHaveLength(0);
  });

  it("una matrícula repetida marca el campo y conserva el diálogo", async () => {
    const { api, user, dialogo } = await abrirEdicion("Editar Inventado, Luis");
    api.responder(`PATCH /profesionales/${ID_LUIS}`, {
      status: 409,
      cuerpo: { detail: { codigo: "recurso_duplicado", campo: "matricula" } },
    });
    await user.type(within(dialogo).getByLabelText("Matrícula"), "MN-0001");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(
        within(dialogo).getByLabelText("Matrícula"),
      ).toHaveAccessibleDescription(
        "Ya existe un profesional con esa matrícula.",
      ),
    );
    expect(
      screen.getByRole("dialog", { name: "Editar profesional" }),
    ).toBeVisible();
    expect(within(dialogo).getByLabelText("Matrícula")).toHaveValue("MN-0001");
  });
});

describe("Profesionales: desactivación", () => {
  it("la confirmación nombra al profesional y explica la consecuencia", async () => {
    const { user } = await abrir();

    await user.click(
      screen.getByRole("button", { name: "Desactivar Ficticia, Ana" }),
    );

    const dialogo = screen.getByRole("dialog", {
      name: "Desactivar profesional",
    });
    expect(within(dialogo).getByText("Ficticia, Ana")).toBeInTheDocument();
    expect(
      within(dialogo).getByText(
        "No va a admitir turnos nuevos. Los turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.",
      ),
    ).toBeInTheDocument();
  });

  it("confirmar envía el POST, avisa y relee", async () => {
    const { api, user } = await abrir();
    api.responder(`POST /profesionales/${ID_ANA}/desactivar`, {
      status: 200,
      cuerpo: { ...ANA, activo: false },
    });
    await user.click(
      screen.getByRole("button", { name: "Desactivar Ficticia, Ana" }),
    );

    await user.click(
      screen.getByRole("button", { name: "Confirmar desactivación" }),
    );

    expect(
      await screen.findByText("Profesional desactivado."),
    ).toBeInTheDocument();
    expect(
      api.pedidos(`POST /profesionales/${ID_ANA}/desactivar`),
    ).toHaveLength(1);
    await waitFor(() =>
      expect(api.pedidos("GET /profesionales")).toHaveLength(2),
    );
  });

  it("un profesional inactivo no ofrece Desactivar pero sí Editar", async () => {
    await abrir();

    expect(
      screen.queryByRole("button", { name: "Desactivar Inventado, Luis" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Editar Inventado, Luis" }),
    ).toBeInTheDocument();
  });
});
