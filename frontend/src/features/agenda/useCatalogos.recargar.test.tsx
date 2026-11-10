import { act, render, screen } from "@testing-library/react";
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
