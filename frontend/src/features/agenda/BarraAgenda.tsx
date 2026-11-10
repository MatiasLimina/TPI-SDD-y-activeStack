import { sumarDias } from "../../shared/tiempo/zonaConsultorio";
import type { VistaAgenda } from "./vistaAgenda";

interface PropsBarra {
  vista: VistaAgenda;
  /** Día actual del consultorio, para el botón `Hoy`. */
  hoy: string;
  /** Cada cambio es una navegación nueva (D6). */
  alCambiar: (vista: VistaAgenda) => void;
  alActualizar: () => void;
}

/** Controles de vista y de navegación de la agenda. */
export function BarraAgenda({
  vista,
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
      <button type="button" onClick={alActualizar}>
        Actualizar
      </button>
    </div>
  );
}
