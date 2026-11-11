import { ID_ANA } from "../../test/fabricas";
import { armarCuerpoBloqueo, enlaceAgenda, terminado } from "./bloqueos";

describe("armarCuerpoBloqueo", () => {
  it("arma inicio y fin con el desfasaje del consultorio, a cualquier minuto", () => {
    expect(
      armarCuerpoBloqueo({
        profesionalId: ID_ANA,
        fechaDesde: "2026-11-12",
        horaDesde: "10:03",
        fechaHasta: "2026-11-12",
        horaHasta: "10:07",
        motivo: " Trámite ",
      }),
    ).toEqual({
      profesional_id: ID_ANA,
      inicio: "2026-11-12T10:03:00-03:00",
      fin: "2026-11-12T10:07:00-03:00",
      motivo: "Trámite",
    });
  });

  it("sin profesional (el odontólogo) no incluye profesional_id", () => {
    const cuerpo = armarCuerpoBloqueo({
      profesionalId: null,
      fechaDesde: "2026-11-12",
      horaDesde: "10:00",
      fechaHasta: "2026-11-13",
      horaHasta: "18:00",
      motivo: "Congreso",
    });

    expect(cuerpo).toEqual({
      inicio: "2026-11-12T10:00:00-03:00",
      fin: "2026-11-13T18:00:00-03:00",
      motivo: "Congreso",
    });
    expect("profesional_id" in cuerpo).toBe(false);
  });
});

describe("terminado", () => {
  const ahora = new Date("2026-11-09T12:00:00Z"); // 09:00 en el consultorio

  it("un bloqueo que termina justo ahora ya terminó", () => {
    expect(terminado("2026-11-09T09:00:00-03:00", ahora)).toBe(true);
  });

  it("un bloqueo que termina más tarde sigue vigente", () => {
    expect(terminado("2026-11-09T09:30:00-03:00", ahora)).toBe(false);
  });

  it("un bloqueo de ayer terminó", () => {
    expect(terminado("2026-11-08T23:59:00-03:00", ahora)).toBe(true);
  });
});

describe("enlaceAgenda", () => {
  it("lleva a la vista diaria de la fecha con el profesional", () => {
    expect(enlaceAgenda("2026-11-12", ID_ANA)).toBe(
      `/agenda?fecha=2026-11-12&profesional=${ID_ANA}`,
    );
  });

  it("sin profesional no incluye el parámetro", () => {
    expect(enlaceAgenda("2026-11-12", null)).toBe("/agenda?fecha=2026-11-12");
  });
});
