import { screen } from "@testing-library/react";

import { CLAVE_TOKEN } from "../features/sesion/almacenamiento";
import { renderizarApp } from "../test/renderizarApp";
import { usarRelojFijo } from "../test/reloj";
import {
  AHORA_SEGUNDOS,
  crearToken,
  tokenDeOdontologo,
  tokenDeRecepcionista,
} from "../test/tokens";
import {
  instalarFetchFalso,
  pedidoHecho,
  respuestaJson,
  type FetchFalso,
} from "../test/fetchFalso";

usarRelojFijo();

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

function ubicacion(): string {
  return screen.getByTestId("ubicacion").textContent ?? "";
}

describe("Redirección por rol tras el login", () => {
  it("lleva a la recepcionista a /agenda, con su rol y el enlace a la configuración", async () => {
    const token = tokenDeRecepcionista(AHORA_SEGUNDOS + 3600);
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(
      respuestaJson(200, { access_token: token, token_type: "bearer" }),
    );
    const { user } = renderizarApp("/login");

    await completarYEnviar(user, "recepcion@example.com", "clave-ficticia");

    expect(
      await screen.findByRole("heading", { name: "Agenda" }),
    ).toBeInTheDocument();
    expect(ubicacion()).toBe("/agenda");
    expect(screen.getByText("Recepcionista")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Configuración" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Email")).not.toBeInTheDocument();
  });

  it("lleva al odontólogo a /agenda, con su rol y sin enlace a la configuración", async () => {
    const token = tokenDeOdontologo(AHORA_SEGUNDOS + 3600);
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(
      respuestaJson(200, { access_token: token, token_type: "bearer" }),
    );
    const { user } = renderizarApp("/login");

    await completarYEnviar(user, "odontologa@example.com", "clave-ficticia");

    expect(
      await screen.findByRole("heading", { name: "Agenda" }),
    ).toBeInTheDocument();
    expect(ubicacion()).toBe("/agenda");
    expect(screen.getByText("Odontólogo")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Configuración" }),
    ).not.toBeInTheDocument();
  });

  it.each([tokenDeRecepcionista, tokenDeOdontologo])(
    "guarda el token en sessionStorage y deja localStorage vacío",
    async (crear) => {
      const token = crear(AHORA_SEGUNDOS + 3600);
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(
        respuestaJson(200, { access_token: token, token_type: "bearer" }),
      );
      const { user } = renderizarApp("/login");

      await completarYEnviar(user, "recepcion@example.com", "clave-ficticia");

      await screen.findByRole("heading", { name: "Agenda" });
      expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
      expect(localStorage.length).toBe(0);
    },
  );
});

const AVISO_VENCIDA = "Tu sesión venció. Iniciá sesión de nuevo.";
const ERROR_GENERICO = "Ocurrió un error. Intentá de nuevo.";

describe("Login rechazado", () => {
  it("muestra el mensaje de la API ante credenciales inválidas, sin sesión ni aviso", async () => {
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(respuestaJson(401, CREDENCIALES_INVALIDAS));
    const { user } = renderizarApp("/login");

    await completarYEnviar(user, "recepcion@example.com", "clave-equivocada");

    expect(
      await screen.findByText("Credenciales inválidas"),
    ).toBeInTheDocument();
    expect(ubicacion()).toBe("/login");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
  });

  it("sin conexión muestra el mensaje y deja reintentar", async () => {
    const falso = instalarFetchFalso();
    falso.mockRejectedValue(new TypeError("Failed to fetch"));
    const { user } = renderizarApp("/login");

    await completarYEnviar(user, "recepcion@example.com", "clave-ficticia");

    expect(
      await screen.findByText("No se pudo conectar con el servidor."),
    ).toBeInTheDocument();
    expect(ubicacion()).toBe("/login");
    expect(screen.getByRole("button", { name: "Ingresar" })).toBeEnabled();
  });

  it("un reintento exitoso limpia el error y muestra el inicio del rol", async () => {
    const token = tokenDeRecepcionista(AHORA_SEGUNDOS + 3600);
    const falso = instalarFetchFalso();
    falso.mockResolvedValueOnce(respuestaJson(401, CREDENCIALES_INVALIDAS));
    falso.mockResolvedValueOnce(
      respuestaJson(200, { access_token: token, token_type: "bearer" }),
    );
    const { user } = renderizarApp("/login");

    await completarYEnviar(user, "recepcion@example.com", "clave-equivocada");
    await screen.findByText("Credenciales inválidas");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(
      await screen.findByRole("heading", { name: "Agenda" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Credenciales inválidas"),
    ).not.toBeInTheDocument();
  });

  it.each([
    ["no es un JWT", "no-es-un-jwt"],
    [
      "tiene un rol desconocido",
      crearToken({ rol: "administrador", exp: AHORA_SEGUNDOS + 3600 }),
    ],
    [
      "no tiene exp",
      crearToken({ rol: "recepcionista", profesional_id: null }),
    ],
    ["ya está vencido", tokenDeRecepcionista(AHORA_SEGUNDOS - 60)],
    ["vence justo ahora", tokenDeRecepcionista(AHORA_SEGUNDOS)],
  ])(
    "un 200 con un token que %s muestra el error genérico, sin sesión ni aviso",
    async (_caso, token) => {
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(
        respuestaJson(200, { access_token: token, token_type: "bearer" }),
      );
      const { user } = renderizarApp("/login");

      await completarYEnviar(user, "recepcion@example.com", "clave-ficticia");

      expect(await screen.findByText(ERROR_GENERICO)).toBeInTheDocument();
      expect(ubicacion()).toBe("/login");
      expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
      expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
    },
  );
});
