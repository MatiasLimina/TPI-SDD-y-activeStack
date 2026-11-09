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
      const respuesta = await fetch(`${urlBase}${ruta}`, {
        method: metodo,
        headers: encabezados,
        body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
      });
      if (respuesta.status === 204) return undefined as T;
      return (await respuesta.json()) as T;
    },
  };
}
