import {
  AHORA_ISO,
  AHORA_SEGUNDOS,
  ID_PROFESIONAL,
  crearToken,
  tokenDeOdontologo,
  tokenDeRecepcionista,
} from "../../test/tokens";
import { interpretarToken } from "./claims";

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(AHORA_ISO);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("claims del token", () => {
  it("el reloj fijo coincide con los segundos que usan los specs", () => {
    expect(Date.now() / 1000).toBe(AHORA_SEGUNDOS);
  });

  it("lee los claims de la recepcionista, con profesional nulo", () => {
    const resultado = interpretarToken(tokenDeRecepcionista(1794229200));

    expect(resultado).toEqual({
      estado: "vigente",
      claims: { rol: "recepcionista", profesionalId: null, exp: 1794229200 },
    });
  });

  it("lee los claims del odontólogo, con su profesional", () => {
    const resultado = interpretarToken(tokenDeOdontologo(1794229200));

    expect(resultado).toEqual({
      estado: "vigente",
      claims: {
        rol: "odontologo",
        profesionalId: ID_PROFESIONAL,
        exp: 1794229200,
      },
    });
  });

  it("con exp un segundo posterior al reloj sigue vigente", () => {
    expect(
      interpretarToken(tokenDeRecepcionista(AHORA_SEGUNDOS + 1)).estado,
    ).toBe("vigente");
  });

  it.each([AHORA_SEGUNDOS, AHORA_SEGUNDOS - 60])(
    "con exp %i (menor o igual al reloj) está vencido, con sus claims",
    (exp) => {
      expect(interpretarToken(tokenDeRecepcionista(exp))).toEqual({
        estado: "vencido",
        claims: { rol: "recepcionista", profesionalId: null, exp },
      });
    },
  );

  it("decodifica base64url con '-' y '_' y texto UTF-8", () => {
    const token = crearToken({
      rol: "odontologo",
      profesional_id: "???>>>Ñandú",
      exp: AHORA_SEGUNDOS + 60,
    });
    const payload = token.split(".")[1] ?? "";

    expect(payload).toMatch(/[-_]/);
    expect(interpretarToken(token)).toMatchObject({
      estado: "vigente",
      claims: { profesionalId: "???>>>Ñandú" },
    });
  });

  it.each([
    ["texto que no es un JWT", "no-es-un-jwt"],
    ["vacío", ""],
    ["dos segmentos", "a.b"],
    ["payload que no es base64", "a.@@@.c"],
    ["payload que no es JSON", `a.${btoa("no es json")}.c`],
    ["payload JSON que no es un objeto", `a.${btoa("[1,2]")}.c`],
  ])("%s es inválido", (_caso, token) => {
    expect(interpretarToken(token)).toEqual({ estado: "invalido" });
  });

  it.each([
    ["sin exp", { rol: "recepcionista", profesional_id: null }],
    ["con exp de texto", { rol: "recepcionista", exp: "1794229200" }],
    ["con exp no finito", { rol: "recepcionista", exp: null }],
    ["con rol desconocido", { rol: "administrador", exp: AHORA_SEGUNDOS + 60 }],
    ["sin rol", { exp: AHORA_SEGUNDOS + 60 }],
    [
      "con rol desconocido y exp pasado",
      { rol: "administrador", exp: AHORA_SEGUNDOS - 60 },
    ],
    ["sin exp y con rol desconocido", { rol: "administrador" }],
  ])("un token %s es inválido, nunca vencido", (_caso, claims) => {
    expect(interpretarToken(crearToken(claims))).toEqual({
      estado: "invalido",
    });
  });
});
