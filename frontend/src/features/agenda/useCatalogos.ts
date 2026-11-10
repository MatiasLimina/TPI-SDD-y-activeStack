import { useEffect, useState } from "react";

import { useClienteApi } from "../sesion/ProveedorSesion";
import type { Prestacion, Profesional, Sillon } from "./tipos";

export interface Catalogos {
  profesionales: Profesional[];
  sillones: Sillon[];
  prestaciones: Prestacion[];
}

/**
 * Los tres catálogos, pedidos en paralelo al montar la página, sin caché global (D7). Incluyen
 * los recursos desactivados: hay turnos históricos que los referencian.
 */
export function useCatalogos(): { catalogos: Catalogos | null } {
  const cliente = useClienteApi();
  const [catalogos, setCatalogos] = useState<Catalogos | null>(null);

  useEffect(() => {
    void Promise.all([
      cliente.pedir<Profesional[]>("GET", "/profesionales"),
      cliente.pedir<Sillon[]>("GET", "/sillones"),
      cliente.pedir<Prestacion[]>("GET", "/prestaciones"),
    ]).then(([profesionales, sillones, prestaciones]) =>
      setCatalogos({ profesionales, sillones, prestaciones }),
    );
  }, [cliente]);

  return { catalogos };
}
