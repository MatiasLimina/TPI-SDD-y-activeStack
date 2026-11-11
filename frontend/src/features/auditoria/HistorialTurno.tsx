import type { ErrorApi } from "../../shared/api/errorApi";
import { fechaHoraCompleta } from "../../shared/tiempo/zonaConsultorio";
import { Dialogo } from "../../shared/ui/Dialogo";
import type { Nombres } from "../agenda/nombres";
import type { TurnoAgenda } from "../agenda/tipos";
import { TEXTO_SIN_PERMISO_LEER } from "../gestion/erroresGestion";
import { useListado } from "../gestion/useListado";
import {
  autorDe,
  cambiosDeReprogramacion,
  datosDeCreacion,
  etiquetaAccion,
  textoDeCancelacion,
  type RegistroAuditoria,
} from "./historial";

interface PropsHistorial {
  /** El turno cuyo historial se muestra, o `null` con el diálogo cerrado. */
  turno: TurnoAgenda | null;
  nombres: Nombres;
  /** `sub` de la sesión: solo para decir `Vos` (D10). */
  usuarioSesion: string | null;
  alCerrar: () => void;
}

function textoDeError(error: ErrorApi): string {
  if (error.codigo === "turno_inexistente") return "Este turno ya no existe.";
  return error.status === 403 ? TEXTO_SIN_PERMISO_LEER : error.mensaje;
}

/** Historial de auditoría de un turno, solo para la recepcionista (US-011, DD-25). */
export function HistorialTurno({
  turno,
  nombres,
  usuarioSesion,
  alCerrar,
}: PropsHistorial) {
  return (
    <Dialogo
      abierto={turno !== null}
      titulo="Historial del turno"
      onCerrar={alCerrar}
    >
      {turno !== null && (
        <Contenido
          key={turno.id}
          turno={turno}
          nombres={nombres}
          usuarioSesion={usuarioSesion}
          alCerrar={alCerrar}
        />
      )}
    </Dialogo>
  );
}

function Contenido({
  turno,
  nombres,
  usuarioSesion,
  alCerrar,
}: PropsHistorial & { turno: TurnoAgenda }) {
  const listado = useListado<RegistroAuditoria[]>(
    `/turnos/${turno.id}/auditoria`,
  );
  const { datos, error, cargando, reintentar } = listado;

  return (
    <>
      {error !== null && (
        <div role="alert">
          <p>{textoDeError(error)}</p>
          {error.codigo !== "turno_inexistente" && (
            <button type="button" onClick={reintentar}>
              Reintentar
            </button>
          )}
        </div>
      )}
      {error === null && (cargando || datos === null) && (
        <p role="status">Cargando…</p>
      )}
      {error === null && datos !== null && datos.length === 0 && (
        <p>Este turno no tiene registros de auditoría.</p>
      )}
      {error === null && datos !== null && datos.length > 0 && (
        <ol>
          {datos.map((registro) => (
            <li key={registro.id}>
              <p>
                <strong>{etiquetaAccion(registro.accion)}</strong>{" "}
                <span>{fechaHoraCompleta(registro.ocurrido_en)}</span>{" "}
                <span>{autorDe(registro.usuario_id, usuarioSesion)}</span>
              </p>
              <DatosDelRegistro registro={registro} nombres={nombres} />
            </li>
          ))}
        </ol>
      )}
      <button type="button" onClick={alCerrar}>
        Cerrar
      </button>
    </>
  );
}

function DatosDelRegistro({
  registro,
  nombres,
}: {
  registro: RegistroAuditoria;
  nombres: Nombres;
}) {
  const { accion, valores_previos: previos, valores_nuevos: nuevos } = registro;
  if (nuevos === null) return null;
  if (accion === "crear")
    return (
      <dl>
        {datosDeCreacion(nuevos, nombres).map((dato) => (
          <div key={dato.etiqueta}>
            <dt>{dato.etiqueta}</dt>
            <dd>{dato.valor}</dd>
          </div>
        ))}
      </dl>
    );
  if (accion === "cancelar") return <p>{textoDeCancelacion(nuevos)}</p>;
  const cambios =
    previos === null ? [] : cambiosDeReprogramacion(previos, nuevos, nombres);
  return cambios.length === 0 ? (
    <p>Sin cambios en los datos.</p>
  ) : (
    <div>
      {cambios.map((cambio) => (
        <p key={cambio}>{cambio}</p>
      ))}
    </div>
  );
}
