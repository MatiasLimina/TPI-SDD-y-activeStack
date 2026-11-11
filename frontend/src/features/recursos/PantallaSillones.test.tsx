import { act, screen, waitFor, within } from "@testing-library/react";

import { CLAVE_TOKEN } from "../sesion/almacenamiento";
import { instalarApiFalsa, type ApiFalsa } from "../../test/apiFalsa";
import { ID_SILLON_1, ID_SILLON_2, sillon } from "../../test/fabricas";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import { AHORA_SEGUNDOS, tokenDeRecepcionista } from "../../test/tokens";

usarRelojFijo();

const RUTA = "/configuracion/sillones";
const SILLONES = [
  sillon({ id: ID_SILLON_1, nombre: "Sillón 1" }),
  sillon({ id: ID_SILLON_2, nombre: "Sillón 2" }),
];

beforeEach(() => {
  sessionStorage.setItem(
    CLAVE_TOKEN,
    tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
  );
});

function apiConSillones(lista: unknown[] = SILLONES): ApiFalsa {
  const api = instalarApiFalsa();
  api.responder("GET /sillones", { status: 200, cuerpo: lista });
  return api;
}

async function abrir(lista?: unknown[]) {
  const api = apiConSillones(lista);
  const vista = renderizarApp(RUTA);
  await screen.findByRole("table");
  return { api, ...vista };
}

describe("Sillones: carga del listado", () => {
  it("indica la carga con rol status y todavía no muestra la tabla", async () => {
    const api = instalarApiFalsa();
    const pendiente = api.pendiente("GET /sillones");

    renderizarApp(RUTA);

    expect(await screen.findByText("Cargando…")).toHaveAttribute(
      "role",
      "status",
    );
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    await act(async () => {
      pendiente.resolver({ status: 200, cuerpo: SILLONES });
    });
    await screen.findByRole("table");
  });

  it("muestra una tabla con encabezados de columna y una fila por sillón", async () => {
    await abrir();

    expect(screen.queryByText("Cargando…")).not.toBeInTheDocument();
    const tabla = screen.getByRole("table");
    expect(
      within(tabla)
        .getAllByRole("columnheader")
        .map((c) => c.textContent),
    ).toEqual(["Nombre", "Estado", "Acciones"]);
    expect(within(tabla).getAllByRole("row")).toHaveLength(3);
    expect(within(tabla).getByText("Sillón 1")).toBeInTheDocument();
    expect(within(tabla).getByText("Sillón 2")).toBeInTheDocument();
  });

  it("un listado vacío muestra el mensaje de la pantalla y no la tabla", async () => {
    apiConSillones([]);

    renderizarApp(RUTA);

    expect(
      await screen.findByText("Todavía no hay sillones cargados."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("una falla de red se muestra con Reintentar, que repite el pedido", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { red: true });
    const { user } = renderizarApp(RUTA);
    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();

    api.responder("GET /sillones", { status: 200, cuerpo: SILLONES });
    await user.click(screen.getByRole("button", { name: "Reintentar" }));

    await screen.findByRole("table");
    expect(
      screen.queryByText("No se pudo conectar con el servidor."),
    ).not.toBeInTheDocument();
  });

  it("un 403 por rol desactualizado no cierra la sesión ni cambia la URL", async () => {
    const token = tokenDeRecepcionista(AHORA_SEGUNDOS + 3600);
    sessionStorage.setItem(CLAVE_TOKEN, token);
    const api = instalarApiFalsa();
    api.responder("GET /sillones", {
      status: 403,
      cuerpo: { detail: { codigo: "rol_insuficiente", mensaje: "x" } },
    });

    renderizarApp(RUTA);

    expect(
      await screen.findByText("No tenés permiso para ver esta información."),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
    expect(screen.getByTestId("ubicacion")).toHaveTextContent(RUTA);
  });

  it("un 500 sin cuerpo JSON muestra el error genérico con Reintentar", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { status: 500 });

    renderizarApp(RUTA);

    expect(
      await screen.findByText("Ocurrió un error. Intentá de nuevo."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reintentar" }),
    ).toBeInTheDocument();
  });

  it("un 401 no_autenticado cierra la sesión con el aviso de sesión vencida, sin el error del listado", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /sillones", {
      status: 401,
      cuerpo: { detail: { codigo: "no_autenticado", mensaje: "x" } },
    });

    renderizarApp(RUTA);

    expect(
      await screen.findByText("Tu sesión venció. Iniciá sesión de nuevo."),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/login");
    expect(screen.queryByRole("button", { name: "Reintentar" })).toBeNull();
  });
});

describe("Sillones: alta", () => {
  async function abrirAlta() {
    const vista = await abrir();
    await vista.user.click(
      screen.getByRole("button", { name: "Nuevo sillón" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Nuevo sillón" });
    return { ...vista, dialogo };
  }

  it("abre un diálogo con el campo vacío y sin pedidos a la API", async () => {
    const { api, dialogo } = await abrirAlta();

    expect(within(dialogo).getByLabelText("Nombre")).toHaveValue("");
    expect(api.pedidos("POST /sillones")).toHaveLength(0);
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
  });

  it("limita el nombre a 50 caracteres", async () => {
    const { dialogo } = await abrirAlta();

    expect(within(dialogo).getByLabelText("Nombre")).toHaveAttribute(
      "maxLength",
      "50",
    );
  });

  it("un nombre en blanco no hace pedidos y marca el campo", async () => {
    const { api, user, dialogo } = await abrirAlta();
    await user.type(within(dialogo).getByLabelText("Nombre"), "   ");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    const campo = within(dialogo).getByLabelText("Nombre");
    expect(campo).toHaveAccessibleDescription("Completá este campo.");
    expect(campo).toBeInvalid();
    expect(api.pedidos("POST /sillones")).toHaveLength(0);
  });

  it("un nombre vacío tampoco hace pedidos", async () => {
    const { api, user, dialogo } = await abrirAlta();

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      within(dialogo).getByLabelText("Nombre"),
    ).toHaveAccessibleDescription("Completá este campo.");
    expect(api.pedidos("POST /sillones")).toHaveLength(0);
  });

  it("envía el cuerpo, cierra el diálogo, avisa y relee el listado", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /sillones", { status: 201, cuerpo: sillon() });
    await user.type(within(dialogo).getByLabelText("Nombre"), " Sillón 3 ");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Sillón guardado.")).toHaveAttribute(
      "role",
      "status",
    );
    expect(api.pedidos("POST /sillones")[0]?.cuerpo).toEqual({
      nombre: "Sillón 3",
    });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => expect(api.pedidos("GET /sillones")).toHaveLength(2));
  });

  it("si falla la relectura, el aviso sigue visible junto al error con Reintentar y no se repite el POST", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /sillones", { status: 201, cuerpo: sillon() });
    api.responder("GET /sillones", { red: true });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Sillón 3");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(await screen.findByText("Sillón guardado.")).toBeInTheDocument();
    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reintentar" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.pedidos("POST /sillones")).toHaveLength(1);
  });

  it("un nombre duplicado marca el campo y conserva el diálogo y los datos", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /sillones", {
      status: 409,
      cuerpo: { detail: { codigo: "recurso_duplicado", campo: "nombre" } },
    });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Sillón 1");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    const campo = within(dialogo).getByLabelText("Nombre");
    await waitFor(() =>
      expect(campo).toHaveAccessibleDescription(
        "Ya existe un sillón con ese nombre.",
      ),
    );
    expect(campo).toHaveValue("Sillón 1");
    expect(screen.getByRole("dialog", { name: "Nuevo sillón" })).toBeVisible();
  });

  it("al reenviar corregido, el error desaparece y el diálogo se cierra", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /sillones", {
      status: 409,
      cuerpo: { detail: { codigo: "recurso_duplicado", campo: "nombre" } },
    });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Sillón 1");
    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));
    await screen.findByText("Ya existe un sillón con ese nombre.");

    api.responder("POST /sillones", { status: 201, cuerpo: sillon() });
    const campo = within(dialogo).getByLabelText("Nombre");
    await user.clear(campo);
    await user.type(campo, "Sillón 3");
    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Sillón guardado.");
    expect(api.pedidos("POST /sillones")).toHaveLength(2);
    expect(
      screen.queryByText("Ya existe un sillón con ese nombre."),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("mientras el envío está en curso el botón se deshabilita y hay un solo POST", async () => {
    const { api, user, dialogo } = await abrirAlta();
    const pendiente = api.pendiente("POST /sillones");
    await user.type(within(dialogo).getByLabelText("Nombre"), "Sillón 3");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    const boton = within(dialogo).getByRole("button", { name: "Guardar" });
    expect(boton).toBeDisabled();
    await user.click(boton);
    expect(api.pedidos("POST /sillones")).toHaveLength(1);
    await act(async () => {
      pendiente.resolver({ status: 201, cuerpo: sillon() });
    });
    await screen.findByText("Sillón guardado.");
  });

  it("un 403 al escribir muestra la falta de permiso sin cerrar la sesión", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /sillones", {
      status: 403,
      cuerpo: { detail: { codigo: "rol_insuficiente", mensaje: "x" } },
    });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Sillón 3");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await within(dialogo).findByText("No tenés permiso para esta operación."),
    ).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).not.toBeNull();
    expect(screen.getByRole("dialog", { name: "Nuevo sillón" })).toBeVisible();
  });

  it("un 401 no_autenticado al escribir cierra la sesión con el aviso", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /sillones", {
      status: 401,
      cuerpo: { detail: { codigo: "no_autenticado", mensaje: "x" } },
    });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Sillón 3");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await screen.findByText("Tu sesión venció. Iniciá sesión de nuevo."),
    ).toBeInTheDocument();
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/login");
  });

  it("una falla de red al escribir muestra el mensaje y conserva el diálogo", async () => {
    const { api, user, dialogo } = await abrirAlta();
    api.responder("POST /sillones", { red: true });
    await user.type(within(dialogo).getByLabelText("Nombre"), "Sillón 3");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await within(dialogo).findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(within(dialogo).getByLabelText("Nombre")).toHaveValue("Sillón 3");
  });
});

describe("Sillones: edición", () => {
  async function abrirEdicion() {
    const vista = await abrir();
    await vista.user.click(
      screen.getByRole("button", { name: "Editar Sillón 2" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Editar sillón" });
    return { ...vista, dialogo };
  }

  it("abre con los valores actuales", async () => {
    const { dialogo } = await abrirEdicion();

    expect(within(dialogo).getByLabelText("Nombre")).toHaveValue("Sillón 2");
  });

  it("Volver cierra sin PATCH y la tabla conserva el nombre original", async () => {
    const { api, user, dialogo } = await abrirEdicion();
    const campo = within(dialogo).getByLabelText("Nombre");
    await user.clear(campo);
    await user.type(campo, "Otro nombre");

    await user.click(within(dialogo).getByRole("button", { name: "Volver" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.pedidos(`PATCH /sillones/${ID_SILLON_2}`)).toHaveLength(0);
    expect(
      within(screen.getByRole("table")).getByText("Sillón 2"),
    ).toBeVisible();
  });

  it("envía solo el campo cambiado", async () => {
    const { api, user, dialogo } = await abrirEdicion();
    api.responder(`PATCH /sillones/${ID_SILLON_2}`, {
      status: 200,
      cuerpo: sillon(),
    });
    const campo = within(dialogo).getByLabelText("Nombre");
    await user.clear(campo);
    await user.type(campo, "Sillón Norte");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    await screen.findByText("Sillón guardado.");
    expect(api.pedidos(`PATCH /sillones/${ID_SILLON_2}`)[0]?.cuerpo).toEqual({
      nombre: "Sillón Norte",
    });
  });

  it("sin cambios (un espacio al final) avisa No hiciste cambios. sin pedidos", async () => {
    const { api, user, dialogo } = await abrirEdicion();
    await user.type(within(dialogo).getByLabelText("Nombre"), " ");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(within(dialogo).getByText("No hiciste cambios.")).toHaveAttribute(
      "role",
      "status",
    );
    expect(screen.getByRole("dialog", { name: "Editar sillón" })).toBeVisible();
    expect(api.pedidos(`PATCH /sillones/${ID_SILLON_2}`)).toHaveLength(0);
  });

  it("un 404 recurso_inexistente deshabilita el envío y relee el listado", async () => {
    const { api, user, dialogo } = await abrirEdicion();
    api.responder(`PATCH /sillones/${ID_SILLON_2}`, {
      status: 404,
      cuerpo: { detail: { codigo: "recurso_inexistente", recurso: "sillon" } },
    });
    const campo = within(dialogo).getByLabelText("Nombre");
    await user.clear(campo);
    await user.type(campo, "Sillón Norte");

    await user.click(within(dialogo).getByRole("button", { name: "Guardar" }));

    expect(
      await within(dialogo).findByText("Este registro ya no existe."),
    ).toBeInTheDocument();
    expect(
      within(dialogo).getByRole("button", { name: "Guardar" }),
    ).toBeDisabled();
    await waitFor(() => expect(api.pedidos("GET /sillones")).toHaveLength(2));
  });
});

describe("Sillones: desactivación y estado", () => {
  it("ofrece Editar y Desactivar con el nombre del sillón en cada fila", async () => {
    await abrir();

    for (const nombre of ["Sillón 1", "Sillón 2"]) {
      expect(
        screen.getByRole("button", { name: `Editar ${nombre}` }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: `Desactivar ${nombre}` }),
      ).toBeInTheDocument();
    }
  });

  it("confirmar hace el POST de desactivar, cierra el diálogo, avisa y relee", async () => {
    const { api, user } = await abrir();
    api.responder(`POST /sillones/${ID_SILLON_1}/desactivar`, {
      status: 200,
      cuerpo: sillon({ activo: false }),
    });
    api.responder("GET /sillones", {
      status: 200,
      cuerpo: [
        sillon({ id: ID_SILLON_1, nombre: "Sillón 1", activo: false }),
        SILLONES[1],
      ],
    });

    await user.click(
      screen.getByRole("button", { name: "Desactivar Sillón 1" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Desactivar sillón" });
    expect(within(dialogo).getByText(/Sillón 1/)).toBeInTheDocument();
    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar desactivación" }),
    );

    expect(await screen.findByText("Sillón desactivado.")).toHaveAttribute(
      "role",
      "status",
    );
    expect(
      api.pedidos(`POST /sillones/${ID_SILLON_1}/desactivar`),
    ).toHaveLength(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await waitFor(() => {
      const fila = screen.getByRole("row", { name: /Sillón 1/ });
      expect(within(fila).getByText("Inactivo")).toBeInTheDocument();
    });
  });

  it("Volver no hace ningún pedido de desactivación", async () => {
    const { api, user } = await abrir();
    await user.click(
      screen.getByRole("button", { name: "Desactivar Sillón 1" }),
    );

    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Volver",
      }),
    );

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(
      api.pedidos(`POST /sillones/${ID_SILLON_1}/desactivar`),
    ).toHaveLength(0);
  });

  it("un error en la confirmación se muestra en el mismo diálogo, que sigue abierto", async () => {
    const { api, user } = await abrir();
    api.responder(`POST /sillones/${ID_SILLON_1}/desactivar`, { red: true });
    await user.click(
      screen.getByRole("button", { name: "Desactivar Sillón 1" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Desactivar sillón" });

    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar desactivación" }),
    );

    expect(
      await within(dialogo).findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(dialogo).toBeVisible();
  });

  it("un 404 al desactivar deshabilita la confirmación y relee el listado", async () => {
    const { api, user } = await abrir();
    api.responder(`POST /sillones/${ID_SILLON_1}/desactivar`, {
      status: 404,
      cuerpo: { detail: { codigo: "recurso_inexistente", recurso: "sillon" } },
    });
    await user.click(
      screen.getByRole("button", { name: "Desactivar Sillón 1" }),
    );
    const dialogo = screen.getByRole("dialog", { name: "Desactivar sillón" });

    await user.click(
      within(dialogo).getByRole("button", { name: "Confirmar desactivación" }),
    );

    expect(
      await within(dialogo).findByText("Este registro ya no existe."),
    ).toBeInTheDocument();
    expect(
      within(dialogo).getByRole("button", { name: "Confirmar desactivación" }),
    ).toBeDisabled();
    await waitFor(() => expect(api.pedidos("GET /sillones")).toHaveLength(2));
  });

  it("un sillón inactivo muestra Inactivo, ofrece Editar y no ofrece Desactivar ni reactivar", async () => {
    await abrir([
      sillon({ id: ID_SILLON_1, nombre: "Sillón 1" }),
      sillon({ id: ID_SILLON_2, nombre: "Sillón 2", activo: false }),
    ]);

    const fila = screen.getByRole("row", { name: /Sillón 2/ });
    expect(within(fila).getByText("Inactivo")).toBeInTheDocument();
    expect(
      within(fila).getByRole("button", { name: "Editar Sillón 2" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Desactivar Sillón 2" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Reactivar/ }),
    ).not.toBeInTheDocument();
  });

  it("la pantalla tiene un título de nivel 1", async () => {
    await abrir();

    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });
});
