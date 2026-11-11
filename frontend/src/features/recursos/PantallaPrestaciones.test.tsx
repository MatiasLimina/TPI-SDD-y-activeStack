import { screen, waitFor, within } from "@testing-library/react";

import { CLAVE_TOKEN } from "../sesion/almacenamiento";
import { instalarApiFalsa } from "../../test/apiFalsa";
import { ID_CONTROL, ID_LIMPIEZA, prestacion } from "../../test/fabricas";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import { AHORA_SEGUNDOS, tokenDeRecepcionista } from "../../test/tokens";

usarRelojFijo();

const RUTA = "/configuracion/prestaciones";
const CONTROL = prestacion({
  id: ID_CONTROL,
  nombre: "Control",
  duracion_min: 30,
  requiere_sillon: false,
});
const LIMPIEZA = prestacion({ id: ID_LIMPIEZA });
const ERROR_ENTERO = "Ingresá minutos enteros.";

beforeEach(() => {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
  );
});

async function abrir() {
  const api = instalarApiFalsa();
  api.responder("GET /prestaciones", {
    status: 200,
    cuerpo: [CONTROL, LIMPIEZA],
  });
  const vista = renderizarApp(RUTA);
  await screen.findByRole("table");
  return { api, ...vista };
}

async function abrirAlta() {
  const vista = await abrir();
  await vista.user.click(
    screen.getByRole("button", { name: "Nueva prestación" }),
  );
  return {
    ...vista,
    dialogo: screen.getByRole("dialog", { name: "Nueva prestación" }),
  };
}

async function abrirEdicionDeControl() {
  const vista = await abrir();
  await vista.user.click(
    screen.getByRole("button", { name: "Editar Control" }),
  );
  return {
    ...vista,
    dialogo: screen.getByRole("dialog", { name: "Editar prestación" }),
  };
}

describe("Prestaciones: listado", () => {
  it("muestra la duración como N min y si requiere sillón", async () => {
    await abrir();

    const control = screen.getByRole("row", { name: /Control/ });
    expect(within(control).getByText("30 min")).toBeInTheDocument();
    expect(within(control).getByText("No")).toBeInTheDocument();
    const limpieza = screen.getByRole("row", { name: /Limpieza/ });
    expect(within(limpieza).getByText("45 min")).toBeInTheDocument();
    expect(within(limpieza).getByText("Sí")).toBeInTheDocument();
  });
});

describe("Prestaciones: alta", () => {
  it("Requiere sillón viene marcada y el nombre limita a 100 caracteres", async () => {
    const { dialogo } = await abrirAlta();

    expect(within(dialogo).getByLabelText("Requiere sillón")).toBeChecked();
    expect(within(dialogo).getByLabelText("Nombre")).toHaveAttribute(
      "maxLength",
      "100",
    );
  });

  it("la duración es un campo de texto con teclado numérico", async () => {
    const { dialogo } = await abrirAlta();

    const campo = within(dialogo).getByLabelText("Duración (minutos)");
    expect(campo).toHaveAttribute("type", "text");
    expect(campo).toHaveAttribute("inputMode", "numeric");
  });

  it("envía una prestación sin sillón con la duración como número", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /prestaciones", { status: 201, cuerpo: CONTROL });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Control");
    await user.type(within(dialogo).getByLabelText("Duración (minutos)"), "30");
    await user.click(within(dialogo).getByLabelText("Requiere sillón"));

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Prestación guardada.")).toBeInTheDocument();
    expect(api.pedidos("POST /prestaciones")[0]?.cuerpo).toEqual({
      nombre: "Control",
      duracion_min: 30,
      requiere_sillon: false,
    });
  });

  it("envía requiere_sillon verdadero si no se toca la casilla", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /prestaciones", { status: 201, cuerpo: LIMPIEZA });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Limpieza");
    await user.type(
      within(dialogo).getByLabelText("Duración (minutos)"),
      " 45 ",
    );

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Prestación guardada.");
    expect(api.pedidos("POST /prestaciones")[0]?.cuerpo).toEqual({
      nombre: "Limpieza",
      duracion_min: 45,
      requiere_sillon: true,
    });
  });

  it.each(["32.5", "32,5", "abc"])(
    "la duración %s marca Ingresá minutos enteros. y no hace pedidos",
    async (valor) => {
      const { api, user, dialogo } = await abrirAlta();
      await user.type(within(dialogo).getByLabelText("Nombre"), "Control");
      await user.type(
        within(dialogo).getByLabelText("Duración (minutos)"),
        valor,
      );

      await user.click(
        within(dialogo).getByRole("button", { name: "Guardar" }),
      );

      expect(
        within(dialogo).getByLabelText("Duración (minutos)"),
      ).toHaveAccessibleDescription(ERROR_ENTERO);
      expect(api.pedidos("POST /prestaciones")).toHaveLength(0);
    },
  );

  it("una duración vacía pide completar el campo, no minutos enteros", async () => {
    const { api, user, dialogo } = await abrirAlta();
    await user.type(within(dialogo).getByLabelText("Nombre"), "Control");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      within(dialogo).getByLabelText("Duración (minutos)"),
    ).toHaveAccessibleDescription("Completá este campo.");
    expect(api.pedidos("POST /prestaciones")).toHaveLength(0);
  });

  it("un entero fuera de rango o negativo igual se envía: lo decide la API", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /prestaciones", {
      status: 422,
      cuerpo: { detail: { codigo: "duracion_invalida", mensaje: "..." } },
    });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Control");
    await user.type(within(dialogo).getByLabelText("Duración (minutos)"), "32");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(
        within(dialogo).getByLabelText("Duración (minutos)"),
      ).toHaveAccessibleDescription(
        "La duración debe ser múltiplo de 5, de 5 a 480 minutos.",
      ),
    );
    expect(api.pedidos("POST /prestaciones")[0]?.cuerpo).toMatchObject({
      duracion_min: 32,
    });
    expect(
      screen.getByRole("dialog", { name: "Nueva prestación" }),
    ).toBeVisible();
  });

  it("un nombre repetido marca Nombre", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /prestaciones", {
      status: 409,
      cuerpo: { detail: { codigo: "recurso_duplicado", campo: "nombre" } },
    });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Limpieza");
    await user.type(within(dialogo).getByLabelText("Duración (minutos)"), "30");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(
        within(dialogo).getByLabelText("Nombre"),
      ).toHaveAccessibleDescription("Ya existe una prestación con ese nombre."),
    );
  });
});

describe("Prestaciones: edición", () => {
  it("una duración no numérica en la edición no hace pedidos", async () => {
    const { api, user, dialogo } = await abrirEdicionDeControl();
    const campo = within(dialogo).getByLabelText("Duración (minutos)");
    expect(campo).toHaveValue("30");
    await user.clear(campo);
    await user.type(campo, "abc");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(campo).toHaveAccessibleDescription(ERROR_ENTERO);
    expect(api.pedidos(`PATCH /prestaciones/${ID_CONTROL}`)).toHaveLength(0);
  });

  it("al marcar Requiere sillón envía solo ese campo", async () => {
    const { api, user, dialogo } = await abrirEdicionDeControl();
    api.responder(`PATCH /prestaciones/${ID_CONTROL}`, {
      status: 200,
      cuerpo: CONTROL,
    });
    expect(within(dialogo).getByLabelText("Requiere sillón")).not.toBeChecked();
    await user.click(within(dialogo).getByLabelText("Requiere sillón"));

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Prestación guardada.");
    expect(api.pedidos(`PATCH /prestaciones/${ID_CONTROL}`)[0]?.cuerpo).toEqual(
      { requiere_sillon: true },
    );
  });

  it("al cambiar la duración envía solo el número nuevo", async () => {
    const { api, user, dialogo } = await abrirEdicionDeControl();
    api.responder(`PATCH /prestaciones/${ID_CONTROL}`, {
      status: 200,
      cuerpo: CONTROL,
    });
    const campo = within(dialogo).getByLabelText("Duración (minutos)");
    await user.clear(campo);
    await user.type(campo, "40");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Prestación guardada.");
    expect(api.pedidos(`PATCH /prestaciones/${ID_CONTROL}`)[0]?.cuerpo).toEqual(
      { duracion_min: 40 },
    );
  });

  it("sin cambios avisa No hiciste cambios.", async () => {
    const { api, user, dialogo } = await abrirEdicionDeControl();

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      within(dialogo).getByText("No hiciste cambios."),
    ).toBeInTheDocument();
    expect(api.pedidos(`PATCH /prestaciones/${ID_CONTROL}`)).toHaveLength(0);
  });
});

describe("Prestaciones: desactivación", () => {
  it("confirmar hace el POST, avisa Prestación desactivada. y relee", async () => {
    const { api, user } = await abrir();
    api.responder(`POST /prestaciones/${ID_CONTROL}/desactivar`, {
      status: 200,
      cuerpo: { ...CONTROL, activa: false },
    });
    await user.click(
      screen.getByRole("button", { name: "Desactivar Control" }),
    );
    const dialogo = screen.getByRole("dialog", {
      name: "Desactivar prestación",
    });
    expect(
      within(dialogo).getByText(
        "No va a admitir turnos nuevos. Los turnos ya agendados no cambian y se pueden cancelar. No se puede reactivar.",
      ),
    ).toBeInTheDocument();

    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar desactivación" }),
    );

    expect(
      await screen.findByText("Prestación desactivada."),
    ).toBeInTheDocument();
    expect(
      api.pedidos(`POST /prestaciones/${ID_CONTROL}/desactivar`),
    ).toHaveLength(1);
    await waitFor(() =>
      expect(api.pedidos("GET /prestaciones")).toHaveLength(2),
    );
  });

  it("una prestación inactiva muestra Inactivo y no ofrece Desactivar", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /prestaciones", {
      status: 200,
      cuerpo: [{ ...CONTROL, activa: false }],
    });

    renderizarApp(RUTA);

    const fila = await screen.findByRole("row", { name: /Control/ });
    expect(within(fila).getByText("Inactivo")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Desactivar Control" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Editar Control" }),
    ).toBeInTheDocument();
  });
});
