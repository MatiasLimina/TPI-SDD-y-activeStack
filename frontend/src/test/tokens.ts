function base64url(texto: string): string {
  const bytes = new TextEncoder().encode(texto);
  const binario = Array.from(bytes, (byte) => String.fromCharCode(byte)).join(
    "",
  );
  return btoa(binario)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/** Token ficticio `encabezado.payload.firma-ficticia`: la firma nunca se verifica ni existe. */
export function crearToken(claims: Record<string, unknown>): string {
  const encabezado = base64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  return `${encabezado}.${base64url(JSON.stringify(claims))}.firma-ficticia`;
}

export const ID_PROFESIONAL = "00000000-0000-4000-8000-0000000000a1";
export const ID_USUARIO = "00000000-0000-4000-8000-0000000000b1";

/** Reloj fijo de los specs: 2026-11-09T12:00:00Z. */
export const AHORA_ISO = "2026-11-09T12:00:00Z";
export const AHORA_SEGUNDOS = 1794225600;

export function tokenDeRecepcionista(exp: number): string {
  return crearToken({
    sub: ID_USUARIO,
    rol: "recepcionista",
    profesional_id: null,
    exp,
  });
}

export function tokenDeOdontologo(exp: number): string {
  return crearToken({
    sub: ID_USUARIO,
    rol: "odontologo",
    profesional_id: ID_PROFESIONAL,
    exp,
  });
}
