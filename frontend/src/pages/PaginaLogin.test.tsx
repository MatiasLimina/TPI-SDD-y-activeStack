import { screen } from "@testing-library/react";

import { renderizarApp } from "../test/renderizarApp";
import {
  instalarFetchFalso,
  pedidoHecho,
  respuestaJson,
  type FetchFalso,
} from "../test/fetchFalso";

const CREDENCIALES_INVALIDAS = {
  detail: {
    codigo: "credenciales_invalidas",
    mensaje: "Credenciales inválidas",
  },
};

async function completarYEnviar(
  user: ReturnType<typeof renderizarApp>["user"],
  email: string,
  password: string,
) {
  await user.type(screen.getByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Contraseña"), password);
  await user.click(screen.getByRole("button", { name: "Ingresar" }));
}

function pedidosAlLogin(falso: FetchFalso): number {
  return falso.mock.calls.filter(([url]) => String(url).endsWith("/auth/login"))
    .length;
}

describe("Formulario de inicio de sesión", () => {
  it.each([
    ["recepcion@example.com", "clave-ficticia"],
    ["  Odontologa@Example.COM ", "  con espacios y Mayúsculas  "],
  ])(
    "envía un único POST /auth/login con %s sin alterar los valores",
    async (email, password) => {
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(respuestaJson(401, CREDENCIALES_INVALIDAS));
      const { user } = renderizarApp("/login");

      await completarYEnviar(user, email, password);

      await screen.findByRole("alert");
      expect(falso).toHaveBeenCalledTimes(1);
      const pedido = pedidoHecho(falso);
      expect(pedido.url).toMatch(/\/auth\/login$/);
      expect(pedido.metodo).toBe("POST");
      expect(pedido.encabezados.get("Content-Type")).toBe("application/json");
      expect(JSON.parse(String(pedido.cuerpo))).toEqual({ email, password });
    },
  );

  it("no hace ningún pedido con los campos vacíos", async () => {
    const falso = instalarFetchFalso();
    const { user } = renderizarApp("/login");

    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(falso).not.toHaveBeenCalled();
  });

  it("no hace ningún pedido si falta uno de los campos", async () => {
    const falso = instalarFetchFalso();
    const { user } = renderizarApp("/login");

    await user.type(screen.getByLabelText("Email"), "recepcion@example.com");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(falso).not.toHaveBeenCalled();
  });

  it("con un pedido en curso deshabilita el botón y no envía un segundo pedido", async () => {
    const falso = instalarFetchFalso();
    let responder: (respuesta: Response) => void = () => {};
    falso.mockReturnValue(
      new Promise<Response>((resolver) => (responder = resolver)),
    );
    const { user } = renderizarApp("/login");

    await completarYEnviar(user, "recepcion@example.com", "clave-ficticia");
    const boton = screen.getByRole("button", { name: /Ingresando|Ingresar/ });
    await user.click(boton);
    await user.keyboard("{Enter}");

    expect(boton).toBeDisabled();
    expect(pedidosAlLogin(falso)).toBe(1);
    responder(respuestaJson(401, CREDENCIALES_INVALIDAS));
    await screen.findByRole("alert");
    expect(screen.getByRole("button", { name: "Ingresar" })).toBeEnabled();
  });
});
