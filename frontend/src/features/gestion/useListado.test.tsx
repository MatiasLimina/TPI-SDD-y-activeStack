import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";

import { instalarApiFalsa } from "../../test/apiFalsa";
import { ProveedorSesion } from "../sesion/ProveedorSesion";
import { useListado } from "./useListado";

function envoltorio({ children }: { children: ReactNode }) {
  return <ProveedorSesion>{children}</ProveedorSesion>;
}

describe("useListado", () => {
  it("carga al montar: primero cargando, después los datos", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { status: 200, cuerpo: [{ id: "s1" }] });

    const { result } = renderHook(() => useListado<unknown[]>("/sillones"), {
      wrapper: envoltorio,
    });

    expect(result.current.cargando).toBe(true);
    expect(result.current.datos).toBeNull();
    await waitFor(() => expect(result.current.datos).toEqual([{ id: "s1" }]));
    expect(result.current.cargando).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("con ruta nula no pide nada", async () => {
    const api = instalarApiFalsa();

    const { result } = renderHook(() => useListado<unknown[]>(null), {
      wrapper: envoltorio,
    });

    expect(result.current.cargando).toBe(false);
    expect(result.current.datos).toBeNull();
    expect(api.pedidos()).toHaveLength(0);
  });

  it("un error de carga queda en error y reintentar lo repite", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { red: true });
    const { result } = renderHook(() => useListado<unknown[]>("/sillones"), {
      wrapper: envoltorio,
    });
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error?.mensaje).toBe(
      "No se pudo conectar con el servidor.",
    );
    expect(result.current.cargando).toBe(false);

    api.responder("GET /sillones", { status: 200, cuerpo: [] });
    act(() => result.current.reintentar());

    await waitFor(() => expect(result.current.datos).toEqual([]));
    expect(result.current.error).toBeNull();
    expect(api.pedidos("GET /sillones")).toHaveLength(2);
  });

  it("recargar vuelve a pedir y mantiene los datos a la vista", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { status: 200, cuerpo: [{ id: "a" }] });
    const { result } = renderHook(() => useListado<unknown[]>("/sillones"), {
      wrapper: envoltorio,
    });
    await waitFor(() => expect(result.current.datos).toEqual([{ id: "a" }]));

    const segundo = api.pendiente("GET /sillones");
    act(() => result.current.recargar());

    expect(result.current.datos).toEqual([{ id: "a" }]);
    await act(async () => {
      segundo.resolver({ status: 200, cuerpo: [{ id: "b" }] });
    });
    await waitFor(() => expect(result.current.datos).toEqual([{ id: "b" }]));
  });

  it("descarta la respuesta de un pedido viejo que llega después", async () => {
    const api = instalarApiFalsa();
    const viejo = api.pendiente("GET /cosas");
    const nuevo = api.pendiente("GET /cosas");
    const { result, rerender } = renderHook(
      ({ ruta }: { ruta: string }) => useListado<unknown[]>(ruta),
      { wrapper: envoltorio, initialProps: { ruta: "/cosas?a=1" } },
    );
    api.responder("GET /cosas", { status: 200, cuerpo: [] });

    rerender({ ruta: "/cosas?a=2" });
    await act(async () => {
      nuevo.resolver({ status: 200, cuerpo: [{ id: "B" }] });
    });
    await waitFor(() => expect(result.current.datos).toEqual([{ id: "B" }]));
    await act(async () => {
      viejo.resolver({ status: 200, cuerpo: [{ id: "A" }] });
    });

    expect(result.current.datos).toEqual([{ id: "B" }]);
  });

  it("descarta el error de un pedido viejo que llega después", async () => {
    const api = instalarApiFalsa();
    const viejo = api.pendiente("GET /cosas");
    const nuevo = api.pendiente("GET /cosas");
    const { result, rerender } = renderHook(
      ({ ruta }: { ruta: string }) => useListado<unknown[]>(ruta),
      { wrapper: envoltorio, initialProps: { ruta: "/cosas?a=1" } },
    );

    rerender({ ruta: "/cosas?a=2" });
    await act(async () => {
      nuevo.resolver({ status: 200, cuerpo: [{ id: "B" }] });
    });
    await waitFor(() => expect(result.current.datos).toEqual([{ id: "B" }]));
    await act(async () => {
      viejo.fallarPorRed();
    });

    expect(result.current.datos).toEqual([{ id: "B" }]);
    expect(result.current.error).toBeNull();
  });

  it("al cambiar de ruta no muestra los datos de la anterior", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /cosas", { status: 200, cuerpo: [{ id: "A" }] });
    const { result, rerender } = renderHook(
      ({ ruta }: { ruta: string }) => useListado<unknown[]>(ruta),
      { wrapper: envoltorio, initialProps: { ruta: "/cosas?a=1" } },
    );
    await waitFor(() => expect(result.current.datos).toEqual([{ id: "A" }]));

    api.pendiente("GET /cosas");
    rerender({ ruta: "/cosas?a=2" });

    expect(result.current.datos).toBeNull();
    expect(result.current.cargando).toBe(true);
  });
});
