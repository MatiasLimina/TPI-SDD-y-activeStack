import { crearClienteApi } from "./cliente";
import {
  instalarFetchFalso,
  pedidoHecho,
  respuestaJson,
} from "../../test/fetchFalso";

const TOKEN_A = "token-ficticio-a.payload.firma-ficticia";
const TOKEN_B = "token-ficticio-b.payload.firma-ficticia";

function clienteSinSesion() {
  return crearClienteApi({
    obtenerToken: () => null,
    alNoAutenticado: () => {},
  });
}

describe("URL base de la API", () => {
  it("usa VITE_API_URL cuando está configurada", async () => {
    vi.stubEnv("VITE_API_URL", "http://api.example.test:9000");
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(respuestaJson(200, {}));

    await clienteSinSesion().pedir("POST", "/auth/login");

    expect(pedidoHecho(falso).url).toBe(
      "http://api.example.test:9000/auth/login",
    );
  });

  it("usa http://localhost:8000 cuando VITE_API_URL no está definida", async () => {
    vi.stubEnv("VITE_API_URL", undefined);
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(respuestaJson(200, {}));

    await clienteSinSesion().pedir("POST", "/auth/login");

    expect(pedidoHecho(falso).url).toBe("http://localhost:8000/auth/login");
  });

  it.each(["http://api.example.test:9000/", "http://api.example.test:9000///"])(
    "no produce barra doble con la base %s",
    async (base) => {
      vi.stubEnv("VITE_API_URL", base);
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(respuestaJson(200, {}));

      await clienteSinSesion().pedir("POST", "/auth/login");

      expect(pedidoHecho(falso).url).toBe(
        "http://api.example.test:9000/auth/login",
      );
    },
  );
});

describe("Token en cada request", () => {
  it.each([TOKEN_A, TOKEN_B])(
    "envía Authorization: Bearer con la sesión activa (%s)",
    async (token) => {
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(respuestaJson(200, []));
      const cliente = crearClienteApi({
        obtenerToken: () => token,
        alNoAutenticado: () => {},
      });

      await cliente.pedir("GET", "/turnos");

      const pedido = pedidoHecho(falso);
      expect(pedido.encabezados.get("Authorization")).toBe(`Bearer ${token}`);
      expect(pedido.url).not.toContain(token);
    },
  );

  it("no envía el encabezado Authorization sin sesión", async () => {
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(respuestaJson(200, {}));

    await clienteSinSesion().pedir("POST", "/auth/login");

    expect(pedidoHecho(falso).encabezados.has("Authorization")).toBe(false);
  });

  it("lee el token de la sesión en cada pedido, no al crear el cliente", async () => {
    const falso = instalarFetchFalso();
    falso.mockImplementation(() => Promise.resolve(respuestaJson(200, {})));
    let token: string | null = null;
    const cliente = crearClienteApi({
      obtenerToken: () => token,
      alNoAutenticado: () => {},
    });

    await cliente.pedir("GET", "/turnos");
    token = TOKEN_A;
    await cliente.pedir("GET", "/turnos");

    expect(pedidoHecho(falso, 0).encabezados.has("Authorization")).toBe(false);
    expect(pedidoHecho(falso, 1).encabezados.get("Authorization")).toBe(
      `Bearer ${TOKEN_A}`,
    );
  });
});
