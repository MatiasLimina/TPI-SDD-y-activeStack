import { Dialogo } from "../../shared/ui/Dialogo";
import { diaYMes, instanteALocal } from "../../shared/tiempo/zonaConsultorio";
import type { Nombres } from "./nombres";
import type { TurnoAgenda } from "./tipos";

interface PropsDetalle {
  /** El turno elegido en la agenda, o `null` con el diálogo cerrado. */
  turno: TurnoAgenda | null;
  nombres: Nombres;
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

/** `DD/MM HH:MM – HH:MM`, y con la fecha también en el fin si el turno cruza la medianoche. */
function textoHorario(turno: TurnoAgenda): string {
  const inicio = instanteALocal(turno.inicio);
  const fin = instanteALocal(turno.fin);
  const finTexto =
    fin.fecha === inicio.fecha ? fin.hora : `${diaYMes(fin.fecha)} ${fin.hora}`;
  return `${diaYMes(inicio.fecha)} ${inicio.hora} – ${finTexto}`;
}

/** Detalle de un turno en un diálogo, para ambos roles. */
export function DetalleTurno({
  turno,
  nombres,
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
          <dl>
            <dt>Horario</dt>
            <dd>{textoHorario(turno)}</dd>
            <dt>Paciente</dt>
            <dd>
              {turno.paciente.apellido}, {turno.paciente.nombre}
            </dd>
            <dt>Prestación</dt>
            <dd>{nombres.prestacion(turno.prestacion_id)}</dd>
            <dt>Profesional</dt>
            <dd>{nombres.profesional(turno.profesional_id)}</dd>
            <dt>Sillón</dt>
            <dd>{nombres.sillon(turno.sillon_id)}</dd>
            <dt>Estado</dt>
            <dd>{turno.estado === "cancelado" ? "Cancelado" : "Programado"}</dd>
            {turno.motivo_cancelacion !== null && (
              <>
                <dt>Motivo de la cancelación</dt>
                <dd>{turno.motivo_cancelacion}</dd>
              </>
            )}
          </dl>
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
