import {
  instalarFetchFalso,
  respuestaJson,
  respuestaVacia,
} from "./fetchFalso";
import type { FetchFalso } from "./fetchFalso";

/** Respuesta de la API falsa; `red` es una falla de red (el `fetch` rechaza). */
export type RespuestaFalsa =
  { status: number; cuerpo?: unknown } | { red: true };

export interface PedidoFalso {
  /** `"METODO /ruta"`, sin parámetros: la clave con la que se configura la respuesta. */
  clave: string;
  metodo: string;
  ruta: string;
  parametros: URLSearchParams;
  /** Cuerpo JSON enviado, o `undefined` si el pedido no tenía. */
  cuerpo: unknown;
  encabezados: Headers;
}

type Resolucion = RespuestaFalsa | ((pedido: PedidoFalso) => RespuestaFalsa);

export interface Pendiente {
  resolver: (respuesta: RespuestaFalsa) => void;
  fallarPorRed: () => void;
}

export interface ApiFalsa {
  fetch: FetchFalso;
  /** Respuesta fija (o calculada del pedido) para todos los pedidos de esa clave. */
  responder: (clave: string, resolucion: Resolucion) => void;
  /** Reserva el próximo pedido de esa clave: queda sin responder hasta que el test lo resuelva. */
  pendiente: (clave: string) => Pendiente;
  /** Pedidos hechos, en orden; con `clave`, solo los de esa clave. */
  pedidos: (clave?: string) => PedidoFalso[];
  /** Pedidos a rutas sin respuesta configurada: hacen fallar el test al terminar. */
  inesperados: () => PedidoFalso[];
  /** Para el test que provoca una ruta sin respuesta a propósito: la da por esperada. */
  reconocerInesperados: () => void;
}

// El cliente HTTP convierte la excepción del `fetch` falso en un error de red que la app puede
// tragar: por eso los pedidos sin respuesta también se anotan aquí y `setup.ts` los verifica
let pedidosInesperados: PedidoFalso[] = [];

/** Falla si algún pedido llegó a una ruta sin respuesta, y vacía la lista. Lo llama `setup.ts`. */
export function verificarPedidosInesperados(): void {
  const rutas = pedidosInesperados.map((p) => p.clave);
  pedidosInesperados = [];
  if (rutas.length > 0)
    throw new Error(
      `La app hizo pedidos a rutas sin respuesta en la API falsa: ${rutas.join(", ")}`,
    );
}

const POR_DEFECTO: Record<string, RespuestaFalsa> = {
  "GET /profesionales": { status: 200, cuerpo: [] },
  "GET /sillones": { status: 200, cuerpo: [] },
  "GET /prestaciones": { status: 200, cuerpo: [] },
  "GET /turnos": { status: 200, cuerpo: { turnos: [], bloqueos: [] } },
};

function aRespuesta(falsa: RespuestaFalsa): Response {
  if ("red" in falsa) throw new TypeError("Failed to fetch");
  return falsa.cuerpo === undefined
    ? respuestaVacia(falsa.status)
    : respuestaJson(falsa.status, falsa.cuerpo);
}

function leerCuerpo(init: RequestInit | undefined): unknown {
  const cuerpo = init?.body;
  return typeof cuerpo === "string"
    ? (JSON.parse(cuerpo) as unknown)
    : undefined;
}

/**
 * Instala un `fetch` falso que responde por `"METODO /ruta"`, sin depender del orden de los
 * pedidos (D15). Sin MSW: alcanza con enrutar, no hace falta interceptar la red.
 */
export function instalarApiFalsa(): ApiFalsa {
  const falso = instalarFetchFalso();
  const fijas = new Map<string, Resolucion>(Object.entries(POR_DEFECTO));
  const reservados = new Map<string, Array<Promise<RespuestaFalsa>>>();
  const hechos: PedidoFalso[] = [];
  pedidosInesperados = [];

  falso.mockImplementation(async (entrada, init) => {
    const url = new URL(String(entrada));
    const metodo = init?.method ?? "GET";
    const clave = `${metodo} ${url.pathname}`;
    const pedido: PedidoFalso = {
      clave,
      metodo,
      ruta: url.pathname,
      parametros: url.searchParams,
      cuerpo: leerCuerpo(init),
      encabezados: new Headers(init?.headers),
    };
    hechos.push(pedido);

    const reservado = reservados.get(clave)?.shift();
    if (reservado !== undefined) return aRespuesta(await reservado);
    const resolucion = fijas.get(clave);
    if (resolucion === undefined) {
      pedidosInesperados.push(pedido);
      throw new Error(`La API falsa no tiene respuesta para ${clave}`);
    }
    return aRespuesta(
      typeof resolucion === "function" ? resolucion(pedido) : resolucion,
    );
  });

  return {
    fetch: falso,
    responder: (clave, resolucion) => void fijas.set(clave, resolucion),
    pendiente: (clave) => {
      let resolver!: (respuesta: RespuestaFalsa) => void;
      const promesa = new Promise<RespuestaFalsa>((resuelve) => {
        resolver = resuelve;
      });
      reservados.set(clave, [...(reservados.get(clave) ?? []), promesa]);
      return {
        resolver,
        fallarPorRed: () => resolver({ red: true }),
      };
    },
    pedidos: (clave) =>
      clave === undefined
        ? [...hechos]
        : hechos.filter((p) => p.clave === clave),
    inesperados: () => [...pedidosInesperados],
    reconocerInesperados: () => {
      pedidosInesperados = [];
    },
  };
}
