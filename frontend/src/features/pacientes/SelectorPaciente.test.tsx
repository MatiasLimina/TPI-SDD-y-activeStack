import { act, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";

import { ProveedorSesion } from "../sesion/ProveedorSesion";
import { instalarApiFalsa } from "../../test/apiFalsa";
import { AHORA_ISO } from "../../test/tokens";
import { SelectorPaciente } from "./SelectorPaciente";
import type { PacienteBusqueda } from "./tipos";

// Fake timers SIN `shouldAdvanceTime`: los bordes de 299 y 300 ms deben ser exactos
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(AHORA_ISO);
});
afterEach(() => {
  vi.useRealTimers();
});

function Contenedor() {
  const [elegido, setElegido] = useState<PacienteBusqueda | null>(null);
  return (
    <SelectorPaciente
      elegido={elegido}
      alElegir={setElegido}
      alCambiar={() => setElegido(null)}
    />
  );
}

// Con fake timers sin `shouldAdvanceTime`, el `asyncWrapper` de Testing Library (que solo
// conoce Jest) se cuelga con user-event: se escribe con `fireEvent` y se avanza el reloj a mano
function escribir(campo: HTMLElement, texto: string) {
  fireEvent.change(campo, { target: { value: texto } });
}

function montar() {
  render(
    <ProveedorSesion>
      <Contenedor />
    </ProveedorSesion>,
  );
  return { campo: screen.getByLabelText("Buscar paciente") };
}

async function pasar(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("Búsqueda de pacientes: espera y mínimo", () => {
  it("no pide a los 299 ms y hace un único pedido a los 300 ms, con q y limite", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [] });
    const { campo } = montar();

    escribir(campo, "per");
    await pasar(299);
    expect(api.pedidos("GET /pacientes")).toHaveLength(0);
    await pasar(1);

    const pedidos = api.pedidos("GET /pacientes");
    expect(pedidos).toHaveLength(1);
    expect(pedidos[0]?.parametros.get("q")).toBe("per");
    expect(pedidos[0]?.parametros.get("limite")).toBe("20");
  });

  it("seguir escribiendo reinicia la espera: un solo pedido con el texto final", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [] });
    const { campo } = montar();

    escribir(campo, "pe");
    await pasar(200);
    escribir(campo, "per");
    await pasar(299);
    expect(api.pedidos("GET /pacientes")).toHaveLength(0);
    await pasar(1);

    expect(api.pedidos("GET /pacientes")).toHaveLength(1);
    expect(api.pedidos("GET /pacientes")[0]?.parametros.get("q")).toBe("per");
  });

  it("con menos de 2 caracteres no pide y avisa", async () => {
    const api = instalarApiFalsa();
    const { campo } = montar();

    escribir(campo, " p ");
    await pasar(300);

    expect(api.pedidos("GET /pacientes")).toHaveLength(0);
    expect(
      screen.getByText("Escribí al menos 2 caracteres."),
    ).toBeInTheDocument();
  });

  it("recorta los espacios extremos antes de pedir", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [] });
    const { campo } = montar();

    escribir(campo, " pe ");
    await pasar(300);

    expect(api.pedidos("GET /pacientes")).toHaveLength(1);
    expect(api.pedidos("GET /pacientes")[0]?.parametros.get("q")).toBe("pe");
  });

  it("limita la entrada a 100 caracteres", () => {
    instalarApiFalsa();
    const { campo } = montar();

    expect(campo).toHaveAttribute("maxlength", "100");
  });

  it("codifica los caracteres especiales en la URL de la API", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [] });
    const { campo } = montar();

    escribir(campo, "Pérez & Cía");
    await pasar(300);

    const [pedido] = api.pedidos("GET /pacientes");
    expect(pedido?.parametros.get("q")).toBe("Pérez & Cía");
    const url = String(api.fetch.mock.calls[0]?.[0]);
    expect(url).toContain("%26");
    expect(url).not.toContain("Pérez & Cía");
  });
});
