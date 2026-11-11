import { ErrorApi } from "../../shared/api/errorApi";
import { interpretarErrorTurno } from "./erroresTurno";

function error(
  status: number,
  codigo: string | null,
  datos: Record<string, unknown> = {},
  mensaje = "Mensaje técnico de la API",
) {
  return new ErrorApi({ status, codigo, mensaje, datos });
}

const SIN_MARCAS = {
  turnoObsoleto: false,
  releerCatalogos: false,
  releerAgenda: false,
};

describe("interpretarErrorTurno: solapamiento", () => {
  it.each([
    [["profesional"], "Ese horario ya está ocupado para el profesional."],
    [
      ["profesional", "paciente"],
      "Ese horario ya está ocupado para el profesional y el paciente.",
    ],
    [
      ["profesional", "sillon", "paciente"],
      "Ese horario ya está ocupado para el profesional, el sillón y el paciente.",
    ],
    [["sillon"], "Ese horario ya está ocupado para el sillón."],
  ])("con los recursos %j dice %s", (recursos, texto) => {
    const resultado = interpretarErrorTurno(
      error(409, "solapamiento", { recursos }, "no se usa"),
      "crear",
    );

    expect(resultado).toEqual({
      general: texto,
      porCampo: {},
      ...SIN_MARCAS,
      releerAgenda: true,
    });
  });

  it("nombra los recursos en el orden fijo aunque lleguen desordenados", () => {
    const resultado = interpretarErrorTurno(
      error(409, "solapamiento", {
        recursos: ["paciente", "sillon", "profesional"],
      }),
      "reprogramar",
    );

    expect(resultado.general).toBe(
      "Ese horario ya está ocupado para el profesional, el sillón y el paciente.",
    );
  });
});

describe("interpretarErrorTurno: reglas de agenda", () => {
  it.each([
    [
      "fuera_de_horario",
      "El turno queda fuera del horario de atención del profesional.",
      false,
    ],
    [
      "turno_en_bloqueo",
      "El turno se superpone con un bloqueo de la agenda del profesional.",
      true,
    ],
  ])("%s es un error general", (codigo, texto, releerAgenda) => {
    expect(interpretarErrorTurno(error(422, codigo), "crear")).toEqual({
      general: texto,
      porCampo: {},
      ...SIN_MARCAS,
      releerAgenda,
    });
  });

  it.each([
    ["inicio_en_pasado", "hora", "El inicio no puede estar en el pasado."],
    [
      "inicio_no_alineado",
      "hora",
      "El horario debe ser múltiplo de 5 minutos.",
    ],
    [
      "duracion_invalida",
      "duracion",
      "La duración debe ser múltiplo de 5, de 5 a 480 minutos.",
    ],
  ])("%s va al campo %s", (codigo, campo, texto) => {
    expect(interpretarErrorTurno(error(422, codigo), "crear")).toEqual({
      general: null,
      porCampo: { [campo]: texto },
      ...SIN_MARCAS,
    });
  });

  it("sillon_requerido va al campo Sillón y relee los catálogos", () => {
    expect(
      interpretarErrorTurno(error(422, "sillon_requerido"), "crear"),
    ).toEqual({
      general: null,
      porCampo: { sillon: "Esta prestación requiere un sillón." },
      ...SIN_MARCAS,
      releerCatalogos: true,
    });
  });

  it("sillon_no_corresponde es general y relee los catálogos", () => {
    expect(
      interpretarErrorTurno(error(422, "sillon_no_corresponde"), "crear"),
    ).toEqual({
      general: "Esta prestación no usa sillón.",
      porCampo: {},
      ...SIN_MARCAS,
      releerCatalogos: true,
    });
  });
});

describe("interpretarErrorTurno: referencia_invalida", () => {
  it.each([
    ["sillon", "inactiva", "sillon", "El sillón está inactivo."],
    ["profesional", "inexistente", "profesional", "El profesional no existe."],
    ["profesional", "inactiva", "profesional", "El profesional está inactivo."],
    ["prestacion", "inactiva", "prestacion", "La prestación está inactiva."],
    ["prestacion", "inexistente", "prestacion", "La prestación no existe."],
    ["paciente", "inactiva", "paciente", "El paciente está inactivo."],
    ["paciente", "inexistente", "paciente", "El paciente no existe."],
    ["sillon", "inexistente", "sillon", "El sillón no existe."],
  ])("en el alta, %s %s va al campo %s", (referencia, motivo, campo, texto) => {
    expect(
      interpretarErrorTurno(
        error(422, "referencia_invalida", { referencia, motivo }),
        "crear",
      ),
    ).toEqual({
      general: null,
      porCampo: { [campo]: texto },
      ...SIN_MARCAS,
      releerCatalogos: true,
    });
  });

  it("al reprogramar, un profesional o un sillón rechazados van a su campo", () => {
    expect(
      interpretarErrorTurno(
        error(422, "referencia_invalida", {
          referencia: "profesional",
          motivo: "inactiva",
        }),
        "reprogramar",
      ).porCampo,
    ).toEqual({ profesional: "El profesional está inactivo." });
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
    "al reprogramar, %s inactivo es un error general que remite a cancelar",
    (referencia, texto) => {
      expect(
        interpretarErrorTurno(
          error(422, "referencia_invalida", { referencia, motivo: "inactiva" }),
          "reprogramar",
        ),
      ).toEqual({
        general: texto,
        porCampo: {},
        ...SIN_MARCAS,
        releerCatalogos: true,
      });
    },
  );

  it("una referencia desconocida cae en un error general", () => {
    const resultado = interpretarErrorTurno(
      error(
        422,
        "referencia_invalida",
        { referencia: "otra", motivo: "inactiva" },
        "Referencia inválida",
      ),
      "crear",
    );

    expect(resultado.porCampo).toEqual({});
    expect(resultado.general).toBe("Referencia inválida");
    expect(resultado.releerCatalogos).toBe(true);
  });
});

describe("interpretarErrorTurno: validación", () => {
  function validacion(
    errores: Array<{ campo: string | null; mensaje: string }>,
  ) {
    return new ErrorApi({
      status: 422,
      codigo: "validacion",
      mensaje: "Revisá los datos ingresados.",
      errores,
    });
  }

  it("marca el campo con un texto propio y nunca muestra el msg de la API", () => {
    const resultado = interpretarErrorTurno(
      validacion([
        { campo: "duracion_min", mensaje: "Input should be a valid integer" },
      ]),
      "crear",
    );

    expect(resultado).toEqual({
      general: null,
      porCampo: { duracion: "Revisá este campo." },
      ...SIN_MARCAS,
    });
    expect(JSON.stringify(resultado)).not.toContain("Input should be");
  });

  it("mapea inicio al campo Hora", () => {
    expect(
      interpretarErrorTurno(
        validacion([{ campo: "inicio", mensaje: "x" }]),
        "crear",
      ).porCampo,
    ).toEqual({ hora: "Revisá este campo." });
  });

  it.each([
    ["profesional_id", "profesional"],
    ["paciente_id", "paciente"],
    ["prestacion_id", "prestacion"],
    ["sillon_id", "sillon"],
  ])("mapea %s al campo %s", (campoApi, campo) => {
    expect(
      interpretarErrorTurno(
        validacion([{ campo: campoApi, mensaje: "x" }]),
        "crear",
      ).porCampo,
    ).toEqual({ [campo]: "Revisá este campo." });
  });

  it("un error con campo nulo es general", () => {
    expect(
      interpretarErrorTurno(
        validacion([{ campo: null, mensaje: "x" }]),
        "crear",
      ),
    ).toEqual({
      general: "Revisá los datos ingresados.",
      porCampo: {},
      ...SIN_MARCAS,
    });
  });

  it("un campo desconocido también es general, y los conocidos siguen en su campo", () => {
    const resultado = interpretarErrorTurno(
      validacion([
        { campo: "inicio", mensaje: "x" },
        { campo: "desconocido", mensaje: "y" },
      ]),
      "crear",
    );

    expect(resultado.porCampo).toEqual({ hora: "Revisá este campo." });
    expect(resultado.general).toBe("Revisá los datos ingresados.");
  });

  it("una validación sin ningún error informado es general", () => {
    expect(interpretarErrorTurno(validacion([]), "crear").general).toBe(
      "Revisá los datos ingresados.",
    );
  });
});

describe("interpretarErrorTurno: el turno cambió", () => {
  it.each([
    [409, "turno_ya_cancelado", "Este turno ya fue cancelado."],
    [409, "turno_ya_iniciado", "Este turno ya inició: no se puede modificar."],
    [404, "turno_inexistente", "Este turno ya no existe."],
  ])(
    "%i %s deja el turno obsoleto y relee la agenda",
    (status, codigo, texto) => {
      expect(
        interpretarErrorTurno(error(status, codigo), "reprogramar"),
      ).toEqual({
        general: texto,
        porCampo: {},
        turnoObsoleto: true,
        releerCatalogos: false,
        releerAgenda: true,
      });
    },
  );

  it("también al cancelar", () => {
    expect(
      interpretarErrorTurno(error(409, "turno_ya_cancelado"), "cancelar")
        .turnoObsoleto,
    ).toBe(true);
  });
});

describe("interpretarErrorTurno: permisos y otros errores", () => {
  it("rol_insuficiente dice que no tiene permiso", () => {
    expect(
      interpretarErrorTurno(error(403, "rol_insuficiente"), "crear"),
    ).toEqual({
      general: "No tenés permiso para esta operación.",
      porCampo: {},
      ...SIN_MARCAS,
    });
  });

  it("un 403 con otro código dice lo mismo", () => {
    expect(
      interpretarErrorTurno(error(403, "profesional_ajeno"), "crear").general,
    ).toBe("No tenés permiso para esta operación.");
  });

  it("un código desconocido muestra el mensaje del error", () => {
    expect(
      interpretarErrorTurno(
        error(422, "otro_codigo", {}, "Mensaje de la API"),
        "crear",
      ),
    ).toEqual({
      general: "Mensaje de la API",
      porCampo: {},
      ...SIN_MARCAS,
    });
  });

  it("una falla de red (status 0) muestra el mensaje del error", () => {
    expect(
      interpretarErrorTurno(
        new ErrorApi({
          status: 0,
          codigo: null,
          mensaje: "No se pudo conectar con el servidor.",
        }),
        "crear",
      ).general,
    ).toBe("No se pudo conectar con el servidor.");
  });

  it("un error sin código muestra el mensaje del error", () => {
    expect(
      interpretarErrorTurno(
        new ErrorApi({
          status: 500,
          codigo: null,
          mensaje: "Ocurrió un error. Intentá de nuevo.",
        }),
        "cancelar",
      ).general,
    ).toBe("Ocurrió un error. Intentá de nuevo.");
  });
});
