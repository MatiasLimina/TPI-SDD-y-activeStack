import { act, render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";

import { instalarApiFalsa } from "../../test/apiFalsa";
import { profesional, sillon } from "../../test/fabricas";
import type { ErrorApi } from "../../shared/api/errorApi";
import { ProveedorSesion } from "../sesion/ProveedorSesion";
import { useCatalogos } from "./useCatalogos";

function Sonda({
  alObtener,
}: {
  alObtener: (recargar: () => Promise<ErrorApi | null>) => void;
}) {
  const { catalogos, recargar } = useCatalogos();
  useEffect(() => alObtener(recargar), [alObtener, recargar]);
  return (
    <output data-testid="sillones">
      {catalogos === null
        ? "sin datos"
        : catalogos.sillones.map((s) => s.nombre).join(",")}
    </output>
  );
}

let recargarActual: () => Promise<ErrorApi | null> = () =>
  Promise.resolve(null);
const obtener = (recargar: () => Promise<ErrorApi | null>) => {
  recargarActual = recargar;
};

function montar() {
  render(
    <ProveedorSesion>
      <Sonda alObtener={obtener} />
    </ProveedorSesion>,
  );
}

describe("useCatalogos: recargar", () => {
  it("vuelve a pedir los tres catálogos, actualiza los datos y devuelve null", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /sillones", { status: 200, cuerpo: [sillon()] });
    montar();
    await screen.findByText("Sillón 1");
    api.responder("GET /sillones", {
      status: 200,
      cuerpo: [sillon({ nombre: "Sillón 9" })],
    });

    let resultado: ErrorApi | null = null;
    await act(async () => {
      resultado = await recargarActual();
    });

    expect(resultado).toBeNull();
    expect(screen.getByTestId("sillones")).toHaveTextContent("Sillón 9");
    expect(api.pedidos("GET /profesionales")).toHaveLength(2);
    expect(api.pedidos("GET /prestaciones")).toHaveLength(2);
  });

  it("si falla devuelve el error y conserva los catálogos anteriores", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /profesionales", {
      status: 200,
      cuerpo: [profesional()],
    });
    api.responder("GET /sillones", { status: 200, cuerpo: [sillon()] });
    montar();
    await screen.findByText("Sillón 1");
    api.responder("GET /sillones", { red: true });

    let resultado: ErrorApi | null = null;
    await act(async () => {
      resultado = await recargarActual();
    });

    expect(resultado).toMatchObject({ status: 0 });
    expect(screen.getByTestId("sillones")).toHaveTextContent("Sillón 1");
  });
});

describe("useCatalogos: orden de las cargas", () => {
  it("una carga inicial lenta no pisa el resultado de una recarga posterior", async () => {
    const api = instalarApiFalsa();
    const inicial = api.pendiente("GET /sillones");
    montar();
    api.responder("GET /sillones", {
      status: 200,
      cuerpo: [sillon({ nombre: "Sillón 9" })],
    });

    await act(async () => {
      await recargarActual();
    });
    expect(screen.getByTestId("sillones")).toHaveTextContent("Sillón 9");

    await act(async () => {
      inicial.resolver({ status: 200, cuerpo: [sillon()] });
      await Promise.resolve();
    });

    await waitFor(() =>
      expect(screen.getByTestId("sillones")).toHaveTextContent("Sillón 9"),
    );
    expect(screen.getByTestId("sillones")).not.toHaveTextContent("Sillón 1");
  });

  it("una recarga vieja que termina tarde no pisa a la nueva y no informa su resultado", async () => {
    const api = instalarApiFalsa();
    montar();
    await waitFor(() =>
      expect(screen.getByTestId("sillones")).not.toHaveTextContent("sin datos"),
    );
    const vieja = api.pendiente("GET /sillones");
    let resultadoViejo: ErrorApi | null | undefined;
    const recargaVieja = recargarActual().then((r) => {
      resultadoViejo = r;
    });
    api.responder("GET /sillones", {
      status: 200,
      cuerpo: [sillon({ nombre: "Sillón 9" })],
    });
    await act(async () => {
      await recargarActual();
    });

    await act(async () => {
      vieja.resolver({ status: 200, cuerpo: [sillon()] });
      await recargaVieja;
    });

    expect(resultadoViejo).toBeNull();
    expect(screen.getByTestId("sillones")).toHaveTextContent("Sillón 9");
  });

  it("la falla de una recarga vieja no se informa si ya hay una más nueva", async () => {
    const api = instalarApiFalsa();
    montar();
    await waitFor(() =>
      expect(screen.getByTestId("sillones")).not.toHaveTextContent("sin datos"),
    );
    const vieja = api.pendiente("GET /sillones");
    let resultadoViejo: ErrorApi | null | undefined;
    const recargaVieja = recargarActual().then((r) => {
      resultadoViejo = r;
    });
    await act(async () => {
      await recargarActual();
    });

    await act(async () => {
      vieja.fallarPorRed();
      await recargaVieja;
    });

    expect(resultadoViejo).toBeNull();
  });
});
