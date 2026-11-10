import { sumarDias } from "../../shared/tiempo/zonaConsultorio";
import type { Rol } from "../sesion/claims";
import {
  nombreProfesional,
  PROFESIONAL_NO_DISPONIBLE,
  SILLON_NO_DISPONIBLE,
} from "./grilla";
import type { Catalogos } from "./useCatalogos";
import type { VistaAgenda } from "./vistaAgenda";

interface PropsBarra {
  vista: VistaAgenda;
  rol: Rol;
  /** Sin catálogos todavía, los filtros no ofrecen opciones. */
  catalogos: Catalogos | null;
  /** Día actual del consultorio, para el botón `Hoy`. */
  hoy: string;
  /** Cada cambio es una navegación nueva (D6). */
  alCambiar: (vista: VistaAgenda) => void;
  alActualizar: () => void;
}

/** Controles de vista y de navegación de la agenda. */
export function BarraAgenda({
  vista,
  rol,
  catalogos,
  hoy,
  alCambiar,
  alActualizar,
}: PropsBarra) {
  const salto = vista.vista === "dia" ? 1 : 7;
  const irA = (fecha: string) => alCambiar({ ...vista, fecha });
  return (
    <div>
      <div role="group" aria-label="Vista">
        <button
          type="button"
          aria-pressed={vista.vista === "dia"}
          onClick={() => alCambiar({ ...vista, vista: "dia" })}
        >
          Día
        </button>
        <button
          type="button"
          aria-pressed={vista.vista === "semana"}
          onClick={() => alCambiar({ ...vista, vista: "semana" })}
        >
          Semana
        </button>
      </div>
      <div role="group" aria-label="Período">
        <button
          type="button"
          onClick={() => irA(sumarDias(vista.fecha, -salto))}
        >
          Período anterior
        </button>
        <button type="button" onClick={() => irA(hoy)}>
          Hoy
        </button>
        <button
          type="button"
          onClick={() => irA(sumarDias(vista.fecha, salto))}
        >
          Período siguiente
        </button>
      </div>
      <Filtros
        vista={vista}
        rol={rol}
        catalogos={catalogos}
        alCambiar={alCambiar}
      />
      <button type="button" onClick={alActualizar}>
        Actualizar
      </button>
    </div>
  );
}

interface Recurso {
  id: string;
  activo: boolean;
}

/**
 * Opciones de un filtro: todos los recursos, incluidos los desactivados, que conservan su
 * agenda (DD-32 l); un id bien formado que no figura en el catálogo se ofrece con texto genérico.
 */
function opciones<R extends Recurso>(
  catalogo: R[],
  seleccionado: string | null,
  nombreDe: (recurso: R) => string,
  nombreAusente: string,
) {
  const ausente =
    seleccionado !== null && !catalogo.some((r) => r.id === seleccionado);
  return (
    <>
      {catalogo.map((recurso) => (
        <option key={recurso.id} value={recurso.id}>
          {recurso.activo
            ? nombreDe(recurso)
            : `${nombreDe(recurso)} (inactivo)`}
        </option>
      ))}
      {ausente && <option value={seleccionado}>{nombreAusente}</option>}
    </>
  );
}

function Filtros({
  vista,
  rol,
  catalogos,
  alCambiar,
}: Pick<PropsBarra, "vista" | "rol" | "catalogos" | "alCambiar">) {
  const esRecepcionista = rol === "recepcionista";
  return (
    <div>
      {esRecepcionista && (
        <label>
          Profesional
          <select
            value={vista.profesionalId ?? ""}
            onChange={(e) =>
              alCambiar({ ...vista, profesionalId: e.target.value || null })
            }
          >
            <option value="">Todos los profesionales</option>
            {catalogos !== null &&
              opciones(
                catalogos.profesionales,
                vista.profesionalId,
                nombreProfesional,
                PROFESIONAL_NO_DISPONIBLE,
              )}
          </select>
        </label>
      )}
      <label>
        Sillón
        <select
          value={vista.sillonId ?? ""}
          onChange={(e) =>
            alCambiar({ ...vista, sillonId: e.target.value || null })
          }
        >
          <option value="">Todos los sillones</option>
          {catalogos !== null &&
            opciones(
              catalogos.sillones,
              vista.sillonId,
              (s) => s.nombre,
              SILLON_NO_DISPONIBLE,
            )}
        </select>
      </label>
      {esRecepcionista && vista.vista === "dia" && (
        <label>
          Agrupar por
          <select
            value={vista.columnas}
            onChange={(e) =>
              alCambiar({
                ...vista,
                columnas:
                  e.target.value === "sillon" ? "sillon" : "profesional",
              })
            }
          >
            <option value="profesional">Profesional</option>
            <option value="sillon">Sillón</option>
          </select>
        </label>
      )}
    </div>
  );
}
