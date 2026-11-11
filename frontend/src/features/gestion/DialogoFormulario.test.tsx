import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DialogoFormulario } from "./DialogoFormulario";

function montar(props: Partial<Parameters<typeof DialogoFormulario>[0]> = {}) {
  const alEnviar = vi.fn();
  const alCerrar = vi.fn();
  const user = userEvent.setup();
  const vista = render(
    <DialogoFormulario
      titulo="Nuevo sillón"
      abierto
      alCerrar={alCerrar}
      alEnviar={alEnviar}
      enviando={false}
      {...props}
    >
      <label>
        Nombre
        <input type="text" />
      </label>
    </DialogoFormulario>,
  );
  return { user, alEnviar, alCerrar, ...vista };
}

describe("DialogoFormulario", () => {
  it("es un diálogo modal con título, con un formulario sin validación del navegador", () => {
    montar();

    const dialogo = screen.getByRole("dialog", { name: "Nuevo sillón" });
    expect(dialogo.querySelector("form")).toHaveAttribute("novalidate");
    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
  });

  it("enviar llama a alEnviar sin recargar la página", async () => {
    const { user, alEnviar } = montar();

    await user.click(screen.getByRole("button", { name: "Guardar" }));

    expect(alEnviar).toHaveBeenCalledTimes(1);
  });

  it("Volver cierra sin enviar", async () => {
    const { user, alEnviar, alCerrar } = montar();

    await user.click(screen.getByRole("button", { name: "Volver" }));

    expect(alCerrar).toHaveBeenCalledTimes(1);
    expect(alEnviar).not.toHaveBeenCalled();
  });

  it("el botón de envío se deshabilita mientras se envía", async () => {
    const { user, alEnviar } = montar({ enviando: true });

    const boton = screen.getByRole("button", { name: "Guardar" });
    expect(boton).toBeDisabled();
    await user.click(boton);
    expect(alEnviar).not.toHaveBeenCalled();
  });

  it("también se deshabilita cuando el registro ya no existe", () => {
    montar({ deshabilitarEnvio: true });

    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();
  });

  it("muestra el error general con rol alert y el aviso de sin cambios con rol status", () => {
    montar({ errorGeneral: "Se superpone.", sinCambios: true });

    expect(screen.getByRole("alert")).toHaveTextContent("Se superpone.");
    expect(screen.getByRole("status")).toHaveTextContent("No hiciste cambios.");
  });

  it("sin error ni aviso no hay alertas", () => {
    montar();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("cerrado, no monta el formulario", () => {
    montar({ abierto: false });

    expect(screen.queryByLabelText("Nombre")).not.toBeInTheDocument();
  });

  it("el texto del botón de envío es configurable", () => {
    montar({ textoEnviar: "Crear" });

    expect(screen.getByRole("button", { name: "Crear" })).toBeInTheDocument();
  });
});
