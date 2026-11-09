import { vi, type Mock } from "vitest";

export type FetchFalso = Mock<typeof fetch>;

/** Reemplaza `fetch` (el borde con la red, D11); `unstubGlobals` lo restaura tras cada test. */
export function instalarFetchFalso(): FetchFalso {
  const falso: FetchFalso = vi.fn<typeof fetch>();
  vi.stubGlobal("fetch", falso);
  return falso;
}

export function respuestaJson(status: number, cuerpo: unknown): Response {
  return new Response(JSON.stringify(cuerpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function respuestaVacia(status: number): Response {
  return new Response(null, { status });
}

export function respuestaTexto(status: number, texto: string): Response {
  return new Response(texto, {
    status,
    headers: { "Content-Type": "text/plain" },
  });
}

/** URL y encabezados del pedido número `indice` (0 por defecto) hecho al `fetch` falso. */
export function pedidoHecho(falso: FetchFalso, indice = 0) {
  const llamada = falso.mock.calls[indice];
  if (llamada === undefined)
    throw new Error(`No hubo un pedido número ${indice}`);
  const [entrada, init] = llamada;
  return {
    url: String(entrada),
    metodo: init?.method ?? "GET",
    encabezados: new Headers(init?.headers),
    cuerpo: init?.body,
  };
}
