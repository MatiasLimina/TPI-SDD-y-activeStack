import estilos from "../gestion/Gestion.module.css";
import { useState } from "react";
import { Link } from "react-router";

import type { ErrorApi } from "../../shared/api/errorApi";
import {
  fechaHoraCompleta,
  hoyLocal,
  instanteALocal,
} from "../../shared/tiempo/zonaConsultorio";
import { Campo } from "../../shared/ui/Campo";
import type { Bloqueo } from "../agenda/tipos";
import { nombreProfesional } from "../agenda/grilla";
import { DialogoFormulario } from "../gestion/DialogoFormulario";
import { camposVacios } from "../gestion/formulario";
import { useEnvioGestion } from "../gestion/useEnvioGestion";
import type { ProfesionalFicha } from "../recursos/tipos";
import { useClienteApi } from "../sesion/ProveedorSesion";
import { armarCuerpoBloqueo, enlaceAgenda } from "./bloqueos";

export const TEXTO_BLOQUEO_CON_TURNOS =
  "Hay turnos activos en ese intervalo: reprogramalos o cancelalos antes de bloquear.";

const CONFIG_ERRORES = {
  campos: {
    profesional_id: "profesional",
    inicio: "fechaDesde",
    fin: "fechaHasta",
    motivo: "motivo",
  },
  codigos: {
    bloqueo_invalido: {
      texto: "El bloqueo debe terminar después de empezar y tener un motivo.",
    },
    profesional_requerido: {
      campo: "profesional",
      texto: "Completá este campo.",
    },
    referencia_invalida: {
      campo: "profesional",
      texto: "El profesional ya no existe.",
    },
    bloqueo_con_turnos: { texto: TEXTO_BLOQUEO_CON_TURNOS },
  },
} as const;

interface TurnoAfectado {
  inicio: string;
  fin: string;
}

function turnosDe(error: ErrorApi | null): TurnoAfectado[] {
  const crudo = error?.datos.turnos;
  if (!Array.isArray(crudo)) return [];
  return crudo.filter(
    (t): t is TurnoAfectado =>
      typeof t === "object" &&
      t !== null &&
      typeof (t as TurnoAfectado).inicio === "string" &&
      typeof (t as TurnoAfectado).fin === "string",
  );
}

interface PropsFormulario {
  abierto: boolean;
  /** El odontólogo no elige profesional: la API usa el de su token (RN-AU-02). */
  esRecepcionista: boolean;
  profesionales: ProfesionalFicha[];
  alGuardado: (creado: Bloqueo) => void;
  alCerrar: () => void;
  /** Un profesional que ya no existe revela un catálogo desactualizado (D11). */
  alReleerProfesionales: () => void;
}

/** Alta de un bloqueo con fecha y hora separadas, en la zona del consultorio (D8). */
export function FormularioBloqueo({
  abierto,
  esRecepcionista,
  profesionales,
  alGuardado,
  alCerrar,
  alReleerProfesionales,
}: PropsFormulario) {
  const cliente = useClienteApi();
  const envio = useEnvioGestion(CONFIG_ERRORES);
  const [hoy] = useState(() => hoyLocal());
  const [profesional, setProfesional] = useState("");
  const [fechaDesde, setFechaDesde] = useState(hoy);
  const [horaDesde, setHoraDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState(hoy);
  const [horaHasta, setHoraHasta] = useState("");
  const [motivo, setMotivo] = useState("");

  async function enviar() {
    const valores = {
      profesional: esRecepcionista ? profesional : "-",
      fechaDesde,
      horaDesde,
      fechaHasta,
      horaHasta,
      motivo,
    };
    const obligatorios = [
      "profesional",
      "fechaDesde",
      "horaDesde",
      "fechaHasta",
      "horaHasta",
      "motivo",
    ];
    if (!envio.validarObligatorios(camposVacios(valores, obligatorios))) return;
    const cuerpo = armarCuerpoBloqueo({
      profesionalId: esRecepcionista ? profesional : null,
      fechaDesde,
      horaDesde,
      fechaHasta,
      horaHasta,
      motivo,
    });
    const resultado: { creado?: Bloqueo } = {};
    const exito = await envio.enviar(
      async () => {
        resultado.creado = await cliente.pedir<Bloqueo>(
          "POST",
          "/bloqueos",
          cuerpo,
        );
      },
      (error) => {
        if (error.codigo === "referencia_invalida") alReleerProfesionales();
      },
    );
    if (exito && resultado.creado !== undefined) alGuardado(resultado.creado);
  }

  const turnos = turnosDe(envio.errorApi);
  const errorGeneral =
    envio.general === null ? null : (
      <>
        <p>{envio.general}</p>
        {turnos.length > 0 && (
          <ul className={estilos.turnosAfectados}>
            {turnos.map((turno) => (
              <li key={`${turno.inicio}-${turno.fin}`}>
                {fechaHoraCompleta(turno.inicio)} a{" "}
                {instanteALocal(turno.fin).hora}{" "}
                <Link
                  to={enlaceAgenda(
                    instanteALocal(turno.inicio).fecha,
                    esRecepcionista ? profesional : null,
                  )}
                >
                  Ver en la agenda
                </Link>
              </li>
            ))}
          </ul>
        )}
      </>
    );

  return (
    <DialogoFormulario
      titulo="Nuevo bloqueo"
      abierto={abierto}
      alCerrar={alCerrar}
      alEnviar={() => void enviar()}
      enviando={envio.enviando}
      errorGeneral={errorGeneral}
    >
      {esRecepcionista && (
        <Campo etiqueta="Profesional" error={envio.errores.profesional}>
          {(atributos) => (
            <select
              {...atributos}
              value={profesional}
              onChange={(e) => setProfesional(e.target.value)}
            >
              <option value="">Sin elegir</option>
              {profesionales.map((p) => (
                <option key={p.id} value={p.id}>
                  {nombreProfesional(p)}
                  {p.activo ? "" : " (inactivo)"}
                </option>
              ))}
            </select>
          )}
        </Campo>
      )}
      <Campo etiqueta="Fecha desde" error={envio.errores.fechaDesde}>
        {(atributos) => (
          <input
            {...atributos}
            type="date"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Hora desde" error={envio.errores.horaDesde}>
        {(atributos) => (
          <input
            {...atributos}
            type="time"
            step={60}
            value={horaDesde}
            onChange={(e) => setHoraDesde(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Fecha hasta" error={envio.errores.fechaHasta}>
        {(atributos) => (
          <input
            {...atributos}
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Hora hasta" error={envio.errores.horaHasta}>
        {(atributos) => (
          <input
            {...atributos}
            type="time"
            step={60}
            value={horaHasta}
            onChange={(e) => setHoraHasta(e.target.value)}
          />
        )}
      </Campo>
      <Campo etiqueta="Motivo" error={envio.errores.motivo}>
        {(atributos) => (
          <input
            {...atributos}
            type="text"
            maxLength={255}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
          />
        )}
      </Campo>
    </DialogoFormulario>
  );
}
