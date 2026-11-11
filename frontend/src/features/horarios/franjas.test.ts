import { franja } from "../../test/fabricas";
import { agruparPorDia, horaCorta, textoFranja } from "./franjas";

describe("horaCorta", () => {
  it("quita los segundos sin pasar por Date", () => {
    expect(horaCorta("09:00:00")).toBe("09:00");
    expect(horaCorta("13:05:00")).toBe("13:05");
  });

  it("deja igual una hora que ya es HH:MM", () => {
    expect(horaCorta("09:00")).toBe("09:00");
  });
});

describe("textoFranja", () => {
  it("arma HH:MM a HH:MM", () => {
    expect(textoFranja(franja())).toBe("09:00 a 13:00");
  });
});

describe("agruparPorDia", () => {
  it("devuelve siempre los siete días, de Lunes a Domingo", () => {
    const dias = agruparPorDia([]);

    expect(dias.map((d) => d.nombre)).toEqual([
      "Lunes",
      "Martes",
      "Miércoles",
      "Jueves",
      "Viernes",
      "Sábado",
      "Domingo",
    ]);
    expect(dias.every((d) => d.franjas.length === 0)).toBe(true);
  });

  it("agrupa las franjas de cada día conservando el orden de la API", () => {
    const manana = franja({ id: "m", dia_semana: 0 });
    const tarde = franja({
      id: "t",
      dia_semana: 0,
      hora_inicio: "14:00:00",
      hora_fin: "18:00:00",
    });
    const viernes = franja({ id: "v", dia_semana: 4 });

    const dias = agruparPorDia([manana, tarde, viernes]);

    expect(dias[0]?.franjas.map((f) => f.id)).toEqual(["m", "t"]);
    expect(dias[4]?.franjas.map((f) => f.id)).toEqual(["v"]);
    expect(dias[1]?.franjas).toEqual([]);
  });

  it("ignora un día de la semana fuera de 0 a 6", () => {
    const dias = agruparPorDia([franja({ dia_semana: 9 })]);

    expect(dias.flatMap((d) => d.franjas)).toEqual([]);
  });
});
