import { useSearchParams } from "react-router";

import { contarElementos } from "../features/agenda/grilla";
import { useAgenda } from "../features/agenda/useAgenda";
import { useCatalogos } from "../features/agenda/useCatalogos";
import { aRango, leerVista } from "../features/agenda/vistaAgenda";
import { useSesion } from "../features/sesion/ProveedorSesion";
import { hoyLocal } from "../shared/tiempo/zonaConsultorio";

const TEXTO_VACIO = "No hay turnos ni bloqueos en este período.";
const TEXTO_SOLO_CANCELADOS =
  "Solo hay turnos cancelados en este período. Activá Mostrar cancelados para verlos.";

export default function PaginaAgenda() {
  const { sesion } = useSesion();
  const [parametros] = useSearchParams();
  const rol = sesion?.claims.rol ?? "odontologo";
  const vista = leerVista(parametros, rol, hoyLocal());
  const { desde, hasta } = aRango(vista);
  const { datos } = useAgenda({
    desde,
    hasta,
    profesionalId: vista.profesionalId,
    sillonId: vista.sillonId,
  });
  const { catalogos } = useCatalogos();

  const conteo = datos === null ? null : contarElementos(datos, vista);
  return (
    <main>
      <h1>Agenda</h1>
      {(datos === null || catalogos === null) && <p>Cargando agenda…</p>}
      {conteo !== null && catalogos !== null && conteo.visibles === 0 && (
        <p>
          {conteo.canceladosOcultos > 0 ? TEXTO_SOLO_CANCELADOS : TEXTO_VACIO}
        </p>
      )}
    </main>
  );
}
