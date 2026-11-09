import {
  ErrorApi,
  MENSAJE_GENERICO,
  MENSAJE_SIN_CONEXION,
  MENSAJE_VALIDACION,
  type ErrorCampo,
} from "./errorApi";

const URL_BASE_POR_DEFECTO = "http://localhost:8000";

export type MetodoHttp = "GET" | "POST" | "PATCH" | "DELETE";

export interface OpcionesCliente {
  /** Por defecto, `VITE_API_URL` o `http://localhost:8000`. */
  urlBase?: string;
  obtenerToken: () => string | null;
  alNoAutenticado: (tokenDelPedido: string) => void;
}

export interface ClienteApi {
  pedir<T = unknown>(
    metodo: MetodoHttp,
    ruta: string,
    cuerpo?: unknown,
  ): Promise<T>;
}

function urlBaseDesdeEntorno(): string {
  const configurada = import.meta.env.VITE_API_URL as string | undefined;
  return configurada ?? URL_BASE_POR_DEFECTO;
}

export function crearClienteApi(opciones: OpcionesCliente): ClienteApi {
  const urlBase = (opciones.urlBase ?? urlBaseDesdeEntorno()).replace(
    /\/+$/,
    "",
  );

  return {
    async pedir<T>(
      metodo: MetodoHttp,
      ruta: string,
      cuerpo?: unknown,
    ): Promise<T> {
      const token = opciones.obtenerToken();
      const encabezados = new Headers();
      if (token !== null) encabezados.set("Authorization", `Bearer ${token}`);
      if (cuerpo !== undefined)
        encabezados.set("Content-Type", "application/json");
      let respuesta: Response;
      try {
        respuesta = await fetch(`${urlBase}${ruta}`, {
          method: metodo,
          headers: encabezados,
          body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
        });
      } catch {
        throw new ErrorApi({
          status: 0,
          codigo: null,
          mensaje: MENSAJE_SIN_CONEXION,
        });
      }
      if (!respuesta.ok) throw await interpretarError(respuesta);
      if (respuesta.status === 204) return undefined as T;
      return (await respuesta.json()) as T;
    },
  };
}

function esObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

async function interpretarError(respuesta: Response): Promise<ErrorApi> {
  const cuerpo: unknown = await respuesta.json().catch(() => null);
  const detail = esObjeto(cuerpo) ? cuerpo.detail : undefined;
  if (esObjeto(detail) && typeof detail.codigo === "string") {
    const { codigo, mensaje, ...datos } = detail;
    return new ErrorApi({
      status: respuesta.status,
      codigo,
      mensaje: typeof mensaje === "string" ? mensaje : MENSAJE_GENERICO,
      datos,
    });
  }
  if (Array.isArray(detail)) {
    return new ErrorApi({
      status: respuesta.status,
      codigo: "validacion",
      mensaje: MENSAJE_VALIDACION,
      errores: detail.map(errorDeCampo),
    });
  }
  return new ErrorApi({
    status: respuesta.status,
    codigo: null,
    mensaje: MENSAJE_GENERICO,
  });
}

/** `campo` es el último tramo de `loc` si es texto y no es el origen (`loc[0]`); si no, nulo. */
function errorDeCampo(elemento: unknown): ErrorCampo {
  const loc =
    esObjeto(elemento) && Array.isArray(elemento.loc) ? elemento.loc : [];
  const ultimo: unknown = loc.length > 1 ? loc[loc.length - 1] : undefined;
  const msg = esObjeto(elemento) ? elemento.msg : undefined;
  return {
    campo: typeof ultimo === "string" ? ultimo : null,
    mensaje: typeof msg === "string" ? msg : MENSAJE_GENERICO,
  };
}
