import { render, screen } from "@testing-library/react";

// jsdom 31 no implementa showModal ni close: setup.ts los reemplaza con espías (D6, D15)
describe("reemplazo de showModal y close", () => {
  it("showModal es un espía que deja el diálogo abierto y accesible por rol", () => {
    render(
      <dialog aria-label="Prueba">
        <p>Contenido</p>
      </dialog>,
    );
    expect(screen.queryByRole("dialog", { name: "Prueba" })).toBeNull();

    const dialogo = document.querySelector("dialog")!;
    dialogo.showModal();

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("dialog", { name: "Prueba" })).toBeInTheDocument();
  });

  it("close es un espía que cierra el diálogo y avisa con el evento close", () => {
    render(<dialog aria-label="Prueba" />);
    const dialogo = document.querySelector("dialog")!;
    const alCerrar = vi.fn();
    dialogo.addEventListener("close", alCerrar);
    dialogo.showModal();

    dialogo.close();

    expect(HTMLDialogElement.prototype.close).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });

  it("abrir dos veces un diálogo modal falla, como en el navegador", () => {
    render(<dialog aria-label="Prueba" />);
    const dialogo = document.querySelector("dialog")!;
    dialogo.showModal();

    expect(() => dialogo.showModal()).toThrow(
      expect.objectContaining({ name: "InvalidStateError" }),
    );
  });

  it("los espías empiezan sin llamadas en cada test", () => {
    expect(HTMLDialogElement.prototype.showModal).not.toHaveBeenCalled();
  });
});
