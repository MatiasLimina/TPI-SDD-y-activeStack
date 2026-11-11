import { crearClienteApi } from "../shared/api/cliente";
import { instalarApiFalsa, verificarPedidosInesperados } from "./apiFalsa";

function cliente() {
  return crearClienteApi({
    urlBase: "http://api.test",
    obtenerToken: () => null,
    alNoAutenticado: () => {},
  });
}

describe("instalarApiFalsa", () => {
  it("responde por método y ruta sin importar el orden de los pedidos", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /profesionales", { status: 200, cuerpo: [{ id: "p" }] });
    api.responder("GET /sillones", { status: 200, cuerpo: [{ id: "s" }] });

    const sillones = await cliente().pedir("GET", "/sillones");
    const profesionales = await cliente().pedir("GET", "/profesionales");

    expect(sillones).toEqual([{ id: "s" }]);
    expect(profesionales).toEqual([{ id: "p" }]);
  });

  it("entrega catálogos y agenda vacíos por defecto", async () => {
    instalarApiFalsa();
    const c = cliente();

    expect(await c.pedir("GET", "/profesionales")).toEqual([]);
    expect(await c.pedir("GET", "/sillones")).toEqual([]);
    expect(await c.pedir("GET", "/prestaciones")).toEqual([]);
    expect(await c.pedir("GET", "/bloqueos")).toEqual([]);
    expect(
      await c.pedir("GET", "/turnos?desde=2026-11-09&hasta=2026-11-09"),
    ).toEqual({ turnos: [], bloqueos: [] });
  });

  it("una ruta que nadie configuró falla en voz alta en vez de inventar datos", async () => {
    const api = instalarApiFalsa();

    await expect(cliente().pedir("GET", "/pacientes?q=ab")).rejects.toThrow();
    api.reconocerInesperados();
  });

  it("registra el pedido a una ruta sin respuesta para que el test falle aunque la app lo trague", async () => {
    const api = instalarApiFalsa();

    await expect(cliente().pedir("GET", "/pacientes?q=ab")).rejects.toThrow();

    expect(api.inesperados().map((p) => p.clave)).toEqual(["GET /pacientes"]);
    expect(() => verificarPedidosInesperados()).toThrow(/GET \/pacientes/);
    // Verificar vacía la lista: el afterEach de setup.ts no vuelve a fallar
    expect(api.inesperados()).toEqual([]);
  });

  it("no cuenta como inesperado un pedido con respuesta configurada o por defecto", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });

    await cliente().pedir("GET", "/sillones");
    await cliente().pedir("POST", "/turnos", {});

    expect(api.inesperados()).toEqual([]);
    expect(() => verificarPedidosInesperados()).not.toThrow();
  });

  it("deja pedidos pendientes que el test resuelve en cualquier orden", async () => {
    const api = instalarApiFalsa();
    const primero = api.pendiente("GET /turnos");
    const segundo = api.pendiente("GET /turnos");

    const a = cliente().pedir(
      "GET",
      "/turnos?desde=2026-11-10&hasta=2026-11-10",
    );
    const b = cliente().pedir(
      "GET",
      "/turnos?desde=2026-11-11&hasta=2026-11-11",
    );
    segundo.resolver({ status: 200, cuerpo: { turnos: ["día 11"] } });
    primero.resolver({ status: 200, cuerpo: { turnos: ["día 10"] } });

    expect(await a).toEqual({ turnos: ["día 10"] });
    expect(await b).toEqual({ turnos: ["día 11"] });
  });

  it("un pendiente puede fallar por red", async () => {
    const api = instalarApiFalsa();
    const pendiente = api.pendiente("GET /turnos");

    const pedido = cliente().pedir(
      "GET",
      "/turnos?desde=2026-11-10&hasta=2026-11-10",
    );
    pendiente.fallarPorRed();

    await expect(pedido).rejects.toMatchObject({ status: 0 });
  });

  it("lista los pedidos hechos, con su ruta, parámetros y cuerpo", async () => {
    const api = instalarApiFalsa();
    api.responder("POST /turnos", { status: 201, cuerpo: {} });
    const c = cliente();

    await c.pedir("GET", "/turnos?desde=2026-11-09&hasta=2026-11-09");
    await c.pedir("POST", "/turnos", { paciente_id: "x" });

    expect(api.pedidos("POST /turnos")).toHaveLength(1);
    expect(api.pedidos("POST /turnos")[0]?.cuerpo).toEqual({
      paciente_id: "x",
    });
    expect(api.pedidos("GET /turnos")[0]?.parametros.get("desde")).toBe(
      "2026-11-09",
    );
    expect(api.pedidos().map((p) => p.clave)).toEqual([
      "GET /turnos",
      "POST /turnos",
    ]);
  });

  it("una respuesta puede calcularse a partir del pedido", async () => {
    const api = instalarApiFalsa();
    api.responder("GET /pacientes", (pedido) => ({
      status: 200,
      cuerpo: [pedido.parametros.get("q")],
    }));

    expect(await cliente().pedir("GET", "/pacientes?q=per")).toEqual(["per"]);
  });
});
