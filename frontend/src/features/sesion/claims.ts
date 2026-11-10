export type Rol = "recepcionista" | "odontologo";

export interface Claims {
  rol: Rol;
  profesionalId: string | null;
  /** Vencimiento en segundos desde epoch, como en el JWT. */
  exp: number;
}

export type ResultadoToken =
  | { estado: "vigente"; claims: Claims }
  | { estado: "vencido"; claims: Claims }
  | { estado: "invalido" };

const INVALIDO: ResultadoToken = { estado: "invalido" };

function decodificarPayload(token: string): unknown {
  const tramos = token.split(".");
  const payload = tramos[1];
  if (tramos.length !== 3 || payload === undefined) return null;
  try {
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const binario = atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
    const bytes = Uint8Array.from(binario, (caracter) =>
      caracter.charCodeAt(0),
    );
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    return null;
  }
}

function esRol(valor: unknown): valor is Rol {
  return valor === "recepcionista" || valor === "odontologo";
}

/**
 * Lee los claims SIN verificar la firma: el navegador no tiene la clave de firma, y los datos
 * solo deciden qué se muestra (design D1). La forma se evalúa antes que el vencimiento.
 */
export function interpretarToken(
  token: string,
  ahoraMs: number = Date.now(),
): ResultadoToken {
  const payload = decodificarPayload(token);
  if (typeof payload !== "object" || payload === null || Array.isArray(payload))
    return INVALIDO;
  const {
    rol,
    profesional_id: profesionalId,
    exp,
  } = payload as Record<string, unknown>;
  if (!esRol(rol) || typeof exp !== "number" || !Number.isFinite(exp))
    return INVALIDO;

  const claims: Claims = {
    rol,
    profesionalId: typeof profesionalId === "string" ? profesionalId : null,
    exp,
  };
  return { estado: exp * 1000 <= ahoraMs ? "vencido" : "vigente", claims };
}
