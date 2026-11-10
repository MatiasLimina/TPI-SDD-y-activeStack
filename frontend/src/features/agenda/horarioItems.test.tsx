import { render, screen, within } from "@testing-library/react";

import { ID_ANA, turno } from "../../test/fabricas";
import { DetalleTurno } from "./DetalleTurno";
import { GrillaAgenda } from "./GrillaAgenda";
import type { Columna } from "./grilla";
import { crearNombres } from "./nombres";
import type { VistaAgenda } from "./vistaAgenda";

const nombres = crearNombres({
  profesionales: [],
  sillones: [],
  prestaciones: [],
});

const vista: VistaAgenda = {
  vista: "dia",
  fecha: "2026-11-09",
  profesionalId: null,
  sillonId: null,
  columnas: "profesional",
  cancelados: false,
};

function columnaCon(inicio: string, fin: string): Columna {
  const t = turno({ inicio, fin });
  return {
    clave: ID_ANA,
    nombre: "Ficticia, Ana",
    carriles: 1,
    items: [
      {
        tipo: "turno",
        turno: t,
        clave: t.id,
        carril: 0,
        segmento: {
          fecha: "2026-11-09",
          desdeMin: 23 * 60 + 55,
          hastaMin: 24 * 60,
          fila: 285,
          filas: 3,
          continuaAntes: false,
          continuaDespues: false,
        },
      },
    ],
  };
}

describe("Horario de un elemento que termina a las 00:00", () => {
  it("la grilla no muestra fecha en el fin de un turno 23:55 a 00:00", () => {
    render(
      <GrillaAgenda
        columnas={[
          columnaCon("2026-11-09T23:55:00-03:00", "2026-11-10T00:00:00-03:00"),
        ]}
        vista={vista}
        nombres={nombres}
        alElegirTurno={() => undefined}
      />,
    );

    // El eje de horas también rotula 00:00: el fin del turno se busca dentro de su elemento
    const item = screen.getByRole("listitem");
    expect(within(item).getByText("23:55")).toBeInTheDocument();
    expect(within(item).getByText("00:00")).toBeInTheDocument();
    expect(within(item).queryByText(/10\/11/)).not.toBeInTheDocument();
  });

  it("la grilla sigue mostrando fechas si el turno pasa de la medianoche", () => {
    render(
      <GrillaAgenda
        columnas={[
          columnaCon("2026-11-09T23:55:00-03:00", "2026-11-10T00:05:00-03:00"),
        ]}
        vista={vista}
        nombres={nombres}
        alElegirTurno={() => undefined}
      />,
    );

    expect(screen.getByText("09/11 23:55")).toBeInTheDocument();
    expect(screen.getByText("10/11 00:05")).toBeInTheDocument();
  });

  it("el detalle muestra 09/11 23:55 – 00:00 sin fecha en el fin", () => {
    render(
      <DetalleTurno
        turno={turno({
          inicio: "2026-11-09T23:55:00-03:00",
          fin: "2026-11-10T00:00:00-03:00",
        })}
        nombres={nombres}
        puedeOperar={false}
        alCerrar={() => undefined}
        alReprogramar={() => undefined}
        alCancelar={() => undefined}
      />,
    );

    expect(screen.getByText("09/11 23:55 – 00:00")).toBeInTheDocument();
  });

  it("el detalle indica la fecha del fin si pasa de la medianoche", () => {
    render(
      <DetalleTurno
        turno={turno({
          inicio: "2026-11-09T23:55:00-03:00",
          fin: "2026-11-10T00:05:00-03:00",
        })}
        nombres={nombres}
        puedeOperar={false}
        alCerrar={() => undefined}
        alReprogramar={() => undefined}
        alCancelar={() => undefined}
      />,
    );

    expect(screen.getByText("09/11 23:55 – 10/11 00:05")).toBeInTheDocument();
  });
});
