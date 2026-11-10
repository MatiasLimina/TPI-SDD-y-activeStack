import { act, screen } from "@testing-library/react";

import { instalarFetchFalso, respuestaJson } from "../../test/fetchFalso";
import { renderizarApp } from "../../test/renderizarApp";
import { usarRelojFijo } from "../../test/reloj";
import {
  AHORA_SEGUNDOS,
  crearToken,
  tokenDeOdontologo,
  tokenDeRecepcionista,
} from "../../test/tokens";
import { CLAVE_TOKEN } from "./almacenamiento";

usarRelojFijo();

const AVISO_VENCIDA = "Tu sesión venció. Iniciá sesión de nuevo.";

function ubicacion(): string {
  return screen.getByTestId("ubicacion").textContent ?? "";
}

describe("Arranque con un token guardado", () => {
  it.each([
    ["recepcionista", tokenDeRecepcionista(AHORA_SEGUNDOS + 60)],
    ["odontologo", tokenDeOdontologo(AHORA_SEGUNDOS + 60)],
  ])("un token vigente de %s conserva la sesión en /agenda", (_rol, token) => {
    sessionStorage.setItem(CLAVE_TOKEN, token);
    const falso = instalarFetchFalso();

    renderizarApp("/agenda");

    expect(screen.getByRole("heading", { name: "Agenda" })).toBeInTheDocument();
    expect(ubicacion()).toBe("/agenda");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
    expect(falso).not.toHaveBeenCalled();
  });

  it.each([
    ["con exp pasado", AHORA_SEGUNDOS - 60],
    ["con exp igual al reloj", AHORA_SEGUNDOS],
  ])("un token vencido (%s) se elimina y avisa en /login", (_caso, exp) => {
    sessionStorage.setItem(CLAVE_TOKEN, tokenDeRecepcionista(exp));

    renderizarApp("/agenda");

    expect(ubicacion()).toBe("/login");
    expect(screen.getByText(AVISO_VENCIDA)).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it.each([
    ["ilegible", "no-es-un-jwt"],
    [
      "de rol desconocido",
      crearToken({ rol: "administrador", exp: AHORA_SEGUNDOS + 3600 }),
    ],
    [
      "de rol desconocido y exp pasado",
      crearToken({ rol: "administrador", exp: AHORA_SEGUNDOS - 60 }),
    ],
    ["sin exp", crearToken({ rol: "recepcionista", profesional_id: null })],
  ])("un token %s se elimina sin avisar", (_caso, token) => {
    sessionStorage.setItem(CLAVE_TOKEN, token);

    renderizarApp("/agenda");

    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it("sin token guardado, /login no muestra el aviso", () => {
    renderizarApp("/agenda");

    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
  });
});

async function pasar(segundos: number): Promise<void> {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(segundos * 1000);
  });
}

function sesionDe(token: string): void {
  sessionStorage.setItem(CLAVE_TOKEN, token);
}

async function iniciarSesionConLogin(
  user: ReturnType<typeof renderizarApp>["user"],
  token: string,
) {
  const falso = instalarFetchFalso();
  falso.mockResolvedValue(
    respuestaJson(200, { access_token: token, token_type: "bearer" }),
  );
  await user.type(screen.getByLabelText("Email"), "recepcion@example.com");
  await user.type(screen.getByLabelText("Contraseña"), "clave-ficticia");
  await user.click(screen.getByRole("button", { name: "Ingresar" }));
  await screen.findByRole("heading", { name: "Agenda" });
}

describe("Temporizador de vencimiento", () => {
  it("a los 59 segundos sigue la sesión y al minuto se cierra con aviso", async () => {
    const token = tokenDeRecepcionista(AHORA_SEGUNDOS + 60);
    sesionDe(token);
    renderizarApp("/agenda");

    await pasar(59);
    expect(ubicacion()).toBe("/agenda");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);

    await pasar(1);
    expect(ubicacion()).toBe("/login");
    expect(screen.getByText(AVISO_VENCIDA)).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it("se programa tras el login", async () => {
    const { user } = renderizarApp("/login");
    await iniciarSesionConLogin(user, tokenDeOdontologo(AHORA_SEGUNDOS + 60));

    await pasar(60);

    expect(ubicacion()).toBe("/login");
    expect(screen.getByText(AVISO_VENCIDA)).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it("el cierre manual cancela el temporizador: no hay aviso al llegar el exp viejo", async () => {
    sesionDe(tokenDeRecepcionista(AHORA_SEGUNDOS + 60));
    const { user } = renderizarApp("/agenda");

    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    await pasar(60);

    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
  });

  it("una sesión nueva no hereda el temporizador de la anterior", async () => {
    sesionDe(tokenDeRecepcionista(AHORA_SEGUNDOS + 60));
    const { user } = renderizarApp("/agenda");
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    const tokenNuevo = tokenDeRecepcionista(AHORA_SEGUNDOS + 3600);
    await iniciarSesionConLogin(user, tokenNuevo);

    await pasar(60);

    expect(ubicacion()).toBe("/agenda");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(tokenNuevo);
  });

  it("con un vencimiento más lejano que 2^31 - 1 ms no se programa y la sesión sigue", async () => {
    const treintaDias = AHORA_SEGUNDOS + 30 * 24 * 3600;
    const token = tokenDeRecepcionista(treintaDias);
    sesionDe(token);
    renderizarApp("/agenda");

    await pasar(1);

    expect(ubicacion()).toBe("/agenda");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
  });

  it("el aviso desaparece al iniciar sesión y volver a cerrarla", async () => {
    sesionDe(tokenDeRecepcionista(AHORA_SEGUNDOS - 60));
    const { user } = renderizarApp("/agenda");
    expect(screen.getByText(AVISO_VENCIDA)).toBeInTheDocument();

    await iniciarSesionConLogin(
      user,
      tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
    );
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
  });
});

function errorDeApi(status: number, codigo: string, mensaje: string): Response {
  return respuestaJson(status, { detail: { codigo, mensaje } });
}

describe("Respuestas de la API en plena sesión", () => {
  it("un 401 no_autenticado a un pedido con el token vigente cierra la sesión con aviso", async () => {
    sesionDe(tokenDeRecepcionista(AHORA_SEGUNDOS + 3600));
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(
      errorDeApi(401, "no_autenticado", "No autenticado"),
    );
    const { cliente } = renderizarApp("/agenda");

    await act(() => cliente.pedir("GET", "/turnos").catch(() => undefined));

    expect(ubicacion()).toBe("/login");
    expect(screen.getByText(AVISO_VENCIDA)).toBeInTheDocument();
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBeNull();
  });

  it("un 401 con otro código no cierra la sesión", async () => {
    const token = tokenDeRecepcionista(AHORA_SEGUNDOS + 3600);
    sesionDe(token);
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(
      errorDeApi(401, "credenciales_invalidas", "Credenciales inválidas"),
    );
    const { cliente } = renderizarApp("/agenda");

    await act(() => cliente.pedir("GET", "/turnos").catch(() => undefined));

    expect(ubicacion()).toBe("/agenda");
    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
  });

  it.each([
    [
      "rol_insuficiente",
      "Rol insuficiente",
      tokenDeOdontologo(AHORA_SEGUNDOS + 3600),
    ],
    // El token dice recepcionista, pero el rol en la base cambió: la SPA no se entera
    [
      "rol_insuficiente",
      "Rol insuficiente",
      tokenDeRecepcionista(AHORA_SEGUNDOS + 3600),
    ],
    [
      "profesional_ajeno",
      "Profesional ajeno",
      tokenDeOdontologo(AHORA_SEGUNDOS + 3600),
    ],
    [
      "paciente_ajeno",
      "Paciente ajeno",
      tokenDeOdontologo(AHORA_SEGUNDOS + 3600),
    ],
  ])(
    "un 403 %s no cierra la sesión ni cambia la ruta",
    async (codigo, mensaje, token) => {
      sesionDe(token);
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(errorDeApi(403, codigo, mensaje));
      const { cliente } = renderizarApp("/agenda");

      const error = await act(() =>
        cliente.pedir("GET", "/turnos").catch((causa: unknown) => causa),
      );

      expect(error).toMatchObject({ status: 403, codigo });
      expect(ubicacion()).toBe("/agenda");
      expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(token);
    },
  );

  it("un 401 a un pedido hecho con un token anterior no cierra la sesión actual", async () => {
    sesionDe(tokenDeRecepcionista(AHORA_SEGUNDOS + 3600));
    const tokenNuevo = tokenDeOdontologo(AHORA_SEGUNDOS + 3600);
    let responderPedido: (respuesta: Response) => void = () => {};
    const falso = instalarFetchFalso();
    falso.mockImplementation((url) =>
      String(url).endsWith("/auth/login")
        ? Promise.resolve(
            respuestaJson(200, {
              access_token: tokenNuevo,
              token_type: "bearer",
            }),
          )
        : new Promise<Response>((resolver) => (responderPedido = resolver)),
    );
    const { user, cliente } = renderizarApp("/agenda");

    const pedido = cliente.pedir("GET", "/turnos").catch(() => undefined);
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    await iniciarSesionConLogin(user, tokenNuevo);
    await act(async () => {
      responderPedido(errorDeApi(401, "no_autenticado", "No autenticado"));
      await pedido;
    });

    expect(sessionStorage.getItem(CLAVE_TOKEN)).toBe(tokenNuevo);
    expect(ubicacion()).toBe("/agenda");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
  });

  it("un 401 que llega después de un cierre manual deja /login sin aviso", async () => {
    sesionDe(tokenDeRecepcionista(AHORA_SEGUNDOS + 3600));
    let responderPedido: (respuesta: Response) => void = () => {};
    const falso = instalarFetchFalso();
    falso.mockReturnValue(
      new Promise<Response>((resolver) => (responderPedido = resolver)),
    );
    const { user, cliente } = renderizarApp("/agenda");

    const pedido = cliente.pedir("GET", "/turnos").catch(() => undefined);
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));
    await act(async () => {
      responderPedido(errorDeApi(401, "no_autenticado", "No autenticado"));
      await pedido;
    });

    expect(ubicacion()).toBe("/login");
    expect(screen.queryByText(AVISO_VENCIDA)).not.toBeInTheDocument();
  });
});
