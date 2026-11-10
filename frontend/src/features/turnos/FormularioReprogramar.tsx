import { useState, type FormEvent } from "react";

import type { ErrorApi } from "../../shared/api/errorApi";
import {
  aInstanteConDesfasaje,
  instanteALocal,
} from "../../shared/tiempo/zonaConsultorio";
import { Dialogo } from "../../shared/ui/Dialogo";
import {
  nombreProfesional,
  PROFESIONAL_NO_DISPONIBLE,
  SILLON_NO_DISPONIBLE,
} from "../agenda/grilla";
import type { Nombres } from "../agenda/nombres";
import type { TurnoAgenda } from "../agenda/tipos";
import type { Catalogos } from "../agenda/useCatalogos";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { Campo } from "./Campo";
import { OpcionesRecurso } from "./OpcionesRecurso";
import { useEnvioTurno, type ErroresPorCampo } from "./useEnvioTurno";

export interface PropsFormularioReprogramar {
  /** El turno a reprogramar, o `null` con el diálogo cerrado. */
  turno: TurnoAgenda | null;
  catalogos: Catalogos;
  nombres: Nombres;
  /** La reprogramación fue exitosa. */
  alReprogramado: () => void;
  alCerrar: () => void;
  alReleerCatalogos: () => Promise<ErrorApi | null>;
  alReleerAgenda: () => void;
}

const OBLIGATORIO = "Completá este campo.";
const DURACION_OBLIGATORIA = "Ingresá la duración.";
const SIN_CAMBIOS = "No hiciste cambios.";

/**
 * Reprogramación de un turno en un diálogo modal (D10). El `PATCH` lleva solo lo que cambió;
 * paciente y prestación se ven como texto y no se envían (DD-23 b).
 */
export function FormularioReprogramar(props: PropsFormularioReprogramar) {
  return (
    <Dialogo
      abierto={props.turno !== null}
      titulo="Reprogramar turno"
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
  catalogos,
  nombres,
  alReprogramado,
  alCerrar,
  alReleerAgenda,
  alReleerCatalogos,
}: PropsFormularioReprogramar & { turno: TurnoAgenda }) {
  const cliente = useClienteApi();
  const envio = useEnvioTurno("reprogramar", {
    alReleerAgenda,
    alReleerCatalogos,
  });
  const original = instanteALocal(turno.inicio);
  const [profesionalId, setProfesionalId] = useState(turno.profesional_id);
  const [sillonId, setSillonId] = useState(turno.sillon_id ?? "");
  const [fecha, setFecha] = useState(original.fecha);
  const [hora, setHora] = useState(original.hora);
  const [duracion, setDuracion] = useState(String(turno.duracion_min));
  const [sinCambios, setSinCambios] = useState(false);

  const { errores } = envio;
  // El selector sigue a la prestación del catálogo (D10): puede haber cambiado desde el alta
  const requiereSillon =
    catalogos.prestaciones.find((p) => p.id === turno.prestacion_id)
      ?.requiere_sillon === true;
  const mostrarSillon = requiereSillon || envio.sillonForzado;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (envio.enviando || envio.turnoObsoleto) return;
    setSinCambios(false);
    // Primero los obligatorios y después la comparación (P9)
    const faltantes: ErroresPorCampo = {};
    if (fecha === "") faltantes.fecha = OBLIGATORIO;
    if (hora === "") faltantes.hora = OBLIGATORIO;
    if (mostrarSillon && sillonId === "") faltantes.sillon = OBLIGATORIO;
    if (duracion.trim() === "") faltantes.duracion = DURACION_OBLIGATORIA;
    if (!envio.mostrarObligatorios(faltantes)) return;

    const cuerpo: Record<string, unknown> = {};
    if (fecha !== original.fecha || hora !== original.hora)
      cuerpo.inicio = aInstanteConDesfasaje(fecha, hora);
    if (profesionalId !== turno.profesional_id)
      cuerpo.profesional_id = profesionalId;
    if (mostrarSillon && sillonId !== (turno.sillon_id ?? ""))
      cuerpo.sillon_id = sillonId;
    if (Number(duracion) !== turno.duracion_min)
      cuerpo.duracion_min = Number(duracion);
    if (Object.keys(cuerpo).length === 0) {
      setSinCambios(true);
      return;
    }
    // Si la prestación ya no requiere sillón y el turno tiene uno, el nulo viaja solo con otro cambio
    if (!mostrarSillon && turno.sillon_id !== null) cuerpo.sillon_id = null;

    const exito = await envio.enviar(
      () => cliente.pedir("PATCH", `/turnos/${turno.id}/reprogramar`, cuerpo),
      { profesional: profesionalId, prestacion: "", sillon: sillonId },
    );
    if (exito) alReprogramado();
  }

  return (
    <form noValidate onSubmit={(e) => void enviar(e)}>
      {envio.generales.length > 0 && (
        <div role="alert">
          {envio.generales.map((texto) => (
            <p key={texto}>{texto}</p>
          ))}
        </div>
      )}
      {sinCambios && <p role="status">{SIN_CAMBIOS}</p>}
      <dl>
        <dt>Paciente</dt>
        <dd>
          {turno.paciente.apellido}, {turno.paciente.nombre}
        </dd>
        <dt>Prestación</dt>
        <dd>{nombres.prestacion(turno.prestacion_id)}</dd>
      </dl>
      <p>Para cambiarlos, cancelá este turno y creá uno nuevo.</p>
      <Campo etiqueta="Profesional" error={errores.profesional}>
        {(atributos) => (
          <select
            {...atributos}
            value={profesionalId}
            onChange={(e) => setProfesionalId(e.target.value)}
          >
            <OpcionesRecurso
              catalogo={catalogos.profesionales}
              estaActivo={(p) => p.activo}
              nombreDe={nombreProfesional}
              nombreAusente={PROFESIONAL_NO_DISPONIBLE}
              conservar={[
                turno.profesional_id,
                ...envio.conservar("profesional", profesionalId),
              ]}
            />
          </select>
        )}
      </Campo>
      {mostrarSillon && (
        <Campo etiqueta="Sillón" error={errores.sillon}>
          {(atributos) => (
            <select
              {...atributos}
              value={sillonId}
              onChange={(e) => setSillonId(e.target.value)}
            >
              <option value="">Elegir…</option>
              <OpcionesRecurso
                catalogo={catalogos.sillones}
                estaActivo={(s) => s.activo}
                nombreDe={(s) => s.nombre}
                nombreAusente={SILLON_NO_DISPONIBLE}
                conservar={[
                  ...(turno.sillon_id === null ? [] : [turno.sillon_id]),
                  ...envio.conservar("sillon", sillonId),
                ]}
              />
            </select>
          )}
        </Campo>
      )}
      <Campo etiqueta="Fecha" error={errores.fecha}>
        {(atributos) => (
          <input
            {...atributos}
            type="date"
            value={fecha}
            onChange={(e) => setFecha(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Hora" error={errores.hora}>
        {(atributos) => (
          <input
            {...atributos}
            type="time"
            step={300}
            value={hora}
            onChange={(e) => setHora(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Duración" error={errores.duracion}>
        {(atributos) => (
          <input
            {...atributos}
            type="number"
            min={5}
            max={480}
            step={5}
            value={duracion}
            onChange={(e) => setDuracion(e.target.value)}
          />
        )}
      </Campo>
      <button type="submit" disabled={envio.enviando || envio.turnoObsoleto}>
        Reprogramar
      </button>
      <button type="button" onClick={alCerrar}>
        Cerrar
      </button>
    </form>
  );
}
