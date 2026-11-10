import { useState, type FormEvent } from "react";

import { Dialogo } from "../../shared/ui/Dialogo";
import type { ErrorApi } from "../../shared/api/errorApi";
import { aInstanteConDesfasaje } from "../../shared/tiempo/zonaConsultorio";
import type { Catalogos } from "../agenda/useCatalogos";
import { SelectorPaciente } from "../pacientes/SelectorPaciente";
import type { PacienteBusqueda } from "../pacientes/tipos";
import { useClienteApi } from "../sesion/ProveedorSesion";
import {
  nombreProfesional,
  PROFESIONAL_NO_DISPONIBLE,
  SILLON_NO_DISPONIBLE,
} from "../agenda/grilla";
import { PRESTACION_NO_DISPONIBLE } from "../agenda/nombres";
import { Campo } from "./Campo";
import { OpcionesRecurso } from "./OpcionesRecurso";
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
  alReleerCatalogos,
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
  const [generales, setGenerales] = useState<string[]>([]);
  // El sillón se muestra aunque el catálogo no lo pida, si la API dijo que hace falta
  const [sillonForzado, setSillonForzado] = useState(false);
  // Valor rechazado de cada selector: sigue como opción hasta que se cambie (P5)
  const [rechazado, setRechazado] = useState<
    Partial<Record<"profesional" | "prestacion" | "sillon", string>>
  >({});
  const [enviando, setEnviando] = useState(false);

  const prestacion = catalogos.prestaciones.find((p) => p.id === prestacionId);
  const mostrarSillon = prestacion?.requiere_sillon === true || sillonForzado;

  /** El valor rechazado se ofrece mientras siga elegido. */
  function conservar(
    campo: "profesional" | "prestacion" | "sillon",
    elegido: string,
  ): string[] {
    return rechazado[campo] !== undefined && rechazado[campo] === elegido
      ? [elegido]
      : [];
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (enviando) return;
    // Solo los obligatorios se comprueban acá: lo demás lo decide la API (D9, P8)
    const faltantes: ErroresPorCampo = {};
    if (paciente === null) faltantes.paciente = "Elegí un paciente.";
    if (profesionalId === "") faltantes.profesional = OBLIGATORIO;
    if (prestacionId === "") faltantes.prestacion = OBLIGATORIO;
    if (mostrarSillon && sillonId === "") faltantes.sillon = OBLIGATORIO;
    if (fecha === "") faltantes.fecha = OBLIGATORIO;
    if (hora === "") faltantes.hora = OBLIGATORIO;
    setErrores(faltantes);
    setGenerales([]);
    if (Object.keys(faltantes).length > 0 || paciente === null) return;

    const inicio = aInstanteConDesfasaje(fecha, hora);
    setEnviando(true);
    try {
      await cliente.pedir("POST", "/turnos", {
        profesional_id: profesionalId,
        paciente_id: paciente.id,
        prestacion_id: prestacionId,
        ...(mostrarSillon ? { sillon_id: sillonId } : {}),
        inicio,
        ...(duracion.trim() === "" ? {} : { duracion_min: Number(duracion) }),
      });
    } catch (causa) {
      const error = comoErrorApi(causa);
      const interpretado = interpretarErrorTurno(error, "crear");
      setErrores(interpretado.porCampo);
      if (interpretado.porCampo.sillon !== undefined) setSillonForzado(true);
      const referencia = error.datos.referencia;
      if (
        error.codigo === "referencia_invalida" &&
        (referencia === "profesional" ||
          referencia === "prestacion" ||
          referencia === "sillon")
      )
        setRechazado({
          [referencia]: {
            profesional: profesionalId,
            prestacion: prestacionId,
            sillon: sillonId,
          }[referencia],
        });
      setGenerales(interpretado.general === null ? [] : [interpretado.general]);
      if (interpretado.releerAgenda) alReleerAgenda();
      setEnviando(false);
      if (interpretado.releerCatalogos) {
        const falla = await alReleerCatalogos();
        // El formulario sigue abierto: la falla se suma como error general (D7, P14)
        if (falla !== null)
          setGenerales((anteriores) => [...anteriores, falla.mensaje]);
      }
      return;
    }
    alCrear(inicio);
  }

  return (
    <form noValidate onSubmit={(e) => void enviar(e)}>
      {generales.length > 0 && (
        <div role="alert">
          {generales.map((texto) => (
            <p key={texto}>{texto}</p>
          ))}
        </div>
      )}
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
            <OpcionesRecurso
              catalogo={catalogos.profesionales}
              estaActivo={(p) => p.activo}
              nombreDe={nombreProfesional}
              nombreAusente={PROFESIONAL_NO_DISPONIBLE}
              conservar={conservar("profesional", profesionalId)}
            />
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
            <OpcionesRecurso
              catalogo={catalogos.prestaciones}
              estaActivo={(p) => p.activa}
              nombreDe={(p) => p.nombre}
              nombreAusente={PRESTACION_NO_DISPONIBLE}
              conservar={conservar("prestacion", prestacionId)}
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
                estaActivo={(x) => x.activo}
                nombreDe={(x) => x.nombre}
                nombreAusente={SILLON_NO_DISPONIBLE}
                conservar={conservar("sillon", sillonId)}
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
