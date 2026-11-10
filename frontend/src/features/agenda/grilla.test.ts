import { sumarDias } from "../../shared/tiempo/zonaConsultorio";
import {
  bloqueo,
  ID_ANA,
  ID_LUIS,
  ID_SILLON_1,
  ID_SILLON_2,
  profesional,
  sillon,
  turno,
} from "../../test/fabricas";
import {
  armarColumnas,
  asignarCarriles,
  contarElementos,
  segmentosPorDia,
} from "./grilla";
import type { VistaAgenda } from "./vistaAgenda";

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

function colocable(clave: string, desde: string, hasta: string) {
  const [segmento] = segmentosPorDia(
    {
      inicio: `2026-11-09T${desde}:00-03:00`,
      fin: `2026-11-09T${hasta}:00-03:00`,
    },
    [DIA],
  );
  return { clave, segmento: segmento! };
}

function carrilesDe(items: ReturnType<typeof colocable>[]) {
  return Object.fromEntries(
    asignarCarriles(items).items.map((i) => [i.clave, i.carril]),
  );
}

describe("asignarCarriles", () => {
  it("segmentos de 10:00-10:30, 10:15-10:45 y 10:30-11:00 usan los carriles 0, 1 y 0", () => {
    const resultado = asignarCarriles([
      colocable("a", "10:00", "10:30"),
      colocable("b", "10:15", "10:45"),
      colocable("c", "10:30", "11:00"),
    ]);

    expect(resultado.items.map((i) => i.carril)).toEqual([0, 1, 0]);
    expect(resultado.carriles).toBe(2);
  });

  it("turnos contiguos (el fin de uno es el inicio del otro) comparten carril", () => {
    expect(
      carrilesDe([
        colocable("a", "10:00", "10:30"),
        colocable("b", "10:30", "11:00"),
      ]),
    ).toEqual({ a: 0, b: 0 });
  });

  it("tres elementos de la misma hora ocupan tres carriles distintos", () => {
    const resultado = asignarCarriles([
      colocable("a", "10:00", "11:00"),
      colocable("b", "10:00", "11:00"),
      colocable("c", "10:00", "11:00"),
    ]);

    expect(new Set(resultado.items.map((i) => i.carril))).toEqual(
      new Set([0, 1, 2]),
    );
    expect(resultado.carriles).toBe(3);
  });

  it("dos bloqueos que comparten una fila redondeada usan carriles distintos", () => {
    // 10:00-10:03 y 10:03-10:05 usan ambos la fila 120 (DD-30 f)
    expect(
      carrilesDe([
        colocable("a", "10:00", "10:03"),
        colocable("b", "10:03", "10:05"),
      ]),
    ).toEqual({ a: 0, b: 1 });
  });

  it("el orden de entrada no cambia el resultado", () => {
    const a = colocable("a", "10:00", "10:30");
    const b = colocable("b", "10:15", "10:45");
    const c = colocable("c", "10:30", "11:00");
    const d = colocable("d", "10:00", "10:30");

    expect(carrilesDe([a, b, c, d])).toEqual(carrilesDe([d, c, b, a]));
    expect(carrilesDe([a, b, c, d])).toEqual(carrilesDe([c, a, d, b]));
  });

  it("sin elementos no hay carriles, y con uno hay uno", () => {
    expect(asignarCarriles([])).toEqual({ items: [], carriles: 0 });
    expect(asignarCarriles([colocable("a", "09:00", "09:30")]).carriles).toBe(
      1,
    );
  });
});

const ID_DESCONOCIDO = "00000000-0000-4000-8000-0000000000a9";

function vistaDe(cambios: Partial<VistaAgenda> = {}): VistaAgenda {
  return {
    vista: "dia",
    fecha: DIA,
    profesionalId: null,
    sillonId: null,
    columnas: "profesional",
    cancelados: false,
    ...cambios,
  };
}

const ANA = profesional();
const LUIS = profesional({
  id: ID_LUIS,
  nombre: "Luis",
  apellido: "Inventado",
});
const SILLON_1 = sillon();
const SILLON_2 = sillon({ id: ID_SILLON_2, nombre: "Sillón 2" });

interface Opciones {
  vista?: Partial<VistaAgenda>;
  turnos?: ReturnType<typeof turno>[];
  bloqueos?: ReturnType<typeof bloqueo>[];
  profesionales?: ReturnType<typeof profesional>[];
  sillones?: ReturnType<typeof sillon>[];
  rol?: "recepcionista" | "odontologo";
  profesionalPropio?: string | null;
}

function columnas(o: Opciones = {}) {
  return armarColumnas({
    vista: vistaDe(o.vista),
    rol: o.rol ?? "recepcionista",
    profesionalPropio: o.profesionalPropio ?? null,
    datos: { turnos: o.turnos ?? [], bloqueos: o.bloqueos ?? [] },
    profesionales: o.profesionales ?? [ANA, LUIS],
    sillones: o.sillones ?? [SILLON_1, SILLON_2],
  });
}

function nombres(o: Opciones = {}): string[] {
  return columnas(o).map((c) => c.nombre);
}

describe("armarColumnas: vista diaria por profesional", () => {
  it("una columna por profesional activo, sin la de un desactivado sin elementos", () => {
    const eva = profesional({
      id: ID_DESCONOCIDO,
      nombre: "Eva",
      apellido: "Ejemplar",
    });

    expect(
      nombres({ profesionales: [ANA, eva, { ...LUIS, activo: false }] }),
    ).toEqual(["Ficticia, Ana", "Ejemplar, Eva"]);
  });

  it("un profesional desactivado con un turno en el día tiene su columna", () => {
    expect(
      nombres({
        profesionales: [ANA, { ...LUIS, activo: false }],
        turnos: [turno({ profesional_id: ID_LUIS })],
      }),
    ).toEqual(["Ficticia, Ana", "Inventado, Luis"]);
  });

  it("un desactivado con solo cancelados ocultos no tiene columna, y sí con la casilla activa", () => {
    const profesionales = [ANA, { ...LUIS, activo: false }];
    const turnos = [turno({ profesional_id: ID_LUIS, estado: "cancelado" })];

    expect(nombres({ profesionales, turnos })).toEqual(["Ficticia, Ana"]);
    expect(
      nombres({ profesionales, turnos, vista: { cancelados: true } }),
    ).toEqual(["Ficticia, Ana", "Inventado, Luis"]);
  });

  it("un elemento de un profesional ausente del catálogo tiene columna con texto genérico", () => {
    expect(
      nombres({
        profesionales: [ANA],
        turnos: [turno({ profesional_id: ID_DESCONOCIDO })],
      }),
    ).toEqual(["Ficticia, Ana", "Profesional no disponible"]);
  });

  it("ubica cada turno y bloqueo en la columna de su profesional", () => {
    const resultado = columnas({
      turnos: [
        turno({ id: "t1" }),
        turno({ id: "t2", profesional_id: ID_LUIS }),
      ],
      bloqueos: [bloqueo({ id: "b1", profesional_id: ID_LUIS })],
    });

    const porColumna = resultado.map((c) =>
      c.items.map((i) => `${i.tipo}:${i.clave.split("|")[0]}`).sort(),
    );
    expect(porColumna).toEqual([["turno:t1"], ["bloqueo:b1", "turno:t2"]]);
  });
});

describe("armarColumnas: filtros", () => {
  it("el filtro de profesional deja a lo sumo su columna, aunque esté vacía", () => {
    expect(nombres({ vista: { profesionalId: ID_ANA } })).toEqual([
      "Ficticia, Ana",
    ]);
  });

  it("filtrar por un desactivado sin elementos no deja ninguna columna", () => {
    expect(
      nombres({
        profesionales: [ANA, { ...LUIS, activo: false }],
        vista: { profesionalId: ID_LUIS },
      }),
    ).toEqual([]);
  });

  it("filtrar por un desactivado con solo cancelados ocultos no deja ninguna columna", () => {
    expect(
      nombres({
        profesionales: [ANA, { ...LUIS, activo: false }],
        turnos: [turno({ profesional_id: ID_LUIS, estado: "cancelado" })],
        vista: { profesionalId: ID_LUIS },
      }),
    ).toEqual([]);
  });

  it("un id de filtro ausente del catálogo no genera una columna por sí mismo", () => {
    expect(nombres({ vista: { profesionalId: ID_DESCONOCIDO } })).toEqual([]);
  });
});

describe("armarColumnas: vista diaria por sillón", () => {
  const porSillon = { columnas: "sillon" } as const;

  it("los turnos sin sillón van en Sin sillón y los bloqueos en Bloqueos", () => {
    const resultado = columnas({
      vista: porSillon,
      sillones: [SILLON_1],
      turnos: [turno({ id: "t1" }), turno({ id: "t2", sillon_id: null })],
      bloqueos: [bloqueo()],
    });

    expect(resultado.map((c) => c.nombre)).toEqual([
      "Sillón 1",
      "Sin sillón",
      "Bloqueos",
    ]);
    expect(resultado.map((c) => c.items.length)).toEqual([1, 1, 1]);
  });

  it("sin turnos sin sillón ni bloqueos, no hay columnas especiales", () => {
    expect(
      nombres({ vista: porSillon, sillones: [SILLON_1], turnos: [turno()] }),
    ).toEqual(["Sillón 1"]);
  });

  it("un sillón desactivado sin elementos no tiene columna, y con un turno sí", () => {
    const sillones = [SILLON_1, { ...SILLON_2, activo: false }];

    expect(nombres({ vista: porSillon, sillones })).toEqual(["Sillón 1"]);
    expect(
      nombres({
        vista: porSillon,
        sillones,
        turnos: [turno({ sillon_id: ID_SILLON_2 })],
      }),
    ).toEqual(["Sillón 1", "Sillón 2"]);
  });

  it("un turno de un sillón ausente del catálogo tiene columna con texto genérico", () => {
    expect(
      nombres({
        vista: porSillon,
        sillones: [SILLON_1],
        turnos: [turno({ sillon_id: ID_DESCONOCIDO })],
      }),
    ).toEqual(["Sillón 1", "Sillón no disponible"]);
  });

  it("el filtro de profesional conserva las columnas de los sillones", () => {
    expect(nombres({ vista: { ...porSillon, profesionalId: ID_ANA } })).toEqual(
      ["Sillón 1", "Sillón 2"],
    );
  });

  it("el filtro de sillón deja ese sillón y Bloqueos si tiene elementos", () => {
    const vista = { ...porSillon, sillonId: ID_SILLON_1 };

    expect(
      nombres({ vista, turnos: [turno()], bloqueos: [bloqueo()] }),
    ).toEqual(["Sillón 1", "Bloqueos"]);
    expect(nombres({ vista })).toEqual(["Sillón 1"]);
  });
});

describe("armarColumnas: vista semanal", () => {
  const semana = { vista: "semana", fecha: "2026-11-12" } as const;

  it("siete columnas, de lunes a domingo, aunque se pida agrupar por sillón", () => {
    const resultado = nombres({ vista: { ...semana, columnas: "sillon" } });

    expect(resultado).toHaveLength(7);
    expect(resultado[0]).toBe("Lunes 09/11");
    expect(resultado[6]).toBe("Domingo 15/11");
  });

  it("tres turnos de profesionales distintos a la misma hora ocupan tres carriles", () => {
    const [lunes] = columnas({
      vista: semana,
      turnos: [
        turno({ id: "t1" }),
        turno({ id: "t2", profesional_id: ID_LUIS }),
        turno({ id: "t3", profesional_id: ID_DESCONOCIDO }),
      ],
    });

    expect(lunes!.items.map((i) => i.carril).sort()).toEqual([0, 1, 2]);
    expect(lunes!.carriles).toBe(3);
  });

  it("un turno que cruza la medianoche aparece en las columnas de los dos días", () => {
    const resultado = columnas({
      vista: semana,
      turnos: [
        turno({
          inicio: "2026-11-10T23:30:00-03:00",
          fin: "2026-11-11T00:30:00-03:00",
        }),
      ],
    });

    expect(
      resultado.filter((c) => c.items.length === 1).map((c) => c.nombre),
    ).toEqual(["Martes 10/11", "Miércoles 11/11"]);
  });

  it("un cancelado y un programado del mismo horario se ven en carriles distintos", () => {
    const [lunes] = columnas({
      vista: { ...semana, cancelados: true },
      turnos: [turno({ id: "t1" }), turno({ id: "t2", estado: "cancelado" })],
    });

    expect(lunes!.items.map((i) => i.carril).sort()).toEqual([0, 1]);
  });
});

describe("armarColumnas: odontólogo", () => {
  it("una sola columna, la de su profesional, aunque esté vacía", () => {
    expect(nombres({ rol: "odontologo", profesionalPropio: ID_ANA })).toEqual([
      "Ficticia, Ana",
    ]);
  });

  it("también si su profesional está desactivado o ausente del catálogo", () => {
    expect(
      nombres({
        rol: "odontologo",
        profesionalPropio: ID_ANA,
        profesionales: [{ ...ANA, activo: false }],
      }),
    ).toEqual(["Ficticia, Ana"]);
    expect(
      nombres({
        rol: "odontologo",
        profesionalPropio: ID_ANA,
        profesionales: [],
      }),
    ).toEqual(["Profesional no disponible"]);
  });

  it("agrupar por sillón se ignora", () => {
    expect(
      nombres({
        rol: "odontologo",
        profesionalPropio: ID_ANA,
        vista: { columnas: "sillon" },
      }),
    ).toEqual(["Ficticia, Ana"]);
  });
});

describe("contarElementos", () => {
  it("cuenta lo visible y los cancelados ocultos por separado", () => {
    const datos = {
      turnos: [turno({ id: "t1" }), turno({ id: "t2", estado: "cancelado" })],
      bloqueos: [],
    };

    expect(contarElementos(datos, vistaDe())).toEqual({
      visibles: 1,
      canceladosOcultos: 1,
    });
    expect(contarElementos(datos, vistaDe({ cancelados: true }))).toEqual({
      visibles: 2,
      canceladosOcultos: 0,
    });
  });

  it("no cuenta lo que no cae en un día visible", () => {
    const datos = {
      turnos: [
        turno({
          inicio: "2026-11-20T10:00:00-03:00",
          fin: "2026-11-20T11:00:00-03:00",
        }),
      ],
      bloqueos: [bloqueo()],
    };

    expect(contarElementos(datos, vistaDe())).toEqual({
      visibles: 1,
      canceladosOcultos: 0,
    });
  });
});
