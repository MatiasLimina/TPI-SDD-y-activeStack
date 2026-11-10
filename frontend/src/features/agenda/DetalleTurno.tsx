import { Dialogo } from "../../shared/ui/Dialogo";
import type { TurnoAgenda } from "./tipos";

interface PropsDetalle {
  /** El turno elegido en la agenda, o `null` con el diálogo cerrado. */
  turno: TurnoAgenda | null;
  /** Solo la recepcionista opera (D16); el odontólogo ve el detalle de solo lectura. */
  puedeOperar: boolean;
  alCerrar: () => void;
  alReprogramar: (turno: TurnoAgenda) => void;
  alCancelar: (turno: TurnoAgenda) => void;
}

/**
 * Reprogramar y cancelar solo se ofrecen para un turno `programado` cuyo inicio es posterior
 * al reloj (RN-AG-13, DD-23). Solo decide qué se muestra: la API sigue siendo la autoridad.
 */
function admiteOperaciones(turno: TurnoAgenda): boolean {
  return (
    turno.estado === "programado" &&
    new Date(turno.inicio).getTime() > Date.now()
  );
}

/** Detalle de un turno en un diálogo, para ambos roles. */
export function DetalleTurno({
  turno,
  puedeOperar,
  alCerrar,
  alReprogramar,
  alCancelar,
}: PropsDetalle) {
  return (
    <Dialogo
      abierto={turno !== null}
      titulo="Detalle del turno"
      onCerrar={alCerrar}
    >
      {turno !== null && (
        <>
          {puedeOperar && admiteOperaciones(turno) && (
            <div>
              <button type="button" onClick={() => alReprogramar(turno)}>
                Reprogramar
              </button>
              <button type="button" onClick={() => alCancelar(turno)}>
                Cancelar turno
              </button>
            </div>
          )}
          <button type="button" onClick={alCerrar}>
            Cerrar
          </button>
        </>
      )}
    </Dialogo>
  );
}
