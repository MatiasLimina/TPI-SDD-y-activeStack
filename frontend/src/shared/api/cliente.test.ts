import { crearClienteApi } from "./cliente";
import { ErrorApi } from "./errorApi";
import {
  instalarFetchFalso,
  pedidoHecho,
  respuestaJson,
  respuestaTexto,
  respuestaVacia,
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

describe("Respuesta exitosa", () => {
  it.each([{ status: "ok" }, [{ id: "00000000-0000-4000-8000-000000000001" }]])(
    "entrega el cuerpo JSON interpretado de un 200",
    async (cuerpo) => {
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(respuestaJson(200, cuerpo));

      await expect(clienteSinSesion().pedir("GET", "/health")).resolves.toEqual(
        cuerpo,
      );
    },
  );

  it("resuelve sin valor y sin error ante un 204", async () => {
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(respuestaVacia(204));

    await expect(
      clienteSinSesion().pedir("DELETE", "/bloqueos/x"),
    ).resolves.toBeUndefined();
  });

  it("envía el cuerpo como JSON con su Content-Type", async () => {
    const falso = instalarFetchFalso();
    falso.mockResolvedValue(respuestaJson(200, {}));

    await clienteSinSesion().pedir("POST", "/auth/login", {
      email: "recepcion@example.com",
    });

    const pedido = pedidoHecho(falso);
    expect(pedido.metodo).toBe("POST");
    expect(pedido.encabezados.get("Content-Type")).toBe("application/json");
    expect(pedido.cuerpo).toBe('{"email":"recepcion@example.com"}');
  });
});

describe("El token no se registra", () => {
  it.each([
    ["JSON de error", respuestaJson(500, { detail: "boom" })],
    ["texto", respuestaTexto(500, "Internal Server Error")],
  ])(
    "ninguna llamada a la consola recibe el token ante un 500 con %s",
    async (_caso, respuesta) => {
      const espias = (["log", "info", "warn", "error", "debug"] as const).map(
        (nivel) => vi.spyOn(console, nivel).mockImplementation(() => {}),
      );
      const falso = instalarFetchFalso();
      falso.mockResolvedValue(respuesta);
      const cliente = crearClienteApi({
        obtenerToken: () => TOKEN_A,
        alNoAutenticado: () => {},
      });

      await cliente.pedir("GET", "/turnos").catch(() => undefined);

      const registrado = espias
        .flatMap((espia) => espia.mock.calls.flat())
        .map(String);
      expect(registrado.some((linea) => linea.includes(TOKEN_A))).toBe(false);
    },
  );
});

const MENSAJE_GENERICO = "Ocurrió un error. Intentá de nuevo.";

/** Hace un GET que debe fallar con la respuesta dada y devuelve el error lanzado. */
async function errorDe(respuesta: Response): Promise<ErrorApi> {
  const falso = instalarFetchFalso();
  falso.mockResolvedValue(respuesta);
  const cliente = crearClienteApi({
    obtenerToken: () => null,
    alNoAutenticado: () => {},
  });
  const error = await cliente.pedir("GET", "/turnos").then(
    () => null,
    (causa: unknown) => causa,
  );
  expect(error).toBeInstanceOf(ErrorApi);
  return error as ErrorApi;
}

describe("Error de negocio de la API", () => {
  it.each([
    [403, "rol_insuficiente", "Rol insuficiente"],
    [404, "turno_inexistente", "El turno no existe"],
  ])(
    "un %i con código y mensaje conserva ambos",
    async (status, codigo, mensaje) => {
      const error = await errorDe(
        respuestaJson(status, { detail: { codigo, mensaje } }),
      );

      expect(error.status).toBe(status);
      expect(error.codigo).toBe(codigo);
      expect(error.mensaje).toBe(mensaje);
      expect(error.errores).toEqual([]);
    },
  );

  it("sin mensaje usa el genérico y conserva los campos adicionales", async () => {
    const error = await errorDe(
      respuestaJson(409, {
        detail: { codigo: "solapamiento", recursos: ["profesional", "sillon"] },
      }),
    );

    expect(error.status).toBe(409);
    expect(error.codigo).toBe("solapamiento");
    expect(error.mensaje).toBe(MENSAJE_GENERICO);
    expect(error.datos).toEqual({ recursos: ["profesional", "sillon"] });
  });

  it("con mensaje y campos adicionales conserva todo menos codigo y mensaje en datos", async () => {
    const error = await errorDe(
      respuestaJson(409, {
        detail: {
          codigo: "bloqueo_con_turnos",
          mensaje: "Hay turnos",
          turnos: ["t-1"],
        },
      }),
    );

    expect(error.mensaje).toBe("Hay turnos");
    expect(error.datos).toEqual({ turnos: ["t-1"] });
  });

  it("un 422 con objeto y mensaje es un error de negocio, sin errores por campo", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: { codigo: "rango_invalido", mensaje: "Rango inválido" },
      }),
    );

    expect(error.status).toBe(422);
    expect(error.codigo).toBe("rango_invalido");
    expect(error.mensaje).toBe("Rango inválido");
    expect(error.errores).toEqual([]);
  });

  it("un 422 con objeto y sin mensaje usa el genérico y conserva los extras", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: {
          codigo: "referencia_invalida",
          referencia: "sillon",
          motivo: "inactiva",
        },
      }),
    );

    expect(error.codigo).toBe("referencia_invalida");
    expect(error.mensaje).toBe(MENSAJE_GENERICO);
    expect(error.datos).toEqual({ referencia: "sillon", motivo: "inactiva" });
    expect(error.errores).toEqual([]);
  });
});

const MENSAJE_VALIDACION = "Revisá los datos ingresados.";

describe("Error de validación de la API", () => {
  it("un campo del body da su nombre y conserva el msg", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: [
          { type: "missing", loc: ["body", "password"], msg: "Field required" },
        ],
      }),
    );

    expect(error.status).toBe(422);
    expect(error.codigo).toBe("validacion");
    expect(error.mensaje).toBe(MENSAJE_VALIDACION);
    expect(error.errores).toEqual([
      { campo: "password", mensaje: "Field required" },
    ]);
  });

  it("un parámetro de la consulta da su nombre", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: [
          {
            type: "date_from_datetime_parsing",
            loc: ["query", "desde"],
            msg: "Input should be a valid date or datetime, input is too short",
          },
        ],
      }),
    );

    expect(error.errores).toEqual([
      {
        campo: "desde",
        mensaje: "Input should be a valid date or datetime, input is too short",
      },
    ]);
  });

  it("un campo anidado toma el último tramo de loc", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: [
          {
            type: "missing",
            loc: ["body", "paciente", "dni"],
            msg: "Field required",
          },
        ],
      }),
    );

    expect(error.errores).toEqual([
      { campo: "dni", mensaje: "Field required" },
    ]);
  });

  it("loc ['body'] da campo nulo: es un error general del formulario", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: [
          {
            type: "value_error",
            loc: ["body"],
            msg: "Value error, inicio no admite null",
          },
        ],
      }),
    );

    expect(error.codigo).toBe("validacion");
    expect(error.errores).toEqual([
      { campo: null, mensaje: "Value error, inicio no admite null" },
    ]);
  });

  it("loc ['body', 5] (posición del JSON) da campo nulo", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: [
          { type: "json_invalid", loc: ["body", 5], msg: "JSON decode error" },
        ],
      }),
    );

    expect(error.codigo).toBe("validacion");
    expect(error.errores).toEqual([
      { campo: null, mensaje: "JSON decode error" },
    ]);
  });

  it("mezcla un error general con uno de campo, una entrada por elemento", async () => {
    const error = await errorDe(
      respuestaJson(422, {
        detail: [
          { type: "value_error", loc: ["body"], msg: "Value error, rango" },
          { type: "missing", loc: ["body", "fin"], msg: "Field required" },
        ],
      }),
    );

    expect(error.errores).toEqual([
      { campo: null, mensaje: "Value error, rango" },
      { campo: "fin", mensaje: "Field required" },
    ]);
  });
});

describe("Otras fallas", () => {
  it("un detail de texto no se muestra: mensaje genérico, código nulo, status conservado", async () => {
    const error = await errorDe(respuestaJson(404, { detail: "Not Found" }));

    expect(error.status).toBe(404);
    expect(error.codigo).toBeNull();
    expect(error.mensaje).toBe(MENSAJE_GENERICO);
    expect(error.mensaje).not.toContain("Not Found");
  });

  it("un cuerpo que no es JSON no se muestra", async () => {
    const error = await errorDe(respuestaTexto(500, "Internal Server Error"));

    expect(error.status).toBe(500);
    expect(error.codigo).toBeNull();
    expect(error.mensaje).toBe(MENSAJE_GENERICO);
  });

  it("un JSON sin detail da el mensaje genérico", async () => {
    const error = await errorDe(
      respuestaJson(503, { status: "degraded", database: "unavailable" }),
    );

    expect(error.status).toBe(503);
    expect(error.codigo).toBeNull();
    expect(error.mensaje).toBe(MENSAJE_GENERICO);
  });

  it("una falla de red da status 0 y el mensaje de conexión", async () => {
    const falso = instalarFetchFalso();
    falso.mockRejectedValue(new TypeError("Failed to fetch"));
    const cliente = crearClienteApi({
      obtenerToken: () => null,
      alNoAutenticado: () => {},
    });

    const error = await cliente
      .pedir("GET", "/turnos")
      .catch((causa: unknown) => causa);

    expect(error).toBeInstanceOf(ErrorApi);
    expect(error).toMatchObject({
      status: 0,
      codigo: null,
      mensaje: "No se pudo conectar con el servidor.",
    });
  });
});
