import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import App from "./App";

describe("App", () => {
  it("se renderiza dentro de un router en jsdom y muestra el título de la aplicación", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: "Turnos y Agenda" }),
    ).toBeInTheDocument();
  });
});
