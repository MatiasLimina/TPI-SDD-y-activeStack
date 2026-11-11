import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { instalarApiFalsa, type ApiFalsa } from "../../test/apiFalsa";
import {
  ID_ANA,
  ID_CONTROL,
  ID_LIMPIEZA,
  ID_LUIS,
  ID_SILLON_1,
  ID_SILLON_2,
  paciente,
  prestacion,
  profesional,
  sillon,
} from "../../test/fabricas";
import { useCatalogos, type Catalogos } from "../agenda/useCatalogos";
import { ProveedorSesion } from "../sesion/ProveedorSesion";
import { FormularioNuevoTurno } from "./FormularioNuevoTurno";

const CATALOGOS: Catalogos = {
  profesionales: [
    profesional(),
    profesional({
      id: ID_LUIS,
      nombre: "Luis",
      apellido: "Inventado",
      activo: false,
    }),
  ],
  sillones: [
    sillon(),
    sillon({ id: ID_SILLON_2, nombre: "Sillón 2", activo: false }),
  ],
  prestaciones: [
    prestacion(),
    prestacion({
      id: ID_CONTROL,
      nombre: "Control",
      duracion_min: 30,
      requiere_sillon: false,
    }),
  ],
};

interface Opciones {
  catalogos?: Catalogos;
  fechaInicial?: string;
  profesionalInicial?: string | null;
}

function montar(opciones: Opciones = {}) {
  const alCrear = vi.fn();
  const alCerrar = vi.fn();
  const user = userEvent.setup();
  render(
    <ProveedorSesion>
      <FormularioNuevoTurno
        abierto
        catalogos={opciones.catalogos ?? CATALOGOS}
        fechaInicial={opciones.fechaInicial ?? "2026-11-12"}
        profesionalInicial={opciones.profesionalInicial ?? null}
        alCrear={alCrear}
        alCerrar={alCerrar}
        alReleerCatalogos={() => Promise.resolve(null)}
        alReleerAgenda={() => {}}
      />
    </ProveedorSesion>,
  );
  return { user, alCrear, alCerrar };
}

type Usuario = ReturnType<typeof userEvent.setup>;

async function elegirPaciente(user: Usuario, api: ApiFalsa) {
  api.responder("GET /pacientes", { status: 200, cuerpo: [paciente()] });
  await user.type(screen.getByLabelText("Buscar paciente"), "car");
  await user.click(
    await screen.findByRole("button", { name: /Imaginaria, Carla/ }),
  );
}

function completar(campo: string, valor: string) {
  fireEvent.change(screen.getByLabelText(campo), { target: { value: valor } });
}

/** Llena todo lo obligatorio de una prestación que requiere sillón. */
async function llenar(user: Usuario, api: ApiFalsa) {
  await elegirPaciente(user, api);
  await user.selectOptions(
    screen.getByLabelText("Profesional"),
    "Ficticia, Ana",
  );
  await user.selectOptions(screen.getByLabelText("Prestación"), "Limpieza");
  await user.selectOptions(screen.getByLabelText("Sillón"), "Sillón 1");
  completar("Fecha", "2026-11-12");
  completar("Hora", "10:00");
}

function enviar(user: Usuario) {
  return user.click(screen.getByRole("button", { name: "Crear turno" }));
}

function cuerpoDelPost(api: ApiFalsa): Record<string, unknown> {
  const [pedido] = api.pedidos("POST /turnos");
  return pedido?.cuerpo as Record<string, unknown>;
}

describe("Formulario de nuevo turno: campos iniciales", () => {
  it("ofrece solo recursos activos", () => {
    instalarApiFalsa();
    montar();

    const profesionales = screen
      .getAllByRole("option")
      .map((o) => o.textContent);
    expect(profesionales).toContain("Ficticia, Ana");
    expect(profesionales).not.toContain("Inventado, Luis");
    expect(profesionales).not.toContain("Inventado, Luis (inactivo)");
    expect(
      screen.queryByRole("option", { name: /Sillón 2/ }),
    ).not.toBeInTheDocument();
  });

  it("precarga al profesional del filtro si está activo", () => {
    instalarApiFalsa();
    montar({ profesionalInicial: ID_ANA });

    expect(screen.getByLabelText("Profesional")).toHaveValue(ID_ANA);
  });

  it("si el filtro es un profesional desactivado, no precarga nada y no lo ofrece", () => {
    instalarApiFalsa();
    montar({ profesionalInicial: ID_LUIS });

    expect(screen.getByLabelText("Profesional")).toHaveValue("");
    expect(
      screen.queryByRole("option", { name: /Inventado/ }),
    ).not.toBeInTheDocument();
  });

  it("la fecha toma la de la agenda y la hora está vacía", () => {
    instalarApiFalsa();
    montar({ fechaInicial: "2026-11-12" });

    expect(screen.getByLabelText("Fecha")).toHaveValue("2026-11-12");
    expect(screen.getByLabelText("Hora")).toHaveValue("");
  });

  it("la hora es de tipo hora con pasos de 300 segundos", () => {
    instalarApiFalsa();
    montar();

    const hora = screen.getByLabelText("Hora");
    expect(hora).toHaveAttribute("type", "time");
    expect(hora).toHaveAttribute("step", "300");
  });

  it("es un diálogo modal con el título Nuevo turno", () => {
    instalarApiFalsa();
    montar();

    expect(
      screen.getByRole("dialog", { name: "Nuevo turno" }),
    ).toBeInTheDocument();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);
  });

  it("usa noValidate: el navegador no bloquea el envío", () => {
    instalarApiFalsa();
    montar();

    expect(screen.getByRole("dialog").querySelector("form")).toHaveAttribute(
      "novalidate",
    );
  });
});

describe("Formulario de nuevo turno: campos obligatorios", () => {
  it("sin paciente muestra Elegí un paciente. y no hace ningún POST", async () => {
    const api = instalarApiFalsa();
    const { user } = montar();
    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");
    completar("Hora", "10:00");

    await enviar(user);

    expect(screen.getByText("Elegí un paciente.")).toBeInTheDocument();
    expect(api.pedidos("POST /turnos")).toHaveLength(0);
  });

  it("sin hora marca el campo Hora con Completá este campo. y no hace ningún POST", async () => {
    const api = instalarApiFalsa();
    const { user } = montar();
    await elegirPaciente(user, api);
    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");

    await enviar(user);

    const hora = screen.getByLabelText("Hora");
    expect(hora).toHaveAccessibleDescription("Completá este campo.");
    expect(hora).toBeInvalid();
    expect(api.pedidos("POST /turnos")).toHaveLength(0);
  });

  it("sin profesional ni prestación marca esos campos", async () => {
    const api = instalarApiFalsa();
    const { user } = montar();
    await elegirPaciente(user, api);
    completar("Hora", "10:00");

    await enviar(user);

    expect(screen.getByLabelText("Profesional")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(screen.getByLabelText("Prestación")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(api.pedidos("POST /turnos")).toHaveLength(0);
  });

  it("sin fecha marca el campo Fecha", async () => {
    const api = instalarApiFalsa();
    const { user } = montar();
    await elegirPaciente(user, api);
    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");
    completar("Hora", "10:00");
    completar("Fecha", "");

    await enviar(user);

    expect(screen.getByLabelText("Fecha")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(api.pedidos("POST /turnos")).toHaveLength(0);
  });
});

describe("Formulario de nuevo turno: sillón según la prestación", () => {
  it("una prestación que requiere sillón lo vuelve obligatorio", async () => {
    const api = instalarApiFalsa();
    const { user } = montar();
    await elegirPaciente(user, api);
    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Prestación"), "Limpieza");
    completar("Hora", "10:00");

    await enviar(user);

    expect(screen.getByLabelText("Sillón")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(api.pedidos("POST /turnos")).toHaveLength(0);
  });

  it("una prestación que no lo requiere oculta el campo y el POST no incluye sillon_id", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = montar();
    await llenar(user, api);
    expect(screen.getByLabelText("Sillón")).toHaveValue(ID_SILLON_1);

    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");
    expect(screen.queryByLabelText("Sillón")).not.toBeInTheDocument();
    await enviar(user);

    expect(api.pedidos("POST /turnos")).toHaveLength(1);
    expect(cuerpoDelPost(api)).not.toHaveProperty("sillon_id");
  });

  it("con una prestación que lo requiere, el POST incluye el sillón elegido", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = montar();
    await llenar(user, api);

    await enviar(user);

    expect(cuerpoDelPost(api)).toMatchObject({ sillon_id: ID_SILLON_1 });
  });
});

describe("Formulario de nuevo turno: duración y zona horaria", () => {
  it("con la duración vacía informa la de la prestación y no la envía", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = montar();
    await llenar(user, api);

    expect(screen.getByText("Por defecto: 45 min")).toBeInTheDocument();
    await enviar(user);

    expect(cuerpoDelPost(api)).not.toHaveProperty("duracion_min");
  });

  it("con otra prestación, informa su propia duración por defecto", async () => {
    const api = instalarApiFalsa();
    const { user } = montar();
    await elegirPaciente(user, api);

    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");

    expect(screen.getByText("Por defecto: 30 min")).toBeInTheDocument();
  });

  it("con una duración cargada la envía", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = montar();
    await llenar(user, api);
    completar("Duración", "60");

    await enviar(user);

    expect(cuerpoDelPost(api)).toMatchObject({ duracion_min: 60 });
  });

  it("interpreta fecha y hora en Buenos Aires aunque el navegador esté en Tokio", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = montar();
    await llenar(user, api);

    await enviar(user);

    expect(cuerpoDelPost(api)).toMatchObject({
      inicio: "2026-11-12T10:00:00-03:00",
      profesional_id: ID_ANA,
      paciente_id: paciente().id,
      prestacion_id: ID_LIMPIEZA,
    });
  });

  it("no valida por adelantado: hora 10:07 y duración 7 llegan a la API", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user } = montar();
    await llenar(user, api);
    completar("Hora", "10:07");
    completar("Duración", "7");

    await enviar(user);

    expect(cuerpoDelPost(api)).toMatchObject({
      inicio: "2026-11-12T10:07:00-03:00",
      duracion_min: 7,
    });
  });

  it("un alta exitosa avisa con el inicio enviado", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const { user, alCrear } = montar();
    await llenar(user, api);

    await enviar(user);

    expect(alCrear).toHaveBeenCalledWith("2026-11-12T10:00:00-03:00");
  });
});

describe("Formulario de nuevo turno: teclado", () => {
  it("Enter en el campo de búsqueda de paciente no envía el formulario", async () => {
    const api = instalarApiFalsa();
    const { user } = montar();

    await user.type(screen.getByLabelText("Buscar paciente"), "car{Enter}");

    expect(api.pedidos("POST /turnos")).toHaveLength(0);
    expect(screen.queryByText("Elegí un paciente.")).not.toBeInTheDocument();
  });

  it("un paciente se elige con Tab y Enter sin enviar el formulario", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [paciente()] });
    const { user } = montar();
    await user.type(screen.getByLabelText("Buscar paciente"), "car");
    await screen.findByRole("button", { name: /Imaginaria, Carla/ });

    await user.tab();
    await user.keyboard("{Enter}");

    expect(
      await screen.findByRole("button", { name: "Cambiar paciente" }),
    ).toBeInTheDocument();
    expect(api.pedidos("POST /turnos")).toHaveLength(0);
  });
});

/** Con el hook real de catálogos, para que la relectura llegue al formulario. */
function Arnes({
  alCrear,
  alReleerAgenda,
}: {
  alCrear: () => void;
  alReleerAgenda: () => void;
}) {
  const { catalogos, recargar } = useCatalogos();
  if (catalogos === null) return null;
  return (
    <FormularioNuevoTurno
      abierto
      catalogos={catalogos}
      fechaInicial="2026-11-12"
      profesionalInicial={null}
      alCrear={alCrear}
      alCerrar={() => {}}
      alReleerCatalogos={recargar}
      alReleerAgenda={alReleerAgenda}
    />
  );
}

async function montarConCatalogos(api: ApiFalsa) {
  api.responder("GET /profesionales", {
    status: 200,
    cuerpo: CATALOGOS.profesionales,
  });
  api.responder("GET /sillones", { status: 200, cuerpo: CATALOGOS.sillones });
  api.responder("GET /prestaciones", {
    status: 200,
    cuerpo: CATALOGOS.prestaciones,
  });
  const alCrear = vi.fn();
  const alReleerAgenda = vi.fn();
  const user = userEvent.setup();
  render(
    <ProveedorSesion>
      <Arnes alCrear={alCrear} alReleerAgenda={alReleerAgenda} />
    </ProveedorSesion>,
  );
  await screen.findByRole("dialog", { name: "Nuevo turno" });
  return { user, alCrear, alReleerAgenda };
}

function rechazar(api: ApiFalsa, status: number, detail: unknown) {
  api.responder("POST /turnos", { status, cuerpo: { detail } });
}

describe("Formulario de nuevo turno: reglas rechazadas por la API", () => {
  it("fuera_de_horario es un error general en una alerta", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, { codigo: "fuera_de_horario", mensaje: "técnico" });

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El turno queda fuera del horario de atención del profesional.",
    );
  });

  it.each([
    ["inicio_en_pasado", "Hora", "El inicio no puede estar en el pasado."],
    [
      "inicio_no_alineado",
      "Hora",
      "El horario debe ser múltiplo de 5 minutos.",
    ],
    [
      "duracion_invalida",
      "Duración",
      "La duración debe ser múltiplo de 5, de 5 a 480 minutos.",
    ],
  ])(
    "%s marca el campo %s, asociado a su error",
    async (codigo, campo, texto) => {
      const api = instalarApiFalsa();
      const { user } = await montarConCatalogos(api);
      await llenar(user, api);
      rechazar(api, 422, { codigo, mensaje: "técnico" });

      await enviar(user);

      await waitFor(() =>
        expect(screen.getByLabelText(campo)).toHaveAccessibleDescription(texto),
      );
      expect(screen.getByLabelText(campo)).toBeInvalid();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    },
  );

  it("sillon_requerido con el catálogo desactualizado relee los catálogos y muestra el campo Sillón", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await elegirPaciente(user, api);
    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");
    completar("Hora", "10:00");
    expect(screen.queryByLabelText("Sillón")).not.toBeInTheDocument();
    rechazar(api, 422, { codigo: "sillon_requerido", mensaje: "técnico" });

    await enviar(user);

    expect(await screen.findByLabelText("Sillón")).toHaveAccessibleDescription(
      "Esta prestación requiere un sillón.",
    );
    expect(api.pedidos("GET /prestaciones")).toHaveLength(2);
    expect(api.pedidos("GET /sillones")).toHaveLength(2);
  });

  it("sillon_no_corresponde es un error general y relee los catálogos", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, { codigo: "sillon_no_corresponde", mensaje: "técnico" });

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Esta prestación no usa sillón.",
    );
    await waitFor(() =>
      expect(api.pedidos("GET /prestaciones")).toHaveLength(2),
    );
  });

  it("un turno_en_bloqueo relee la agenda", async () => {
    const api = instalarApiFalsa();
    const { user, alReleerAgenda } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, { codigo: "turno_en_bloqueo", mensaje: "técnico" });

    await enviar(user);

    await screen.findByRole("alert");
    expect(alReleerAgenda).toHaveBeenCalledTimes(1);
  });
});

describe("Formulario de nuevo turno: referencias inválidas", () => {
  const SILLON_INACTIVO = {
    codigo: "referencia_invalida",
    referencia: "sillon",
    motivo: "inactiva",
  };

  it("un sillón inactivo se marca, relee los catálogos y sigue elegido como (inactivo)", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, SILLON_INACTIVO);
    api.responder("GET /sillones", {
      status: 200,
      cuerpo: [
        sillon({ activo: false }),
        sillon({ id: ID_SILLON_2, nombre: "Sillón 2" }),
      ],
    });

    await enviar(user);

    expect(await screen.findByLabelText("Sillón")).toHaveAccessibleDescription(
      "El sillón está inactivo.",
    );
    await waitFor(() =>
      expect(
        screen.getByRole("option", {
          name: "Sillón 1 (inactivo)",
          selected: true,
        }),
      ).toBeInTheDocument(),
    );
    expect(api.pedidos("GET /sillones")).toHaveLength(2);
  });

  it("al cambiar el valor rechazado, la opción inactiva deja de ofrecerse", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, SILLON_INACTIVO);
    api.responder("GET /sillones", {
      status: 200,
      cuerpo: [
        sillon({ activo: false }),
        sillon({ id: ID_SILLON_2, nombre: "Sillón 2" }),
      ],
    });
    await enviar(user);
    await screen.findByRole("option", { name: "Sillón 1 (inactivo)" });

    await user.selectOptions(screen.getByLabelText("Sillón"), "Sillón 2");

    expect(
      screen.queryByRole("option", { name: "Sillón 1 (inactivo)" }),
    ).not.toBeInTheDocument();
  });

  it("un profesional inexistente se ve con el texto genérico y sin la marca (inactivo)", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, {
      codigo: "referencia_invalida",
      referencia: "profesional",
      motivo: "inexistente",
    });
    api.responder("GET /profesionales", { status: 200, cuerpo: [] });

    await enviar(user);

    expect(
      await screen.findByLabelText("Profesional"),
    ).toHaveAccessibleDescription("El profesional no existe.");
    await waitFor(() =>
      expect(
        screen.getByRole("option", {
          name: "Profesional no disponible",
          selected: true,
        }),
      ).toBeInTheDocument(),
    );
  });

  it("una prestación inactiva marca su campo y conserva la opción rechazada", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, {
      codigo: "referencia_invalida",
      referencia: "prestacion",
      motivo: "inactiva",
    });
    api.responder("GET /prestaciones", {
      status: 200,
      cuerpo: [prestacion({ activa: false })],
    });

    await enviar(user);

    expect(
      await screen.findByLabelText("Prestación"),
    ).toHaveAccessibleDescription("La prestación está inactiva.");
    await waitFor(() =>
      expect(
        screen.getByRole("option", {
          name: "Limpieza (inactivo)",
          selected: true,
        }),
      ).toBeInTheDocument(),
    );
  });

  it("un paciente inactivo se marca en el selector de paciente", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, {
      codigo: "referencia_invalida",
      referencia: "paciente",
      motivo: "inactiva",
    });

    await enviar(user);

    expect(
      await screen.findByText("El paciente está inactivo."),
    ).toBeInTheDocument();
  });

  it("si falla la relectura de catálogos el formulario sigue abierto con sus datos y muestra el error como general", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, SILLON_INACTIVO);
    api.responder("GET /sillones", { red: true });

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo conectar con el servidor.",
    );
    expect(
      screen.getByRole("dialog", { name: "Nuevo turno" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(screen.getByLabelText("Hora")).toHaveValue("10:00");
    expect(
      screen.queryByRole("button", { name: "Reintentar" }),
    ).not.toBeInTheDocument();
  });
});

describe("Formulario de nuevo turno: sillón tras un rechazo de la API", () => {
  const ID_CONSULTA = "00000000-0000-4000-8000-0000000000d3";
  const CONSULTA = prestacion({
    id: ID_CONSULTA,
    nombre: "Consulta",
    duracion_min: 15,
    requiere_sillon: false,
  });

  it("tras un sillón rechazado, cambiar a una prestación sin sillón lo oculta y el POST no incluye sillon_id", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, {
      codigo: "referencia_invalida",
      referencia: "sillon",
      motivo: "inactiva",
    });
    await enviar(user);
    await waitFor(() =>
      expect(screen.getByLabelText("Sillón")).toHaveAccessibleDescription(
        "El sillón está inactivo.",
      ),
    );
    api.responder("POST /turnos", { status: 201, cuerpo: {} });

    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");
    expect(screen.queryByLabelText("Sillón")).not.toBeInTheDocument();
    await enviar(user);

    await waitFor(() => expect(api.pedidos("POST /turnos")).toHaveLength(2));
    expect(api.pedidos("POST /turnos")[1]?.cuerpo).not.toHaveProperty(
      "sillon_id",
    );
  });

  it("tras sillon_requerido, otra prestación sin sillón no muestra el campo", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await elegirPaciente(user, api);
    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");
    completar("Hora", "10:00");
    api.responder("GET /prestaciones", {
      status: 200,
      cuerpo: [...CATALOGOS.prestaciones, CONSULTA],
    });
    rechazar(api, 422, { codigo: "sillon_requerido", mensaje: "técnico" });
    await enviar(user);
    await screen.findByRole("option", { name: "Consulta" });

    await user.selectOptions(screen.getByLabelText("Prestación"), "Consulta");

    expect(screen.queryByLabelText("Sillón")).not.toBeInTheDocument();
  });

  it("tras sillon_requerido, el campo sigue visible al volver a la prestación rechazada", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await elegirPaciente(user, api);
    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Ficticia, Ana",
    );
    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");
    completar("Hora", "10:00");
    rechazar(api, 422, { codigo: "sillon_requerido", mensaje: "técnico" });
    await enviar(user);
    await screen.findByLabelText("Sillón");

    await user.selectOptions(screen.getByLabelText("Prestación"), "Limpieza");
    await user.selectOptions(screen.getByLabelText("Prestación"), "Control");

    expect(screen.getByLabelText("Sillón")).toBeInTheDocument();
  });
});

describe("Formulario de nuevo turno: validación, permisos y red", () => {
  it("un error de validación marca el campo con un texto propio y no muestra el msg de la API", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, [
      {
        loc: ["body", "duracion_min"],
        msg: "Input should be a valid integer",
        type: "x",
      },
    ]);

    await enviar(user);

    await waitFor(() =>
      expect(screen.getByLabelText("Duración")).toHaveAccessibleDescription(
        "Revisá este campo.",
      ),
    );
    expect(screen.queryByText(/Input should be/)).not.toBeInTheDocument();
  });

  it("un error de validación sin campo es un error general", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, [{ loc: ["body"], msg: "x", type: "x" }]);

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Revisá los datos ingresados.",
    );
  });

  it("una fecha como 1900-01-15, con desfasaje con segundos, no lanza y la API la rechaza sobre Hora", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    completar("Fecha", "1900-01-15");
    rechazar(api, 422, [
      {
        loc: ["body", "inicio"],
        msg: "Input should have timezone info",
        type: "x",
      },
    ]);

    await enviar(user);

    await waitFor(() =>
      expect(screen.getByLabelText("Hora")).toHaveAccessibleDescription(
        "Revisá este campo.",
      ),
    );
    expect(String(cuerpoDelPost(api).inicio)).toMatch(/^1900-01-15T10:00:00-/);
  });

  it("un 403 muestra la falta de permiso y deja el formulario abierto", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 403, { codigo: "rol_insuficiente", mensaje: "técnico" });

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No tenés permiso para esta operación.",
    );
    expect(
      screen.getByRole("dialog", { name: "Nuevo turno" }),
    ).toBeInTheDocument();
  });

  it("una falla de red muestra el mensaje y conserva los datos", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    api.responder("POST /turnos", { red: true });

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo conectar con el servidor.",
    );
    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(screen.getByLabelText("Hora")).toHaveValue("10:00");
    expect(screen.getByRole("button", { name: "Crear turno" })).toBeEnabled();
  });

  it("un código desconocido muestra el mensaje de la API", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 422, { codigo: "otro_codigo", mensaje: "Mensaje de la API" });

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Mensaje de la API",
    );
  });

  it("un 409 solapamiento se anuncia como alerta", async () => {
    const api = instalarApiFalsa();
    const { user } = await montarConCatalogos(api);
    await llenar(user, api);
    rechazar(api, 409, { codigo: "solapamiento", recursos: ["profesional"] });

    await enviar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ese horario ya está ocupado para el profesional.",
    );
  });
});
