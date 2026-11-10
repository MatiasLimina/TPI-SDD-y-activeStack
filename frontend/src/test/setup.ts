import "@testing-library/jest-dom/vitest";

/**
 * jsdom 31 no implementa `HTMLDialogElement.showModal` ni `close`. Los reemplazos son espías
 * (para afirmar que se abrió como modal y no solo con `open`) y reproducen lo observable:
 * abren y cierran el `<dialog>`, de modo que sea accesible por rol, y `close` avisa con el
 * evento `close`. Foco atrapado y `Esc` reales solo se verifican a mano (D6, D15).
 */
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = vi.fn(function (
    this: HTMLDialogElement,
  ) {
    if (this.hasAttribute("open"))
      throw new DOMException("El diálogo ya está abierto", "InvalidStateError");
    this.setAttribute("open", "");
  });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    if (!this.hasAttribute("open")) return;
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  });
});

afterEach(() => {
  sessionStorage.clear();
  localStorage.clear();
});
