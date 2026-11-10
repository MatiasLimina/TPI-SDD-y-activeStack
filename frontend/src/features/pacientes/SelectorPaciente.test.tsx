import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

const CARLA = {
  id: "00000000-0000-4000-8000-0000000000e1",
  nombre: "Carla",
  apellido: "Imaginaria",
  documento: "00000104",
  activo: true,
};

async function buscar(campo: HTMLElement, texto = "per") {
  escribir(campo, texto);
  await pasar(300);
}

describe("Resultados de la búsqueda de pacientes", () => {
  it("elegir un paciente lo muestra con la acción Cambiar paciente", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [CARLA] });
    const { campo } = montar();
    await buscar(campo);

    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(screen.getByText("00000104")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Imaginaria, Carla/ }));

    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Cambiar paciente" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Buscar paciente")).not.toBeInTheDocument();
  });

  it("Cambiar paciente vuelve a la búsqueda", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [CARLA] });
    const { campo } = montar();
    await buscar(campo);
    fireEvent.click(screen.getByRole("button", { name: /Imaginaria, Carla/ }));

    fireEvent.click(screen.getByRole("button", { name: "Cambiar paciente" }));

    expect(screen.getByLabelText("Buscar paciente")).toBeInTheDocument();
  });

  it("tras elegir un paciente con Enter, el foco pasa a Cambiar paciente y no se pierde en el body", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [CARLA] });
    const { campo } = montar();
    await buscar(campo);
    const resultado = screen.getByRole("button", { name: /Imaginaria, Carla/ });
    resultado.focus();

    fireEvent.click(resultado);

    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Cambiar paciente" }),
    );
  });

  it("tras Cambiar paciente, el foco pasa al campo de búsqueda", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [CARLA] });
    const { campo } = montar();
    await buscar(campo);
    fireEvent.click(screen.getByRole("button", { name: /Imaginaria, Carla/ }));

    fireEvent.click(screen.getByRole("button", { name: "Cambiar paciente" }));

    expect(document.activeElement).toBe(
      screen.getByLabelText("Buscar paciente"),
    );
  });

  it("al montar el selector no roba el foco", () => {
    instalarApiFalsa();
    const { campo } = montar();

    expect(document.activeElement).not.toBe(campo);
  });

  it("un paciente inactivo se ve identificado y no se puede elegir", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", {
      status: 200,
      cuerpo: [{ ...CARLA, activo: false }],
    });
    const { campo } = montar();
    await buscar(campo);

    expect(screen.getByText("Inactivo")).toBeInTheDocument();
    const boton = screen.getByRole("button", { name: /Imaginaria, Carla/ });
    expect(boton).toBeDisabled();
    fireEvent.click(boton);
    expect(
      screen.queryByRole("button", { name: "Cambiar paciente" }),
    ).not.toBeInTheDocument();
  });

  it("muestra los resultados en el orden de la API", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", {
      status: 200,
      cuerpo: [
        { ...CARLA, id: "a", apellido: "Zeta", nombre: "Uno" },
        { ...CARLA, id: "b", apellido: "Alfa", nombre: "Dos" },
      ],
    });
    const { campo } = montar();
    await buscar(campo);

    const nombres = screen.getAllByRole("button").map((b) => b.textContent);
    expect(nombres[0]).toContain("Zeta, Uno");
    expect(nombres[1]).toContain("Alfa, Dos");
  });

  it("sin resultados lo informa", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [] });
    const { campo } = montar();
    await buscar(campo);

    expect(
      screen.getByText("No se encontraron pacientes."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Hay más resultados: refiná la búsqueda."),
    ).not.toBeInTheDocument();
  });

  it("con 20 resultados sugiere refinar la búsqueda, y con 19 no", async () => {
    const api = instalarApiFalsa();
    const lista = (n: number) =>
      Array.from({ length: n }, (_, i) => ({
        ...CARLA,
        id: `id-${i}`,
        documento: `${i}`,
      }));
    api.responder("GET /pacientes", { status: 200, cuerpo: lista(19) });
    const { campo } = montar();
    await buscar(campo, "per");
    expect(
      screen.queryByText("Hay más resultados: refiná la búsqueda."),
    ).not.toBeInTheDocument();

    api.responder("GET /pacientes", { status: 200, cuerpo: lista(20) });
    await buscar(campo, "pere");

    expect(
      screen.getByText("Hay más resultados: refiná la búsqueda."),
    ).toBeInTheDocument();
  });

  it("solo se muestra la respuesta de la última búsqueda", async () => {
    const api = instalarApiFalsa();
    const primera = api.pendiente("GET /pacientes");
    api.responder("GET /pacientes", {
      status: 200,
      cuerpo: [{ ...CARLA, nombre: "Pere", apellido: "Segunda" }],
    });
    const { campo } = montar();
    await buscar(campo, "per");
    await buscar(campo, "pere");
    expect(screen.getByText("Segunda, Pere")).toBeInTheDocument();

    await act(async () => {
      primera.resolver({ status: 200, cuerpo: [CARLA] });
    });

    expect(screen.getByText("Segunda, Pere")).toBeInTheDocument();
    expect(screen.queryByText("Imaginaria, Carla")).not.toBeInTheDocument();
  });

  it("no muestra resultados de un texto anterior mientras se espera el nuevo", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [CARLA] });
    const { campo } = montar();
    await buscar(campo, "per");
    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();

    escribir(campo, "pere");

    expect(screen.queryByText("Imaginaria, Carla")).not.toBeInTheDocument();
  });

  it("un error de red se muestra con su mensaje", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { red: true });
    const { campo } = montar();
    await buscar(campo);

    expect(
      screen.getByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Buscar paciente")).toHaveValue("per");
  });
});

describe("Selector de paciente con teclado", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  function montarEnFormulario(alEnviar: () => void) {
    const user = userEvent.setup();
    render(
      <ProveedorSesion>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            alEnviar();
          }}
        >
          <Contenedor />
          <button type="submit">Guardar</button>
        </form>
      </ProveedorSesion>,
    );
    return user;
  }

  it("con Tab se llega a un resultado y Enter lo elige, sin enviar el formulario", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [CARLA] });
    const alEnviar = vi.fn();
    const user = montarEnFormulario(alEnviar);
    await user.type(screen.getByLabelText("Buscar paciente"), "per");
    const resultado = await screen.findByRole("button", {
      name: /Imaginaria, Carla/,
    });

    await user.tab();
    expect(resultado).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(
      await screen.findByRole("button", { name: "Cambiar paciente" }),
    ).toBeInTheDocument();
    expect(alEnviar).not.toHaveBeenCalled();
  });

  it("Enter en el campo de búsqueda no envía el formulario", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", { status: 200, cuerpo: [] });
    const alEnviar = vi.fn();
    const user = montarEnFormulario(alEnviar);

    await user.type(screen.getByLabelText("Buscar paciente"), "per{Enter}");

    expect(alEnviar).not.toHaveBeenCalled();
  });
});
