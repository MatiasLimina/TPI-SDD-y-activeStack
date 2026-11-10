import { sumarDias } from "../../shared/tiempo/zonaConsultorio";
import { segmentosPorDia } from "./grilla";

function diasDeLaSemana(lunes: string): string[] {
  return Array.from({ length: 7 }, (_, i) => sumarDias(lunes, i));
}

const DIA = "2026-11-09";

function segmentos(inicio: string, fin: string, dias: string[] = [DIA]) {
  return segmentosPorDia({ inicio, fin }, dias);
}

describe("segmentosPorDia: ubicación en filas de 5 minutos", () => {
  it("un turno de 10:00 a 10:45 ocupa 9 filas desde la 120", () => {
    expect(
      segmentos("2026-11-09T10:00:00-03:00", "2026-11-09T10:45:00-03:00"),
    ).toEqual([
      {
        fecha: DIA,
        desdeMin: 600,
        hastaMin: 645,
        fila: 120,
        filas: 9,
        continuaAntes: false,
        continuaDespues: false,
      },
    ]);
  });

  it("el primer tramo del día empieza en la fila 0", () => {
    const [segmento] = segmentos(
      "2026-11-09T00:00:00-03:00",
      "2026-11-09T00:30:00-03:00",
    );

    expect(segmento).toMatchObject({ fila: 0, filas: 6 });
  });

  it("el último tramo del día ocupa solo la fila 287", () => {
    const [segmento] = segmentos(
      "2026-11-09T23:55:00-03:00",
      "2026-11-10T00:00:00-03:00",
    );

    expect(segmento).toMatchObject({ fila: 287, filas: 1 });
  });

  it("el inicio se redondea hacia abajo y el fin hacia arriba solo para ubicarlo", () => {
    const [segmento] = segmentos(
      "2026-11-09T10:03:00-03:00",
      "2026-11-09T10:07:00-03:00",
    );

    expect(segmento).toMatchObject({
      fila: 120,
      filas: 2,
      // Las horas reales no se redondean
      desdeMin: 603,
      hastaMin: 607,
    });
  });

  it("usa la hora de Buenos Aires aunque el navegador esté en Tokio", () => {
    // 22:30 en Buenos Aires: en Tokio ya sería el día 10 a las 10:30
    const [segmento] = segmentos(
      "2026-11-09T22:30:00-03:00",
      "2026-11-09T23:00:00-03:00",
    );

    expect(segmento).toMatchObject({ fecha: DIA, fila: 270, filas: 6 });
  });
});

describe("segmentosPorDia: elementos que cruzan días", () => {
  const DIAS = ["2026-11-10", "2026-11-11"];

  it("un turno que cruza la medianoche se parte en un segmento por día", () => {
    const resultado = segmentos(
      "2026-11-10T23:30:00-03:00",
      "2026-11-11T00:30:00-03:00",
      DIAS,
    );

    expect(resultado).toHaveLength(2);
    expect(resultado[0]).toMatchObject({
      fecha: "2026-11-10",
      fila: 282,
      filas: 6,
      continuaAntes: false,
      continuaDespues: true,
    });
    expect(resultado[1]).toMatchObject({
      fecha: "2026-11-11",
      fila: 0,
      filas: 6,
      continuaAntes: true,
      continuaDespues: false,
    });
  });

  it("un bloqueo de varios días ocupa todo un día intermedio", () => {
    const resultado = segmentos(
      "2026-11-09T08:00:00-03:00",
      "2026-11-13T20:00:00-03:00",
      ["2026-11-11"],
    );

    expect(resultado).toEqual([
      {
        fecha: "2026-11-11",
        desdeMin: 0,
        hastaMin: 1440,
        fila: 0,
        filas: 288,
        continuaAntes: true,
        continuaDespues: true,
      },
    ]);
  });

  it("un fin exacto a las 00:00 no genera un segmento en el día siguiente", () => {
    const resultado = segmentos(
      "2026-11-10T20:00:00-03:00",
      "2026-11-11T00:00:00-03:00",
      ["2026-11-10", "2026-11-11", "2026-11-12"],
    );

    expect(resultado).toHaveLength(1);
    expect(resultado[0]).toMatchObject({
      fecha: "2026-11-10",
      fila: 240,
      filas: 48,
      continuaDespues: false,
    });
  });

  it("un bloqueo que cruza el fin de la semana visible queda en un solo día de cada semana", () => {
    const inicio = "2026-11-15T22:00:00-03:00";
    const fin = "2026-11-16T02:00:00-03:00";
    const semana1 = diasDeLaSemana("2026-11-09");
    const semana2 = diasDeLaSemana("2026-11-16");

    const primera = segmentosPorDia({ inicio, fin }, semana1);
    const segunda = segmentosPorDia({ inicio, fin }, semana2);

    expect(primera.map((s) => s.fecha)).toEqual(["2026-11-15"]);
    expect(primera[0]).toMatchObject({
      fila: 264,
      filas: 24,
      continuaDespues: true,
    });
    expect(segunda.map((s) => s.fecha)).toEqual(["2026-11-16"]);
    expect(segunda[0]).toMatchObject({
      fila: 0,
      filas: 24,
      continuaAntes: true,
    });
  });

  it("un elemento fuera de los días visibles no tiene segmentos", () => {
    expect(
      segmentos("2026-11-20T10:00:00-03:00", "2026-11-20T11:00:00-03:00"),
    ).toEqual([]);
  });
});
