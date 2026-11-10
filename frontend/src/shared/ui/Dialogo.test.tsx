import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";

import { Dialogo } from "./Dialogo";

function Prueba() {
  const [abierto, setAbierto] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setAbierto(true)}>
        Abrir
      </button>
      <Dialogo
        abierto={abierto}
        titulo="Nuevo turno"
        onCerrar={() => setAbierto(false)}
      >
        <p>Contenido</p>
      </Dialogo>
    </>
  );
}

describe("Dialogo", () => {
  it("se abre llamando a showModal y se nombra por su título", async () => {
    render(<Prueba />);
    expect(screen.queryByRole("dialog")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Abrir" }));

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);
    expect(
      screen.getByRole("dialog", { name: "Nuevo turno" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Contenido")).toBeInTheDocument();
  });

  it("con los eventos cancel y close queda cerrado y puede volver a abrirse", async () => {
    render(<Prueba />);
    await userEvent.click(screen.getByRole("button", { name: "Abrir" }));
    const dialogo = screen.getByRole("dialog");

    fireEvent(dialogo, new Event("cancel", { cancelable: true }));
    fireEvent(dialogo, new Event("close"));
    expect(screen.queryByRole("dialog")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Abrir" }));

    expect(screen.getByRole("dialog", { name: "Nuevo turno" })).toBeVisible();
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(2);
  });

  it("se cierra con close cuando el padre lo da por cerrado", async () => {
    function Cierra() {
      const [abierto, setAbierto] = useState(true);
      return (
        <Dialogo abierto={abierto} titulo="Cancelar turno" onCerrar={() => {}}>
          <button type="button" onClick={() => setAbierto(false)}>
            Volver
          </button>
        </Dialogo>
      );
    }
    render(<Cierra />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Volver" }));

    expect(HTMLDialogElement.prototype.close).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
