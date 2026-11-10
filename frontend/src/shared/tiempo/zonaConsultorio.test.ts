import {
  aInstanteConDesfasaje,
  diasEntre,
  etiquetaDia,
  hoyLocal,
  instanteALocal,
  lunesDeLaSemana,
  sumarDias,
} from "./zonaConsultorio";

describe("instanteALocal", () => {
  it("convierte un instante con desfasaje a fecha y hora de Buenos Aires", () => {
    expect(instanteALocal("2026-11-09T22:30:00-03:00")).toEqual({
      fecha: "2026-11-09",
      hora: "22:30",
      minutosDelDia: 22 * 60 + 30,
    });
  });

  it("muestra la medianoche como 00:00 y nunca como 24:00", () => {
    expect(instanteALocal("2026-11-09T00:00:00-03:00")).toEqual({
      fecha: "2026-11-09",
      hora: "00:00",
      minutosDelDia: 0,
    });
  });

  it("convierte un instante en Z a la hora local, pasando de día si hace falta", () => {
    expect(instanteALocal("2026-11-10T02:00:00Z")).toEqual({
      fecha: "2026-11-09",
      hora: "23:00",
      minutosDelDia: 23 * 60,
    });
    expect(instanteALocal("2026-11-10T03:00:00Z")).toEqual({
      fecha: "2026-11-10",
      hora: "00:00",
      minutosDelDia: 0,
    });
  });

  it("no depende de la zona de la máquina: el mismo instante da lo mismo en Tokio", () => {
    // La suite corre en Asia/Tokyo: la hora local del navegador sería 10:30 del día 10
    expect(new Date("2026-11-09T22:30:00-03:00").getHours()).toBe(10);
    expect(instanteALocal("2026-11-09T22:30:00-03:00").hora).toBe("22:30");
  });
});

describe("hoyLocal", () => {
  it("a las 23:00 en Buenos Aires todavía es el día anterior al de Tokio", () => {
    expect(hoyLocal(new Date("2026-11-10T02:00:00Z"))).toBe("2026-11-09");
  });

  it("a las 00:00 en Buenos Aires ya es el día siguiente", () => {
    expect(hoyLocal(new Date("2026-11-10T03:00:00Z"))).toBe("2026-11-10");
  });
});

describe("sumarDias", () => {
  it.each([
    ["2026-11-09", 1, "2026-11-10"],
    ["2026-11-30", 1, "2026-12-01"],
    ["2026-12-31", 1, "2027-01-01"],
    ["2026-03-01", -1, "2026-02-28"],
    ["2028-03-01", -1, "2028-02-29"],
    ["2026-12-21", 7, "2026-12-28"],
    ["2026-11-09", -7, "2026-11-02"],
  ])("%s %i días da %s", (fecha, dias, esperado) => {
    expect(sumarDias(fecha, dias)).toBe(esperado);
  });

  it("no depende de la zona de la máquina en el cambio de mes", () => {
    expect(sumarDias("2026-10-31", 1)).toBe("2026-11-01");
  });
});

describe("lunesDeLaSemana", () => {
  it.each([
    ["jueves", "2026-11-12", "2026-11-09"],
    ["lunes", "2026-11-09", "2026-11-09"],
    ["domingo", "2026-11-15", "2026-11-09"],
    ["domingo que cruza el año", "2027-01-03", "2026-12-28"],
  ])("el %s %s tiene el lunes %s", (_dia, fecha, lunes) => {
    expect(lunesDeLaSemana(fecha)).toBe(lunes);
  });
});

describe("etiquetaDia", () => {
  it.each([
    ["2026-11-09", "Lunes 09/11"],
    ["2026-11-12", "Jueves 12/11"],
    ["2026-11-15", "Domingo 15/11"],
  ])("%s se llama %s", (fecha, etiqueta) => {
    expect(etiquetaDia(fecha)).toBe(etiqueta);
  });
});

describe("aInstanteConDesfasaje", () => {
  it.each([
    ["2026-11-12", "10:00", "2026-11-12T10:00:00-03:00"],
    // Verano de 2008: la zona IANA tenía -02:00, que un -03:00 fijo no puede satisfacer
    ["2008-01-15", "10:00", "2008-01-15T10:00:00-02:00"],
    ["2009-03-16", "10:00", "2009-03-16T10:00:00-03:00"],
    ["2026-11-12", "23:55", "2026-11-12T23:55:00-03:00"],
    ["2026-11-12", "00:00", "2026-11-12T00:00:00-03:00"],
  ])("%s %s da %s", (fecha, hora, esperado) => {
    expect(aInstanteConDesfasaje(fecha, hora)).toBe(esperado);
  });

  it("el instante resultante vuelve a la misma fecha y hora local", () => {
    const instante = aInstanteConDesfasaje("2008-01-15", "10:00");

    expect(instanteALocal(instante)).toMatchObject({
      fecha: "2008-01-15",
      hora: "10:00",
    });
  });

  it("con un desfasaje con segundos (antes de 1920) no lanza y lo conserva", () => {
    let resultado = "";

    expect(() => {
      resultado = aInstanteConDesfasaje("1900-01-15", "10:00");
    }).not.toThrow();
    expect(resultado).toMatch(/^1900-01-15T10:00:00-\d{2}:\d{2}(:\d{2})?$/);
  });
});

describe("diasEntre", () => {
  it.each([
    ["2026-11-09", "2026-11-09", 0],
    ["2026-11-09", "2026-11-10", 1],
    ["2026-11-10", "2026-11-09", -1],
    ["2026-12-30", "2027-01-02", 3],
    ["2026-11-09", "2026-11-13", 4],
  ])("de %s a %s hay %i días", (desde, hasta, dias) => {
    expect(diasEntre(desde, hasta)).toBe(dias);
  });
});
