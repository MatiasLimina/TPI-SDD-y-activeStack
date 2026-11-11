import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { instalarApiFalsa, type ApiFalsa } from "../../test/apiFalsa";
import {
  ID_ANA,
  ID_CONTROL,
  ID_LUIS,
  ID_SILLON_1,
  ID_SILLON_2,
  ID_TURNO,
  prestacion,
  profesional,
  sillon,
  turno,
} from "../../test/fabricas";
import { crearNombres } from "../agenda/nombres";
import type { Catalogos } from "../agenda/useCatalogos";
import { ProveedorSesion } from "../sesion/ProveedorSesion";
import { FormularioReprogramar } from "./FormularioReprogramar";

const LUIS = profesional({
  id: ID_LUIS,
  nombre: "Luis",
  apellido: "Inventado",
});

const CATALOGOS: Catalogos = {
  profesionales: [profesional(), LUIS],
  sillones: [sillon(), sillon({ id: ID_SILLON_2, nombre: "Sillón 2" })],
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

/** Turno del 2026-11-12 de 10:00 a 10:45, de Ana, con Limpieza y Sillón 1. */
const TURNO = turno({
  inicio: "2026-11-12T10:00:00-03:00",
  fin: "2026-11-12T10:45:00-03:00",
});

interface Opciones {
  catalogos?: Catalogos;
  turno?: ReturnType<typeof turno>;
}

function montar(opciones: Opciones = {}) {
  const catalogos = opciones.catalogos ?? CATALOGOS;
  const alReprogramado = vi.fn();
  const alCerrar = vi.fn();
  const alReleerAgenda = vi.fn();
  const user = userEvent.setup();
  render(
    <ProveedorSesion>
      <FormularioReprogramar
        turno={opciones.turno ?? TURNO}
        catalogos={catalogos}
        nombres={crearNombres(catalogos)}
        alReprogramado={alReprogramado}
        alCerrar={alCerrar}
        alReleerCatalogos={() => Promise.resolve(null)}
        alReleerAgenda={alReleerAgenda}
      />
    </ProveedorSesion>,
  );
  return { user, alReprogramado, alCerrar, alReleerAgenda };
}

type Usuario = ReturnType<typeof userEvent.setup>;

function cambiar(campo: string, valor: string) {
  fireEvent.change(screen.getByLabelText(campo), { target: { value: valor } });
}

function enviar(user: Usuario) {
  return user.click(screen.getByRole("button", { name: "Reprogramar" }));
}

function cuerpoDelPatch(api: ApiFalsa): unknown {
  return api.pedidos(`PATCH /turnos/${ID_TURNO}/reprogramar`)[0]?.cuerpo;
}

function pedidosPatch(api: ApiFalsa) {
  return api.pedidos(`PATCH /turnos/${ID_TURNO}/reprogramar`);
}

function apiConPatchExitoso() {
  const api = instalarApiFalsa();
  api.responder(`PATCH /turnos/${ID_TURNO}/reprogramar`, {
    status: 200,
    cuerpo: {},
  });
  return api;
}

describe("Formulario de reprogramación: datos", () => {
  it("se abre como diálogo modal precargado en la hora de Buenos Aires", () => {
    instalarApiFalsa();
    montar();

    expect(
      screen.getByRole("dialog", { name: "Reprogramar turno" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Fecha")).toHaveValue("2026-11-12");
    expect(screen.getByLabelText("Hora")).toHaveValue("10:00");
    expect(screen.getByLabelText("Duración")).toHaveValue(45);
    expect(screen.getByLabelText("Profesional")).toHaveValue(ID_ANA);
    expect(screen.getByLabelText("Sillón")).toHaveValue(ID_SILLON_1);
  });

  it("paciente y prestación se ven como texto, sin controles, con la indicación de cancelar", () => {
    instalarApiFalsa();
    montar();

    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(screen.getByText("Limpieza")).toBeInTheDocument();
    expect(
      screen.getByText("Para cambiarlos, cancelá este turno y creá uno nuevo."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Paciente")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Prestación")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Buscar paciente")).not.toBeInTheDocument();
  });

  it("ofrece los profesionales activos y el actual aunque esté desactivado", () => {
    instalarApiFalsa();
    montar({
      catalogos: {
        ...CATALOGOS,
        profesionales: [
          profesional({ activo: false }),
          { ...LUIS, activo: false },
          profesional({
            id: "00000000-0000-4000-8000-0000000000a3",
            nombre: "Eva",
            apellido: "Ejemplar",
          }),
        ],
      },
    });

    expect(
      screen.getByRole("option", { name: "Ficticia, Ana (inactivo)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Ejemplar, Eva" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: /Inventado/ }),
    ).not.toBeInTheDocument();
  });

  it("ofrece el sillón actual aunque esté desactivado", () => {
    instalarApiFalsa();
    montar({
      catalogos: {
        ...CATALOGOS,
        sillones: [
          sillon({ activo: false }),
          sillon({ id: ID_SILLON_2, nombre: "Sillón 2" }),
        ],
      },
    });

    expect(
      screen.getByRole("option", { name: "Sillón 1 (inactivo)" }),
    ).toBeInTheDocument();
  });

  it("usa noValidate", () => {
    instalarApiFalsa();
    montar();

    expect(screen.getByRole("dialog").querySelector("form")).toHaveAttribute(
      "novalidate",
    );
  });
});

describe("Formulario de reprogramación: obligatorios", () => {
  it("con la duración vaciada muestra Ingresá la duración. y no hace ningún PATCH", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    cambiar("Duración", "");
    await enviar(user);

    expect(screen.getByLabelText("Duración")).toHaveAccessibleDescription(
      "Ingresá la duración.",
    );
    expect(pedidosPatch(api)).toHaveLength(0);
  });

  it("con la hora y la fecha vaciadas muestra Completá este campo. en cada una y no hace ningún PATCH", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    cambiar("Hora", "");
    cambiar("Fecha", "");
    await enviar(user);

    expect(screen.getByLabelText("Hora")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(screen.getByLabelText("Fecha")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(pedidosPatch(api)).toHaveLength(0);
  });
});

describe("Formulario de reprogramación: solo lo que cambió", () => {
  it("si solo cambia la hora, el cuerpo es exactamente el inicio", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    cambiar("Hora", "15:00");
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({
      inicio: "2026-11-12T15:00:00-03:00",
    });
  });

  it("si solo cambia la fecha, el cuerpo es exactamente el inicio", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    cambiar("Fecha", "2026-11-13");
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({
      inicio: "2026-11-13T10:00:00-03:00",
    });
  });

  it("si solo cambia el profesional, el cuerpo es exactamente el profesional", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Inventado, Luis",
    );
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({ profesional_id: ID_LUIS });
  });

  it("si solo cambia el sillón, el cuerpo es exactamente el sillón", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    await user.selectOptions(screen.getByLabelText("Sillón"), "Sillón 2");
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({ sillon_id: ID_SILLON_2 });
  });

  it("si solo cambia la duración, el cuerpo es exactamente la duración", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    cambiar("Duración", "60");
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({ duracion_min: 60 });
  });

  it("con varios cambios envía solo esos y nunca paciente ni prestación", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    cambiar("Hora", "11:30");
    cambiar("Duración", "30");
    await enviar(user);

    const cuerpo = cuerpoDelPatch(api);
    expect(cuerpo).toEqual({
      inicio: "2026-11-12T11:30:00-03:00",
      duracion_min: 30,
    });
    expect(cuerpo).not.toHaveProperty("paciente_id");
    expect(cuerpo).not.toHaveProperty("prestacion_id");
  });

  it("escribir el mismo valor que ya tenía no cuenta como cambio", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    cambiar("Duración", "45");
    await enviar(user);

    expect(screen.getByText("No hiciste cambios.")).toBeInTheDocument();
    expect(pedidosPatch(api)).toHaveLength(0);
  });

  it("sin cambios informa No hiciste cambios. y no hace ningún pedido", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar();

    await enviar(user);

    expect(screen.getByText("No hiciste cambios.")).toBeInTheDocument();
    expect(pedidosPatch(api)).toHaveLength(0);
  });

  it("con un sillón sobrante (la prestación ya no lo requiere) y el formulario intacto, tampoco hay pedido", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar({
      catalogos: {
        ...CATALOGOS,
        prestaciones: [prestacion({ requiere_sillon: false })],
      },
    });

    await enviar(user);

    expect(screen.getByText("No hiciste cambios.")).toBeInTheDocument();
    expect(pedidosPatch(api)).toHaveLength(0);
  });

  it("si la prestación ya no requiere sillón y hay otro cambio, envía sillon_id nulo junto con él", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar({
      catalogos: {
        ...CATALOGOS,
        prestaciones: [prestacion({ requiere_sillon: false })],
      },
    });
    expect(screen.queryByLabelText("Sillón")).not.toBeInTheDocument();

    cambiar("Hora", "15:00");
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({
      inicio: "2026-11-12T15:00:00-03:00",
      sillon_id: null,
    });
  });

  it("si la prestación pasó a requerir sillón y el turno no tiene, pide el sillón antes de comparar", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar({ turno: { ...TURNO, sillon_id: null } });

    await enviar(user);

    expect(screen.getByLabelText("Sillón")).toHaveValue("");
    expect(screen.getByLabelText("Sillón")).toHaveAccessibleDescription(
      "Completá este campo.",
    );
    expect(screen.queryByText("No hiciste cambios.")).not.toBeInTheDocument();
    expect(pedidosPatch(api)).toHaveLength(0);
  });

  it("al elegir el sillón que faltaba, lo envía", async () => {
    const api = apiConPatchExitoso();
    const { user } = montar({ turno: { ...TURNO, sillon_id: null } });

    await user.selectOptions(screen.getByLabelText("Sillón"), "Sillón 2");
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({ sillon_id: ID_SILLON_2 });
  });

  it("una reprogramación exitosa avisa al padre", async () => {
    apiConPatchExitoso();
    const { user, alReprogramado } = montar();

    cambiar("Hora", "15:00");
    await enviar(user);

    expect(alReprogramado).toHaveBeenCalledTimes(1);
  });
});

function rechazar(api: ApiFalsa, status: number, detail: unknown) {
  api.responder(`PATCH /turnos/${ID_TURNO}/reprogramar`, {
    status,
    cuerpo: { detail },
  });
}

describe("Formulario de reprogramación: sillón tras un rechazo de la API", () => {
  it("sillon_requerido con el catálogo desactualizado muestra el campo Sillón", async () => {
    const api = instalarApiFalsa();
    rechazar(api, 422, { codigo: "sillon_requerido", mensaje: "técnico" });
    const { user } = montar({
      catalogos: {
        ...CATALOGOS,
        prestaciones: [prestacion({ requiere_sillon: false })],
      },
    });
    expect(screen.queryByLabelText("Sillón")).not.toBeInTheDocument();
    cambiar("Hora", "15:00");

    await enviar(user);

    expect(await screen.findByLabelText("Sillón")).toHaveAccessibleDescription(
      "Esta prestación requiere un sillón.",
    );
  });
});

describe("Formulario de reprogramación: el turno cambió", () => {
  it.each([
    [409, "turno_ya_cancelado", "Este turno ya fue cancelado."],
    [409, "turno_ya_iniciado", "Este turno ya inició: no se puede modificar."],
    [404, "turno_inexistente", "Este turno ya no existe."],
  ])(
    "%i %s explica el motivo, deshabilita el envío y relee la agenda",
    async (status, codigo, texto) => {
      const api = instalarApiFalsa();
      rechazar(api, status, { codigo, mensaje: "técnico" });
      const { user, alReleerAgenda } = montar();
      cambiar("Hora", "15:00");

      await enviar(user);

      expect(await screen.findByRole("alert")).toHaveTextContent(texto);
      expect(
        screen.getByRole("button", { name: "Reprogramar" }),
      ).toBeDisabled();
      expect(screen.getByRole("button", { name: "Cerrar" })).toBeEnabled();
      expect(alReleerAgenda).toHaveBeenCalledTimes(1);
      expect(pedidosPatch(api)).toHaveLength(1);
    },
  );

  it("última escritura gana: el PATCH lleva solo el inicio aunque otro usuario cambió el profesional", async () => {
    const api = apiConPatchExitoso();
    const { user, alReprogramado } = montar();

    cambiar("Hora", "15:00");
    await enviar(user);

    expect(cuerpoDelPatch(api)).toEqual({
      inicio: "2026-11-12T15:00:00-03:00",
    });
    expect(alReprogramado).toHaveBeenCalledTimes(1);
  });

  it.each([
    [
      "paciente",
      "El paciente está inactivo: este turno no se puede reprogramar, pero sí cancelar.",
    ],
    [
      "prestacion",
      "La prestación está inactiva: este turno no se puede reprogramar, pero sí cancelar.",
    ],
  ])(
    "%s inactivo indica que solo se puede cancelar",
    async (referencia, texto) => {
      const api = instalarApiFalsa();
      rechazar(api, 422, {
        codigo: "referencia_invalida",
        referencia,
        motivo: "inactiva",
      });
      const { user } = montar();
      cambiar("Hora", "15:00");

      await enviar(user);

      expect(await screen.findByRole("alert")).toHaveTextContent(texto);
      expect(screen.getByRole("button", { name: "Reprogramar" })).toBeEnabled();
    },
  );

  it("un valor rechazado que es el actual del turno se sigue ofreciendo al elegir otro", async () => {
    const api = instalarApiFalsa();
    rechazar(api, 422, {
      codigo: "referencia_invalida",
      referencia: "profesional",
      motivo: "inactiva",
    });
    const { user } = montar({
      catalogos: {
        ...CATALOGOS,
        profesionales: [profesional({ activo: false }), LUIS],
      },
    });
    cambiar("Hora", "15:00");
    await enviar(user);
    await screen.findByText("El profesional está inactivo.");

    await user.selectOptions(
      screen.getByLabelText("Profesional"),
      "Inventado, Luis",
    );

    expect(
      screen.getByRole("option", { name: "Ficticia, Ana (inactivo)" }),
    ).toBeInTheDocument();
  });
});
