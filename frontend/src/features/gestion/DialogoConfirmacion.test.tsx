import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { DialogoConfirmacion } from "./DialogoConfirmacion";

function montar(
  props: Partial<Parameters<typeof DialogoConfirmacion>[0]> = {},
) {
  const alConfirmar = vi.fn();
  const alCerrar = vi.fn();
  const user = userEvent.setup();
  render(
    <DialogoConfirmacion
      titulo="Desactivar sillón"
      abierto
      textoConfirmar="Confirmar desactivación"
      enviando={false}
      alConfirmar={alConfirmar}
      alCerrar={alCerrar}
      {...props}
    >
      <p>
        ¿Desactivar <strong>Sillón 1</strong>? No se puede reactivar.
      </p>
    </DialogoConfirmacion>,
  );
  return { user, alConfirmar, alCerrar };
}

describe("DialogoConfirmacion", () => {
  it("muestra el título y el texto de consecuencia", () => {
    montar();

    expect(
      screen.getByRole("dialog", { name: "Desactivar sillón" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Sillón 1")).toBeInTheDocument();
    expect(screen.getByText(/No se puede reactivar/)).toBeInTheDocument();
  });

  it("confirmar llama a alConfirmar", async () => {
    const { user, alConfirmar } = montar();

    await user.click(
      screen.getByRole("button", { name: "Confirmar desactivación" }),
    );

    expect(alConfirmar).toHaveBeenCalledTimes(1);
  });

  it("Volver cierra sin confirmar", async () => {
    const { user, alConfirmar, alCerrar } = montar();

    await user.click(screen.getByRole("button", { name: "Volver" }));

    expect(alCerrar).toHaveBeenCalledTimes(1);
    expect(alConfirmar).not.toHaveBeenCalled();
  });

  it("muestra el error en el mismo diálogo con rol alert", () => {
    montar({ error: "No se pudo conectar con el servidor." });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "No se pudo conectar con el servidor.",
    );
  });

  it("deshabilita la confirmación mientras se envía y cuando el registro ya no existe", () => {
    const { user } = montar({ enviando: true });
    expect(
      screen.getByRole("button", { name: "Confirmar desactivación" }),
    ).toBeDisabled();
    void user;
  });

  it("deshabilitarConfirmacion también la bloquea", () => {
    montar({ deshabilitarConfirmacion: true });

    expect(
      screen.getByRole("button", { name: "Confirmar desactivación" }),
    ).toBeDisabled();
  });
});
