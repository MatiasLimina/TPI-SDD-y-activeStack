import { crearNombres } from "../agenda/nombres";
import {
  auditoriaCancelar,
  auditoriaCrear,
  auditoriaReprogramar,
  ID_ANA,
  ID_LIMPIEZA,
  ID_SILLON_1,
  ID_SILLON_2,
  ID_USUARIO_OTRO,
  ID_USUARIO_PRUEBA,
  prestacion,
  profesional,
  sillon,
  valoresDeAuditoria,
} from "../../test/fabricas";
import {
  autorDe,
  cambiosDeReprogramacion,
  datosDeCreacion,
  etiquetaAccion,
  textoDeCancelacion,
} from "./historial";

const nombres = crearNombres({
  profesionales: [profesional({ id: ID_ANA })],
  sillones: [
    sillon({ id: ID_SILLON_1, nombre: "Sillón 1" }),
    sillon({ id: ID_SILLON_2, nombre: "Sillón 2" }),
  ],
  prestaciones: [prestacion({ id: ID_LIMPIEZA, nombre: "Limpieza" })],
});

describe("etiquetaAccion", () => {
  it.each([
    ["crear", "Creación"],
    ["reprogramar", "Reprogramación"],
    ["cancelar", "Cancelación"],
  ] as const)("%s se muestra como %s", (accion, texto) => {
    expect(etiquetaAccion(accion)).toBe(texto);
  });
});

describe("autorDe", () => {
  it("es Vos si el usuario del registro es el de la sesión", () => {
    expect(autorDe(ID_USUARIO_PRUEBA, ID_USUARIO_PRUEBA)).toBe("Vos");
  });

  it("es Otro usuario si es otro", () => {
    expect(autorDe(ID_USUARIO_OTRO, ID_USUARIO_PRUEBA)).toBe("Otro usuario");
  });

  it("es Otro usuario si la sesión no tiene usuario, aunque coincida lo nulo", () => {
    expect(autorDe(ID_USUARIO_PRUEBA, null)).toBe("Otro usuario");
    expect(autorDe(null, null)).toBe("Otro usuario");
  });
});

describe("datosDeCreacion", () => {
  it("muestra horario, profesional, prestación, sillón y duración", () => {
    const registro = auditoriaCrear();

    expect(datosDeCreacion(registro.valores_nuevos, nombres)).toEqual([
      { etiqueta: "Horario", valor: "12/11/2026 10:00 a 10:45" },
      { etiqueta: "Profesional", valor: "Ficticia, Ana" },
      { etiqueta: "Prestación", valor: "Limpieza" },
      { etiqueta: "Sillón", valor: "Sillón 1" },
      { etiqueta: "Duración", valor: "45 min" },
    ]);
  });

  it("un turno sin sillón dice Sin sillón", () => {
    const valores = valoresDeAuditoria({ sillon_id: null });

    expect(
      datosDeCreacion(valores, nombres).find((d) => d.etiqueta === "Sillón")
        ?.valor,
    ).toBe("Sin sillón");
  });

  it("un recurso fuera del catálogo usa el texto genérico, sin el id", () => {
    const valores = valoresDeAuditoria({
      sillon_id: "00000000-0000-4000-8000-0000000000ee",
    });

    const sillonTexto = datosDeCreacion(valores, nombres).find(
      (d) => d.etiqueta === "Sillón",
    )?.valor;
    expect(sillonTexto).toBe("Sillón no disponible");
  });
});

describe("cambiosDeReprogramacion", () => {
  it("muestra solo el horario si solo cambió el horario", () => {
    const registro = auditoriaReprogramar();

    expect(
      cambiosDeReprogramacion(
        registro.valores_previos,
        registro.valores_nuevos,
        nombres,
      ),
    ).toEqual(["Horario: 12/11/2026 10:00 a 10:45 → 12/11/2026 11:00 a 11:45"]);
  });

  it("muestra horario y sillón cuando cambian los dos, sin profesional ni duración", () => {
    const registro = auditoriaReprogramar({
      valores_nuevos: valoresDeAuditoria({
        inicio: "2026-11-12T11:00:00-03:00",
        fin: "2026-11-12T11:45:00-03:00",
        sillon_id: ID_SILLON_2,
      }),
    });

    expect(
      cambiosDeReprogramacion(
        registro.valores_previos,
        registro.valores_nuevos,
        nombres,
      ),
    ).toEqual([
      "Horario: 12/11/2026 10:00 a 10:45 → 12/11/2026 11:00 a 11:45",
      "Sillón: Sillón 1 → Sillón 2",
    ]);
  });

  it("un sillón quitado se ve como Sin sillón", () => {
    const previos = valoresDeAuditoria();
    const nuevos = valoresDeAuditoria({ sillon_id: null });

    expect(cambiosDeReprogramacion(previos, nuevos, nombres)).toEqual([
      "Sillón: Sillón 1 → Sin sillón",
    ]);
  });

  it("muestra el cambio de profesional y de duración", () => {
    const previos = valoresDeAuditoria();
    const nuevos = valoresDeAuditoria({
      profesional_id: "00000000-0000-4000-8000-0000000000a9",
      duracion_min: 30,
    });

    expect(cambiosDeReprogramacion(previos, nuevos, nombres)).toEqual([
      "Profesional: Ficticia, Ana → Profesional no disponible",
      "Duración: 45 min → 30 min",
    ]);
  });

  it("sin diferencias no devuelve cambios", () => {
    const valores = valoresDeAuditoria();

    expect(cambiosDeReprogramacion(valores, { ...valores }, nombres)).toEqual(
      [],
    );
  });
});

describe("textoDeCancelacion", () => {
  it("muestra el motivo", () => {
    const registro = auditoriaCancelar();

    expect(textoDeCancelacion(registro.valores_nuevos)).toBe("Motivo: Viaje");
  });

  it("sin motivo dice Sin motivo", () => {
    expect(
      textoDeCancelacion(valoresDeAuditoria({ motivo_cancelacion: null })),
    ).toBe("Sin motivo");
  });
});
