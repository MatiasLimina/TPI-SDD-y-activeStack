import { act, renderHook } from "@testing-library/react";

import { ErrorApi } from "../../shared/api/errorApi";
import { useEnvioTurno } from "./useEnvioTurno";

const ELEGIDOS = { profesional: "p", prestacion: "r", sillon: "s" };

const sillonRequerido = () =>
  new ErrorApi({
    status: 422,
    codigo: "sillon_requerido",
    mensaje: "Hace falta un sillón.",
  });

const solapamiento = () =>
  new ErrorApi({ status: 409, codigo: "solapamiento", mensaje: "Solapa." });

const fallaDeRelectura = () =>
  new ErrorApi({ status: 0, codigo: null, mensaje: "Sin conexión." });

describe("useEnvioTurno: relectura de catálogos", () => {
  it("suma la falla de la relectura al error general del envío vigente", async () => {
    const alReleerCatalogos = vi.fn(() => Promise.resolve(fallaDeRelectura()));
    const { result } = renderHook(() =>
      useEnvioTurno("crear", { alReleerAgenda: vi.fn(), alReleerCatalogos }),
    );

    await act(async () => {
      await result.current.enviar(
        () => Promise.reject(sillonRequerido()),
        ELEGIDOS,
      );
    });

    expect(result.current.generales).toContain("Sin conexión.");
  });

  it("la falla de la relectura de un envío anterior no se suma a los errores del siguiente", async () => {
    let terminarRelectura!: (falla: ErrorApi | null) => void;
    const alReleerCatalogos = vi.fn(
      () =>
        new Promise<ErrorApi | null>((resuelve) => {
          terminarRelectura = resuelve;
        }),
    );
    const { result } = renderHook(() =>
      useEnvioTurno("crear", { alReleerAgenda: vi.fn(), alReleerCatalogos }),
    );

    let primero!: Promise<boolean>;
    await act(async () => {
      primero = result.current.enviar(
        () => Promise.reject(sillonRequerido()),
        ELEGIDOS,
      );
      await Promise.resolve();
    });
    await act(async () => {
      await result.current.enviar(
        () => Promise.reject(solapamiento()),
        ELEGIDOS,
      );
    });
    const erroresDelSegundo = [...result.current.generales];

    await act(async () => {
      terminarRelectura(fallaDeRelectura());
      await primero;
    });

    expect(erroresDelSegundo).toHaveLength(1);
    expect(result.current.generales).toEqual(erroresDelSegundo);
  });
});
