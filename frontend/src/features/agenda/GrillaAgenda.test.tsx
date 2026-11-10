import { render, screen } from "@testing-library/react";

import { ID_ANA } from "../../test/fabricas";
import { GrillaAgenda } from "./GrillaAgenda";
import type { Columna } from "./grilla";
import { crearNombres } from "./nombres";
import type { VistaAgenda } from "./vistaAgenda";

const SCROLL_A_LAS_OCHO = 96 * 6;

const nombres = crearNombres({
  profesionales: [],
  sillones: [],
  prestaciones: [],
});

function vista(cambios: Partial<VistaAgenda> = {}): VistaAgenda {
  return {
    vista: "dia",
    fecha: "2026-11-09",
    profesionalId: null,
    sillonId: null,
    columnas: "profesional",
    cancelados: false,
    ...cambios,
  };
}

function columnas(): Columna[] {
  return [{ clave: ID_ANA, nombre: "Ficticia, Ana", items: [], carriles: 1 }];
}

/** Registra cada asignación a `scrollTop` con la cantidad de columnas que había en ese momento. */
const asignaciones: Array<{ valor: number; columnas: number }> = [];

beforeEach(() => {
  asignaciones.length = 0;
  Object.defineProperty(HTMLElement.prototype, "scrollTop", {
    configurable: true,
    get: () => 0,
    set(this: HTMLElement, valor: number) {
      asignaciones.push({
        valor,
        columnas: this.querySelectorAll("section").length,
      });
    },
  });
});

afterEach(() => {
  delete (HTMLElement.prototype as { scrollTop?: number }).scrollTop;
});

function conContenido(): number {
  return asignaciones.filter(
    (a) => a.columnas > 0 && a.valor === SCROLL_A_LAS_OCHO,
  ).length;
}

function grilla(v: VistaAgenda, cols: Columna[]) {
  return (
    <GrillaAgenda
      columnas={cols}
      vista={v}
      nombres={nombres}
      alElegirTurno={() => undefined}
    />
  );
}

describe("GrillaAgenda: desplazamiento inicial a las 08:00", () => {
  it("se desplaza cuando las columnas llegan después del montaje", () => {
    const { rerender } = render(grilla(vista(), []));
    expect(conContenido()).toBe(0);

    rerender(grilla(vista(), columnas()));

    expect(conContenido()).toBe(1);
  });

  it("vuelve a desplazarse al cambiar de período y recibir columnas de nuevo", () => {
    const { rerender } = render(grilla(vista(), columnas()));
    expect(conContenido()).toBe(1);

    rerender(grilla(vista({ fecha: "2026-11-10" }), []));
    rerender(grilla(vista({ fecha: "2026-11-10" }), columnas()));

    expect(conContenido()).toBe(2);
  });

  it("vuelve a desplazarse al cambiar de vista", () => {
    const { rerender } = render(grilla(vista(), columnas()));

    rerender(grilla(vista({ vista: "semana" }), []));
    rerender(grilla(vista({ vista: "semana" }), columnas()));

    expect(conContenido()).toBe(2);
  });

  it("Actualizar (mismo período, columnas nuevas) no reinicia el desplazamiento", () => {
    const { rerender } = render(grilla(vista(), columnas()));

    rerender(grilla(vista(), columnas()));
    rerender(grilla(vista(), columnas()));

    expect(conContenido()).toBe(1);
  });
});

describe("GrillaAgenda: eje de horas", () => {
  it("muestra 24 etiquetas de 00:00 a 23:00, cada una en la fila donde empieza su hora", () => {
    const { container } = render(grilla(vista(), columnas()));

    const etiquetas = Array.from(
      container.querySelectorAll<HTMLElement>("[data-eje-hora]"),
    );
    expect(etiquetas.map((e) => e.textContent)).toEqual(
      Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`),
    );
    expect(etiquetas.map((e) => e.style.gridRow)).toEqual(
      Array.from({ length: 24 }, (_, h) => `${h * 12 + 1} / span 12`),
    );
  });

  it("queda oculto para lectores de pantalla y no cuenta como columna", () => {
    const { container } = render(grilla(vista(), columnas()));

    const eje = container.querySelector("[data-eje]");
    expect(eje).not.toBeNull();
    expect(eje).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelectorAll("section")).toHaveLength(1);
    expect(
      screen.getAllByRole("region").map((r) => r.getAttribute("aria-label")),
    ).toEqual(["Ficticia, Ana"]);
  });

  it("no aparece mientras no hay columnas", () => {
    const { container } = render(grilla(vista(), []));

    expect(container.querySelector("[data-eje]")).toBeNull();
  });
});
