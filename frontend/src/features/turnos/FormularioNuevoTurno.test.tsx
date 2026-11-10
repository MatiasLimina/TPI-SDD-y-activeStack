import { fireEvent, render, screen } from "@testing-library/react";
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
import type { Catalogos } from "../agenda/useCatalogos";
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
