import { aParametros, aRango, leerVista } from "./vistaAgenda";

const HOY = "2026-11-09";
const ID_A = "00000000-0000-4000-8000-0000000000a1";
const ID_SILLON = "00000000-0000-4000-8000-0000000000c1";

function leer(
  consulta: string,
  rol: "recepcionista" | "odontologo" = "recepcionista",
) {
  return leerVista(new URLSearchParams(consulta), rol, HOY);
}

describe("leerVista", () => {
  it("sin parámetros es la vista diaria de hoy, sin filtros", () => {
    expect(leer("")).toEqual({
      vista: "dia",
      fecha: HOY,
      profesionalId: null,
      sillonId: null,
      columnas: "profesional",
      cancelados: false,
    });
  });

  it("lee todos los parámetros válidos", () => {
    expect(
      leer(
        `vista=dia&fecha=2026-11-12&profesional=${ID_A}&sillon=${ID_SILLON}&columnas=sillon&cancelados=1`,
      ),
    ).toEqual({
      vista: "dia",
      fecha: "2026-11-12",
      profesionalId: ID_A,
      sillonId: ID_SILLON,
      columnas: "sillon",
      cancelados: true,
    });
  });

  it("la vista semanal conserva la fecha en curso", () => {
    expect(leer("vista=semana&fecha=2026-11-12")).toMatchObject({
      vista: "semana",
      fecha: "2026-11-12",
    });
  });

  it.each([
    ["una fecha que no existe en el calendario", "fecha=2026-02-30"],
    ["una fecha con otro formato", "fecha=09-11-2026"],
    ["una fecha vacía", "fecha="],
    ["un año posterior al admitido", "fecha=9999-12-31"],
    ["un año anterior al admitido", "fecha=0999-12-31"],
    ["un año de dos cifras", "fecha=0050-01-15"],
  ])("ignora %s y usa hoy", (_caso, consulta) => {
    expect(leer(consulta).fecha).toBe(HOY);
  });

  it.each(["9998-12-31", "1000-01-01", "2028-02-29"])(
    "acepta la fecha %s",
    (fecha) => {
      expect(leer(`fecha=${fecha}`).fecha).toBe(fecha);
    },
  );

  it("ignora un 29 de febrero de un año que no es bisiesto", () => {
    expect(leer("fecha=2027-02-29").fecha).toBe(HOY);
  });

  it("ignora una vista, un filtro, un modo de columnas y un cancelados mal formados", () => {
    expect(
      leer(
        "vista=mes&profesional=no-es-un-id&sillon=123&columnas=otro&cancelados=si",
      ),
    ).toEqual({
      vista: "dia",
      fecha: HOY,
      profesionalId: null,
      sillonId: null,
      columnas: "profesional",
      cancelados: false,
    });
  });

  it("columnas se ignora en la vista semanal", () => {
    expect(leer("vista=semana&columnas=sillon").columnas).toBe("profesional");
  });

  it("para el odontólogo ignora profesional y columnas, y conserva el sillón", () => {
    expect(
      leer(
        `profesional=${ID_A}&columnas=sillon&sillon=${ID_SILLON}&cancelados=1`,
        "odontologo",
      ),
    ).toEqual({
      vista: "dia",
      fecha: HOY,
      profesionalId: null,
      sillonId: ID_SILLON,
      columnas: "profesional",
      cancelados: true,
    });
  });
});

describe("aRango", () => {
  it("la vista diaria pide un solo día", () => {
    expect(aRango({ ...leer("fecha=2026-11-12"), vista: "dia" })).toEqual({
      desde: "2026-11-12",
      hasta: "2026-11-12",
    });
  });

  it.each([
    ["jueves", "2026-11-12"],
    ["lunes", "2026-11-09"],
    ["domingo", "2026-11-15"],
  ])("la vista semanal de un %s va de lunes a domingo", (_dia, fecha) => {
    expect(aRango(leer(`vista=semana&fecha=${fecha}`))).toEqual({
      desde: "2026-11-09",
      hasta: "2026-11-15",
    });
  });

  it("una semana que cruza el año", () => {
    expect(aRango(leer("vista=semana&fecha=2026-12-29"))).toEqual({
      desde: "2026-12-28",
      hasta: "2027-01-03",
    });
  });
});

describe("aParametros", () => {
  it("escribe la vista y la fecha, y solo los filtros que hay", () => {
    expect(aParametros(leer("fecha=2026-11-12")).toString()).toBe(
      "vista=dia&fecha=2026-11-12",
    );
  });

  it("lo que se escribe se lee igual", () => {
    const vista = leer(
      `vista=dia&fecha=2026-11-12&profesional=${ID_A}&sillon=${ID_SILLON}&columnas=sillon&cancelados=1`,
    );

    expect(leer(aParametros(vista).toString())).toEqual(vista);
  });

  it("no incluye datos de pacientes ni más claves que las de la vista", () => {
    const claves = [
      ...aParametros(
        leer(`fecha=2026-11-12&profesional=${ID_A}&cancelados=1`),
      ).keys(),
    ];

    expect(claves).toEqual(["vista", "fecha", "profesional", "cancelados"]);
  });
});
