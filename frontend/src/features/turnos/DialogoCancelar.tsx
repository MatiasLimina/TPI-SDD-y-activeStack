import { useState, type FormEvent } from "react";

import { diaYMes, instanteALocal } from "../../shared/tiempo/zonaConsultorio";
import { Dialogo } from "../../shared/ui/Dialogo";
import type { TurnoAgenda } from "../agenda/tipos";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { Campo } from "../../shared/ui/Campo";
import { useEnvioTurno } from "./useEnvioTurno";

interface PropsDialogoCancelar {
  /** El turno a cancelar, o `null` con el diálogo cerrado. */
  turno: TurnoAgenda | null;
  alCancelado: () => void;
  alCerrar: () => void;
  alReleerAgenda: () => void;
}

const MAXIMO_MOTIVO = 255;

/** Confirmación de cancelación con motivo opcional (D11, DD-14, DD-22). */
export function DialogoCancelar(props: PropsDialogoCancelar) {
  return (
    <Dialogo
      abierto={props.turno !== null}
      titulo="Cancelar turno"
      onCerrar={props.alCerrar}
    >
      {props.turno !== null && (
        <Contenido key={props.turno.id} {...props} turno={props.turno} />
      )}
    </Dialogo>
  );
}

function Contenido({
  turno,
  alCancelado,
  alCerrar,
  alReleerAgenda,
}: PropsDialogoCancelar & { turno: TurnoAgenda }) {
  const cliente = useClienteApi();
  // Cancelar no relee catálogos: ningún error de esta operación los revela
  const envio = useEnvioTurno("cancelar", {
    alReleerAgenda,
    alReleerCatalogos: () => Promise.resolve(null),
  });
  const [motivo, setMotivo] = useState("");
  const inicio = instanteALocal(turno.inicio);

  async function confirmar(evento: FormEvent) {
    evento.preventDefault();
    if (envio.enviando || envio.turnoObsoleto) return;
    const motivoLimpio = motivo.trim();
    const exito = await envio.enviar(
      () =>
        cliente.pedir(
          "POST",
          `/turnos/${turno.id}/cancelar`,
          motivoLimpio === "" ? undefined : { motivo: motivoLimpio },
        ),
      { profesional: "", prestacion: "", sillon: "" },
    );
    if (exito) alCancelado();
  }

  return (
    <form noValidate onSubmit={(e) => void confirmar(e)}>
      {envio.generales.length > 0 && (
        <div role="alert">
          {envio.generales.map((texto) => (
            <p key={texto}>{texto}</p>
          ))}
        </div>
      )}
      <p>
        ¿Cancelar el turno de{" "}
        <strong>
          {turno.paciente.apellido}, {turno.paciente.nombre}
        </strong>{" "}
        del <strong>{diaYMes(inicio.fecha)}</strong> a las{" "}
        <strong>{inicio.hora}</strong>?
      </p>
      <Campo etiqueta="Motivo">
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={MAXIMO_MOTIVO}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
        )}
      </Campo>
      <button type="submit" disabled={envio.enviando || envio.turnoObsoleto}>
        Confirmar cancelación
      </button>
      <button type="button" onClick={alCerrar}>
        Volver
      </button>
    </form>
  );
}
