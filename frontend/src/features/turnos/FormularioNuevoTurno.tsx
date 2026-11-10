import { useState, type FormEvent } from "react";

import { Dialogo } from "../../shared/ui/Dialogo";
import type { ErrorApi } from "../../shared/api/errorApi";
import { aInstanteConDesfasaje } from "../../shared/tiempo/zonaConsultorio";
import type { Catalogos } from "../agenda/useCatalogos";
import { SelectorPaciente } from "../pacientes/SelectorPaciente";
import type { PacienteBusqueda } from "../pacientes/tipos";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { Campo } from "./Campo";
import { comoErrorApi } from "../agenda/errores";
import { interpretarErrorTurno, type CampoTurno } from "./erroresTurno";

export interface PropsFormularioNuevoTurno {
  abierto: boolean;
  catalogos: Catalogos;
  /** La fecha de la agenda en curso. */
  fechaInicial: string;
  /** El profesional del filtro, si hay uno. */
  profesionalInicial: string | null;
  /** El alta fue exitosa; recibe el `inicio` enviado. */
  alCrear: (inicio: string) => void;
  alCerrar: () => void;
  /** Vuelve a pedir los catálogos; devuelve el error si falla (D7). */
  alReleerCatalogos: () => Promise<ErrorApi | null>;
  alReleerAgenda: () => void;
}

const OBLIGATORIO = "Completá este campo.";

type ErroresPorCampo = Partial<Record<CampoTurno, string>>;

/**
 * Alta de un turno en un diálogo modal (D9). El contenido se monta solo con el diálogo
 * abierto, así cada apertura empieza con el formulario limpio.
 */
export function FormularioNuevoTurno(props: PropsFormularioNuevoTurno) {
  return (
    <Dialogo
      abierto={props.abierto}
      titulo="Nuevo turno"
      onCerrar={props.alCerrar}
    >
      {props.abierto && <Contenido {...props} />}
    </Dialogo>
  );
}

function Contenido({
  catalogos,
  fechaInicial,
  profesionalInicial,
  alCrear,
  alCerrar,
  alReleerAgenda,
}: PropsFormularioNuevoTurno) {
  const cliente = useClienteApi();
  const activoInicial = catalogos.profesionales.some(
    (p) => p.id === profesionalInicial && p.activo,
  );
  const [profesionalId, setProfesionalId] = useState(
    activoInicial && profesionalInicial !== null ? profesionalInicial : "",
  );
  const [paciente, setPaciente] = useState<PacienteBusqueda | null>(null);
  const [prestacionId, setPrestacionId] = useState("");
  const [sillonId, setSillonId] = useState("");
  const [fecha, setFecha] = useState(fechaInicial);
  const [hora, setHora] = useState("");
  const [duracion, setDuracion] = useState("");
  const [errores, setErrores] = useState<ErroresPorCampo>({});
  const [general, setGeneral] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const prestacion = catalogos.prestaciones.find((p) => p.id === prestacionId);
  const requiereSillon = prestacion?.requiere_sillon === true;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (enviando) return;
    // Solo los obligatorios se comprueban acá: lo demás lo decide la API (D9, P8)
    const faltantes: ErroresPorCampo = {};
    if (paciente === null) faltantes.paciente = "Elegí un paciente.";
    if (profesionalId === "") faltantes.profesional = OBLIGATORIO;
    if (prestacionId === "") faltantes.prestacion = OBLIGATORIO;
    if (requiereSillon && sillonId === "") faltantes.sillon = OBLIGATORIO;
    if (fecha === "") faltantes.fecha = OBLIGATORIO;
    if (hora === "") faltantes.hora = OBLIGATORIO;
    setErrores(faltantes);
    setGeneral(null);
    if (Object.keys(faltantes).length > 0 || paciente === null) return;

    const inicio = aInstanteConDesfasaje(fecha, hora);
    setEnviando(true);
    try {
      await cliente.pedir("POST", "/turnos", {
        profesional_id: profesionalId,
        paciente_id: paciente.id,
        prestacion_id: prestacionId,
        ...(requiereSillon ? { sillon_id: sillonId } : {}),
        inicio,
        ...(duracion.trim() === "" ? {} : { duracion_min: Number(duracion) }),
      });
    } catch (causa) {
      const interpretado = interpretarErrorTurno(comoErrorApi(causa), "crear");
      setGeneral(interpretado.general);
      if (interpretado.releerAgenda) alReleerAgenda();
      setEnviando(false);
      return;
    }
    alCrear(inicio);
  }

  return (
    <form noValidate onSubmit={(e) => void enviar(e)}>
      {general !== null && <div role="alert">{general}</div>}
      <fieldset>
        <legend>Paciente</legend>
        <SelectorPaciente
          elegido={paciente}
          alElegir={setPaciente}
          alCambiar={() => setPaciente(null)}
          error={errores.paciente}
        />
      </fieldset>
      <Campo etiqueta="Profesional" error={errores.profesional}>
        {(atributos) => (
          <select
            {...atributos}
            value={profesionalId}
            onChange={(e) => setProfesionalId(e.target.value)}
          >
            <option value="">Elegir…</option>
            {catalogos.profesionales
              .filter((p) => p.activo)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.apellido}, {p.nombre}
                </option>
              ))}
          </select>
        )}
      </Campo>
      <Campo etiqueta="Prestación" error={errores.prestacion}>
        {(atributos) => (
          <select
            {...atributos}
            value={prestacionId}
            onChange={(e) => setPrestacionId(e.target.value)}
          >
            <option value="">Elegir…</option>
            {catalogos.prestaciones
              .filter((p) => p.activa)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre}
                </option>
              ))}
          </select>
        )}
      </Campo>
      {requiereSillon && (
        <Campo etiqueta="Sillón" error={errores.sillon}>
          {(atributos) => (
            <select
              {...atributos}
              value={sillonId}
              onChange={(e) => setSillonId(e.target.value)}
            >
              <option value="">Elegir…</option>
              {catalogos.sillones
                .filter((s) => s.activo)
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nombre}
                  </option>
                ))}
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
      <Campo
        etiqueta="Duración"
        error={errores.duracion}
        ayuda={
          prestacion === undefined
            ? undefined
            : `Por defecto: ${prestacion.duracion_min} min`
        }
      >
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
      <button type="submit" disabled={enviando}>
        Crear turno
      </button>
      <button type="button" onClick={alCerrar}>
        Cerrar
      </button>
    </form>
  );
}
