import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { instalarApiFalsa, type ApiFalsa } from "../../test/apiFalsa";
import { ID_TURNO, turno } from "../../test/fabricas";
import { ProveedorSesion } from "../sesion/ProveedorSesion";
import { DialogoCancelar } from "./DialogoCancelar";

const TURNO = turno({
  inicio: "2026-11-12T10:00:00-03:00",
  fin: "2026-11-12T10:45:00-03:00",
});
const RUTA = `POST /turnos/${ID_TURNO}/cancelar`;

function montar() {
  const alCancelado = vi.fn();
  const alCerrar = vi.fn();
  const alReleerAgenda = vi.fn();
  const user = userEvent.setup();
  render(
    <ProveedorSesion>
      <DialogoCancelar
        turno={TURNO}
        alCancelado={alCancelado}
        alCerrar={alCerrar}
        alReleerAgenda={alReleerAgenda}
      />
    </ProveedorSesion>,
  );
  return { user, alCancelado, alCerrar, alReleerAgenda };
}

function apiOk(): ApiFalsa {
  const api = instalarApiFalsa();
  api.responder(RUTA, { status: 200, cuerpo: {} });
  return api;
}

function confirmar(user: ReturnType<typeof userEvent.setup>) {
  return user.click(
    screen.getByRole("button", { name: "Confirmar cancelación" }),
  );
}

describe("Diálogo de cancelación", () => {
  it("muestra paciente, día y hora del turno", () => {
    instalarApiFalsa();
    montar();

    expect(
      screen.getByRole("dialog", { name: "Cancelar turno" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Imaginaria, Carla")).toBeInTheDocument();
    expect(screen.getByText(/12\/11/)).toBeInTheDocument();
    expect(screen.getByText(/10:00/)).toBeInTheDocument();
  });

  it("Volver cierra sin hacer pedidos", async () => {
    const api = apiOk();
    const { user, alCerrar } = montar();

    await user.click(screen.getByRole("button", { name: "Volver" }));

    expect(alCerrar).toHaveBeenCalledTimes(1);
    expect(api.pedidos()).toHaveLength(0);
  });

  it("con un motivo lo envía en el cuerpo", async () => {
    const api = apiOk();
    const { user, alCancelado } = montar();
    fireEvent.change(screen.getByLabelText("Motivo"), {
      target: { value: "Viaje" },
    });

    await confirmar(user);

    expect(api.pedidos(RUTA)[0]?.cuerpo).toEqual({ motivo: "Viaje" });
    expect(alCancelado).toHaveBeenCalledTimes(1);
  });

  it("con el motivo en blanco hace el pedido sin cuerpo", async () => {
    const api = apiOk();
    const { user } = montar();
    fireEvent.change(screen.getByLabelText("Motivo"), {
      target: { value: "   " },
    });

    await confirmar(user);

    expect(api.pedidos(RUTA)).toHaveLength(1);
    expect(api.pedidos(RUTA)[0]?.cuerpo).toBeUndefined();
  });

  it("el motivo admite como máximo 255 caracteres", () => {
    instalarApiFalsa();
    montar();

    expect(screen.getByLabelText("Motivo")).toHaveAttribute("maxlength", "255");
  });

  it("turno_ya_iniciado lo explica, deshabilita el envío y relee la agenda", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, {
      status: 409,
      cuerpo: { detail: { codigo: "turno_ya_iniciado", mensaje: "técnico" } },
    });
    const { user, alReleerAgenda, alCancelado } = montar();

    await confirmar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Este turno ya inició: no se puede modificar.",
    );
    expect(
      screen.getByRole("button", { name: "Confirmar cancelación" }),
    ).toBeDisabled();
    expect(alReleerAgenda).toHaveBeenCalledTimes(1);
    expect(alCancelado).not.toHaveBeenCalled();
  });

  it("una falla de red se muestra y permite reintentar", async () => {
    const api = instalarApiFalsa();
    api.responder(RUTA, { red: true });
    const { user } = montar();

    await confirmar(user);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No se pudo conectar con el servidor.",
    );
    expect(
      screen.getByRole("button", { name: "Confirmar cancelación" }),
    ).toBeEnabled();
  });
});
